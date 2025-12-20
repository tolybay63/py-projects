import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from db_utils import close_all_pools, select_query


# Определяем логику жизненного цикла
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Код здесь выполняется ПРИ СТАРТЕ ---
    print(">>> Сервер FastAPI запущен (Lifespan)")

    yield  # Здесь приложение работает и принимает запросы

    # --- Код здесь выполняется ПРИ ОСТАНОВКЕ ---
    await close_all_pools()
    print("<<< Сервер FastAPI остановлен, все соединения разорваны (Lifespan)")


# Передаем lifespan в конструктор FastAPI
app = FastAPI(lifespan=lifespan)

@app.get("/factor/{id}", tags=["Модель [Meta]: Факторы"], summary="Указанный фактор")
async def factor(id: int):
    query = "SELECT * FROM factor WHERE id = $1"
    # Запрос к базе 'dtj_model'
    data = await select_query(query, {"id": id},"dtj_model")
    return data


@app.get("/users", tags=["Модель [Admin]: Пользователи"], summary="Список пользователей")
async def users():
    query = "SELECT * FROM authuser WHERE 0=0"
    # Запрос к базе 'dtj_admin'
    # Пул для нее создастся автоматически при первом вызове
    data = await select_query(query, {},"dtj_admin")
    return data

@app.get("/plans", tags=["Модель [Plan]: Объекты"], summary="Список объектов")
async def factors():
    query = "SELECT * FROM obj o, objVer v WHERE o.id = v.ownerVer and v.lastVer=1"
    # Запрос к другой базе, например 'dtj_plandata'
    # Пул для нее создастся автоматически при первом вызове
    data = await select_query(query, {},"dtj_plandata")
    return data


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)










# import uvicorn
# from fastapi import FastAPI
#
# from prj2.db_select import db_select
#
# app = FastAPI()
#
#
# @app.get("/factors")
# async def factors():
#     query = "SELECT * FROM factor"
#     return await db_select(query, {}, "dtj_model")
#
#
# if __name__ == "__main__":
#     uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
