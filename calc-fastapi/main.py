from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI

from db_utils import close_all_pools, select_query, cod_id_from_entity, ids_from_entity_cods


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
app = FastAPI(
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в Fast API!"}


@app.get("/calc_bayes", tags=["Модель [Calc]: Расчеты"], summary="Расчет по методу Байеса")
async def calc_bayes(id: int = 1012):
    #m1 = await cod_id_from_entity("Prop", ["Prop_WaterArea", "Prop_CalcWaterFluct"])
    #print(m1)

    m2 = await ids_from_entity_cods("Prop", ["Prop_WaterArea", "Prop_CalcWaterFluct"])
    print("m2", m2)

    whe = "(" + ",".join(f"{it}" for it in m2) + ")"


    # Расчет...
    # ...
    return whe


@app.post("/factors", tags=["Модель [Meta]: Факторы"], summary="Список факторов")
async def factors():
    query = "SELECT * FROM factor WHERE 0=0"
    # Запрос к базе 'fish_model'
    data = await select_query(query, {},"fish_model")
    return data


@app.get("/factor_vals_by_cod/{cod_factor}", tags=["Факторы"], summary="Список значений указанного фактора")
async def factor_vals(cod_factor: str="Factor_FishType"):
    query = f"""
            select fv.id, fv.cod, fv.name
            from Factor fv
                     join Factor f on fv.parent = f.id
            where f.cod = $1
            order by fv.ord
    """

    data = await select_query(query, {"cod_factor": cod_factor}, "fish_model")
    return data




@app.get("/load_dict/{dict_name}", tags=["Словари"], summary="Список значений указанного словаря")
async def factor_vals(dict_name: str="fd_accesslevel"):
    query = f"""
        select id, text 
        from {dict_name} 
        where vis=1
        order by ord
    """
    data = await select_query(query, {}, "fish_model")
    return data


@app.get("/users", tags=["Модель [Admin]: Пользователи"], summary="Список пользователей")
async def users():
    query = "SELECT * FROM authuser WHERE 0=0"
    # Запрос к базе 'dtj_admin'
    # Пул для нее создастся автоматически при первом вызове
    data = await select_query(query, {},"dtj_admin")
    return data


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
