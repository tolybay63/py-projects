import os
from typing import Any, Sequence, Coroutine
from dotenv import load_dotenv
import asyncpg
from fastapi import HTTPException, status

load_dotenv()

# Хранилище пулов соединений: {'db_name': pool_object}
pools = {}


async def get_db_pool(db_name: str):
    """Возвращает существующий пул или создает новый для указанной базы данных."""
    if db_name not in pools:
        base_dsn = os.getenv("POSTGRES_DSN")
        if not base_dsn:
            raise ValueError("Переменная POSTGRES_DSN не найдена в .env файле")

        dsn = f"{base_dsn}/{db_name}"
        pools[db_name] = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        print(f"--- Пул соединений для БД '{db_name}' создан ({dsn}) ---")

    return pools[db_name]


async def select_query(sql: str, params: dict, db_name: str = "fish_model"):
    """Выполняет SELECT-запрос в указанной БД (по умолчанию в fish_model)."""
    pool = await get_db_pool(db_name)

    async with pool.acquire() as conn:
        values = list(params.values())
        rows = await conn.fetch(sql, *values)
        return [dict(row) for row in rows]

#====================================================

async def get_years(calculation_id: int) -> dict:
    # 1. Получаем ID свойств из мета-базы
    mp = await cod_id_from_entity("Prop", ["Prop_CalcStartYear", "Prop_CalcEndYear"], db_name="fish_model")

    query = f"""
        select 
            v1.strVal as year1,
            v2.strVal as year2
        from Obj o
            join DataProp d1 on d1.isObj=1 and d1.objOrRelObj=o.id and d1.prop={mp['Prop_CalcStartYear']}
            join DataPropVal v1 on v1.dataprop=d1.id
            join DataProp d2 on d2.isObj=1 and d2.objOrRelObj=o.id and d2.prop={mp['Prop_CalcEndYear']}
            join DataPropVal v2 on v2.dataprop=d2.id
        where o.id = $1
    """
    # Передаем id через позиционный параметр asyncpg ($1)
    pool = await get_db_pool("fish_calc")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, calculation_id)
        if not row:
            raise ValueError(f"Расчет с id={calculation_id} не найден в fish_calc")
        return {"year1": int(row["year1"]), "year2": int(row["year2"])}


async def load_reservoir_data(calculation_id: int, props_list: list[str]) -> dict:
    return await load_data_with_period(calculation_id, props_list)


async def load_data_with_period(calculation_id: int, props_list: list[str]) -> dict:
    # Шаг 1. Получаем начальный и конечный год расчета
    years = await get_years(calculation_id)
    year1, year2 = years["year1"], years["year2"]

    # Шаг 2. Получаем ID переданных свойств из базы fish_model (meta)
    prop_ids = await ids_from_entity_cods("Prop", props_list, db_name="fish_model")

    # Шаг 3. Строим динамические колонки годов для SQL (например: null as v2022, null as v2023...)
    years_range = range(year1, year2 + 1)
    sel_columns = ", ".join([f"null as v{y}" for y in years_range])

    # Шаг 4. Формируем запросы для свойств и их дочерних элементов (parent)
    sub_queries = []
    for pid in prop_ids:
        sub_queries.append(f"""
            select id, cod, {sel_columns} from prop where id = {pid}
            union all
            select id, cod, {sel_columns} from prop where parent = {pid}
        """)

    meta_sql = " union all ".join(sub_queries)

    # Выполняем мета-запрос в fish_model
    meta_rows = await select_query(meta_sql, {}, db_name="fish_model")

    # Мапа для быстрого поиска кодов свойств по их ID: {prop_id: 'Prop_WaterArea', ...}
    id_to_cod = {row["id"]: row["cod"] for row in meta_rows}
    all_prop_ids = list(id_to_cod.keys())

    if not all_prop_ids:
        return {}

    # Шаг 5. Загружаем фактические значения с периодами из fish_calc
    # Формируем список ID свойств для IN (...)
    ids_str = ", ".join(map(str, all_prop_ids))
    val_sql = f"""
        select 
            d1.prop as prop_id,
            v1.numberval as val,
            date_part('year', v1.dbeg)::int as y
        from Obj o
            join DataProp d1 on d1.isObj=1 and d1.objOrRelObj=o.id and d1.periodType is not null
            join DataPropVal v1 on v1.dataprop=d1.id and v1.numberval is not null
        where o.id = $1 and d1.prop in ({ids_str})
    """

    pool = await get_db_pool("fish_calc")
    async with pool.acquire() as conn:
        val_rows = await conn.fetch(val_sql, calculation_id)

    # Шаг 6. Индексируем значения для быстрого доступа: {(prop_id, year): value}
    val_map = {(r["prop_id"], r["y"]): r["val"] for r in val_rows}

    # Шаг 7. Собираем итоговую структуру в виде словаря: reservoir[cod][year] = value
    meter_data = {}

    for row in meta_rows:
        p_id = row["id"]
        cod = row["cod"]

        if cod not in meter_data:
            meter_data[cod] = {}

        for y in years_range:
            val = val_map.get((p_id, y))
            if val is not None:
                meter_data[cod][y] = val

    return meter_data

#====================================================

async def cod_id_from_entity(entity: str, cods: Sequence[str], db_name: str = "fish_model") -> dict[Any, Any]:
    """Возвращает словарь {cod: id} из сущностей метаданных (по умолчанию в БД fish_model)."""
    if not cods:
        return {}

    formatted_cods = ", ".join(f"'{c}'" for c in cods)
    query = f"SELECT id, cod FROM {entity} WHERE cod IN ({formatted_cods})"

    res = await select_query(query, {}, db_name)
    return {item['cod']: item['id'] for item in res}


async def ids_from_entity_cods(entity: str, cods: Sequence[str], db_name: str = "fish_model") -> tuple[int, ...]:
    """Возвращает кортеж идентификаторов с проверкой наличия всех кодов."""
    if not cods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указаны коды для выборки."
        )

    formatted_cods = ", ".join(f"'{c}'" for c in cods)
    query = f"SELECT id, cod FROM {entity} WHERE cod IN ({formatted_cods})"
    res = await select_query(query, {}, db_name)

    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"В сущности '{entity}' не найден ни один из указанных кодов: {list(cods)}"
        )

    found_map = {item["cod"]: item["id"] for item in res}
    missing_cods = [c for c in cods if c not in found_map]

    if missing_cods:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"В сущности '{entity}' не найдены коды: {missing_cods}"
        )

    return tuple(found_map[c] for c in cods)


async def id_propval(entity: str, id_entity: int, cod_prop: str, db_name: str = "fish_model"):
    """Из таблицы PropVal возвращает id свойства по связующей сущности и коду пропса."""
    query = f"""
        select pv.id from PropVal pv, Prop p
        where pv.prop = p.id and pv.{entity} = $1 and p.cod = $2    
    """
    pool = await get_db_pool(db_name)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, id_entity, cod_prop)
        if row:
            return row["id"]
        else:
            raise ValueError(f"NotFoundPossibleValues-{cod_prop}")


async def map_entity_id_from_pv(entity: str, cod_prop: str, key_is_propval: bool = False, db_name: str = "fish_model"):
    """Возвращает карту соответствия между ID PropVal и ID сущности."""
    query = f"""
        select pv.id, pv.{entity} from PropVal pv, Prop p
        where pv.prop = p.id and p.cod = $1 and pv.{entity} is not null    
    """
    pool = await get_db_pool(db_name)
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, cod_prop)
        if key_is_propval:
            return {item['id']: item[entity] for item in rows}
        else:
            return {item[entity]: item['id'] for item in rows}


async def close_all_pools():
    """Закрывает все открытые пулы при выключении приложения."""
    for name, pool in list(pools.items()):
        await pool.close()
        print(f"--- Пул БД '{name}' закрыт ---")
    pools.clear()