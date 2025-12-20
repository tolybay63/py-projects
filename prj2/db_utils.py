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


async def close_all_pools():
    """Закрывает все открытые пулы при выключении"""
    for name, pool in pools.items():
        await pool.close()
        print(f"--- Пул БД '{name}' закрыт ---")
