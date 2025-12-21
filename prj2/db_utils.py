from typing import Any

import asyncpg

# Хранилище пулов: {'db_name': pool_object}
pools = {}

async def get_db_pool(db_name: str):
    """Возвращает существующий пул или создает новый"""
    if db_name not in pools:
        dsn = f"postgresql://pg:1q2w3e4R@127.0.0.1:5432/{db_name}"
        # Инициализируем пул для конкретной БД
        pools[db_name] = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        print(f"--- Пул соединений для БД '{db_name}' создан ---")
    return pools[db_name]


async def select_query(sql: str, params: dict, db_name: str):
    """Выполняет запрос в указанной БД, используя её пул"""
    pool = await get_db_pool(db_name)

    async with pool.acquire() as conn:
        values = list(params.values())
        rows = await conn.fetch(sql, *values)
        return [dict(row) for row in rows]

#Частный случай УДАЛИТЬ!
async def get_prop_params(props: list):
    """Возвращает словарь из props: {'Prop_A': 1000, 'Prop_B: 1001', ...}"""
    query = "SELECT id, cod FROM prop WHERE cod like 'Prop_%'"
    res = await select_query(query, {}, "dtj_model")
    result_dict = {item['cod']: item['id'] for item in res}
    return {k: result_dict[k] for k in props if k in result_dict}

"""Возвращает словарь {cod: id} из кодов (cods) сущности (entity) в порядке cods: {'Cod_A': 1000, 'Cod_B: 1001', ...}"""
async def cod_id_from_entity(entity: str, cods: list):
    query = f"SELECT id, cod FROM {entity} WHERE cod like '{entity}_%'"
    res = await select_query(query, {}, "dtj_model")
    result_dict = {item['cod']: item['id'] for item in res}
    return {k: result_dict[k] for k in cods if k in result_dict}

"""Возвращает словарь {cod: id} из сущности (entity) {'Cod_A': 1000, 'Cod_B: 1001', ...}"""
async def cod_id_from_entity_map(entity: str, cod: str):
    query = f"SELECT id, cod FROM {entity} WHERE cod like '{cod}'"
    res = await select_query(query, {}, "dtj_model")
    return {item['cod']: item['id'] for item in res}

async def id_propval(entity: str, id_entity: int, cod_prop: str):
    query = f"""
        select pv.id, pv.prop from PropVal pv, Prop p
        where pv.prop=p.id and pv.{entity}={id_entity} and p.cod like '{cod_prop}'    
    """
    res = await select_query(query, {}, "dtj_model")
    if len(res) > 0:
        return res[0]["id"]
    else:
        raise 'NotFoundPossibleValues-{cod_prop}'

async def map_entity_id_from_pv(entity: str, cod_prop: str, key_is_propval: bool = False):
    query = f"""
        select pv.id, pv.factorVal from PropVal pv, Prop p
        where pv.prop=p.id and p.cod='{cod_prop}' and pv.{entity} is not null    
    """
    res = await select_query(query, {}, "dtj_model")
    if key_is_propval:
        return {item['id']: item[entity] for item in res}
    else:
        return {item[entity]: item['id'] for item in res}


async def close_all_pools():
    """Закрывает все открытые пулы при выключении"""
    for name, pool in pools.items():
        await pool.close()
        print(f"--- Пул БД '{name}' закрыт ---")
