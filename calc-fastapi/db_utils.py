from starlette import status

# Хранилище пулов: {'db_name': pool_object}
pools = {}
from fastapi import HTTPException, status
from dotenv import load_dotenv
import os
import asyncpg
from typing import Sequence, Any



load_dotenv()


# Убедись, что переменные окружения загружены (например, через load_dotenv())
# from dotenv import load_dotenv
# load_dotenv()

async def get_db_pool(db_name: str):
    """Возвращает существующий пул или создает новый"""
    if db_name not in pools:
        # Получаем базовый DSN из переменных окружения
        base_dsn = os.getenv("POSTGRES_DSN")

        if not base_dsn:
            raise ValueError("Переменная POSTGRES_DSN не найдена в .env файле")

        # Формируем полный DSN: добавляем слэш и имя базы
        dsn = f"{base_dsn}/{db_name}"

        # Инициализируем пул
        pools[db_name] = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        print(f"--- Пул соединений для БД '{db_name}' создан ({base_dsn}/{db_name}) ---")

    return pools[db_name]


async def select_query(sql: str, params: dict, db_name: str):
    """Выполняет запрос в указанной БД, используя её пул"""
    pool = await get_db_pool(db_name)

    async with pool.acquire() as conn:
        values = list(params.values())
        rows = await conn.fetch(sql, *values)
        return [dict(row) for row in rows]


"""Возвращает словарь {cod: id} из кодов (cods) сущности (entity): {'Cod_A': 1000, 'Cod_B': 1001, ...}"""
async def cod_id_from_entity(entity: str, cods: Sequence[str]) -> dict[Any, Any] | tuple[Any]:
    if not cods:
        return {}

    # Формируем безопасный список значений в кавычках для IN (...)
    formatted_cods = ", ".join(f"'{c}'" for c in cods)
    query = f"SELECT id, cod FROM {entity} WHERE cod IN ({formatted_cods})"

    res = await select_query(query, {}, "fish_model")
    return {item['cod']: item['id'] for item in res}


"""Возвращает кортеж идентификаторов: (id1, id2, ...)"""
async def ids_from_entity_cods(entity: str, cods: Sequence[str]) -> tuple[int, ...]:
    # 1. Если список кодов пуст — статус 400 (Bad Request)
    if not cods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указаны коды для выборки."
        )

    formatted_cods = ", ".join(f"'{c}'" for c in cods)
    query = f"SELECT id, cod FROM {entity} WHERE cod IN ({formatted_cods})"
    res = await select_query(query, {}, "fish_model")

    # 2. Если по запросу вообще ничего не нашлось — статус 404 (Not Found)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"В сущности '{entity}' не найден ни один из указанных кодов: {list(cods)}"
        )

    found_map = {item["cod"]: item["id"] for item in res}

    # 3. Если нашлась только часть кодов — статус 404 с перечислением недостающих
    missing_cods = [c for c in cods if c not in found_map]
    if missing_cods:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"В сущности '{entity}' не найдены коды: {missing_cods}"
        )

    return tuple(found_map[c] for c in cods)



""" Из таблицы PropVal возвращает id в зависимости entity (Cls, FV, Measure) и его id """
async def id_propval(entity: str, id_entity: int, cod_prop: str):
    query = f"""
        select pv.id from PropVal pv, Prop p
        where pv.prop=p.id and pv.{entity}={id_entity} and p.cod like '{cod_prop}'    
    """
    res = await select_query(query, {}, "fish_model")
    if len(res) > 0:
        return res[0]["id"]
    else:
        raise 'NotFoundPossibleValues-{cod_prop}'

""" Возвращает список {idPropVal: idEntity} | {idEntity: idPropVal} в зависимости key_is_propval"""
async def map_entity_id_from_pv(entity: str, cod_prop: str, key_is_propval: bool = False):
    query = f"""
        select pv.id, pv.{entity} from PropVal pv, Prop p
        where pv.prop=p.id and p.cod='{cod_prop}' and pv.{entity} is not null    
    """
    res = await select_query(query, {}, "fish_model")
    if key_is_propval:
        return {item['id']: item[entity] for item in res}
    else:
        return {item[entity]: item['id'] for item in res}


async def close_all_pools():
    """Закрывает все открытые пулы при выключении"""
    for name, pool in pools.items():
        await pool.close()
        print(f"--- Пул БД '{name}' закрыт ---")
