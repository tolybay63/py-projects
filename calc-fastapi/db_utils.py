import os
from typing import Any, Sequence
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