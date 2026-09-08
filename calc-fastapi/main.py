from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

from db_utils import (
    cod_id_from_entity,
    select_query,
    close_all_pools, load_reservoir_data, get_years
)


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


from fastapi import HTTPException

import json


@app.get("/calc_bayes/{calculation_id}/run", tags=["Модель [Calc]: Расчеты"])
async def run_calc_bayes(calculation_id: int):
    async def log_generator():
        try:
            yield f"[{calculation_id}] Старт выполнения расчета...\n"

            # Шаг 1: Основные свойства расчета
            yield f"[{calculation_id}] Шаг 1: Загрузка основных свойств расчета...\n"
            years = await get_years(calculation_id)
            yield f"[{calculation_id}] Период расчета: с {years['year1']} по {years['year2']} год.\n"

            # Шаг 2: Параметры водоема + тестовый вывод структуры
            yield f"[{calculation_id}] Шаг 2: Загрузка параметров водоема (Prop_WaterArea, Prop_CalcWaterFluct)...\n"
            reservoir_data = await load_reservoir_data(calculation_id, ["Prop_WaterArea", "Prop_CalcWaterFluct"])

            yield f"[{calculation_id}] Полученные данные водоема (тестовый вывод):\n"
            pretty_data = json.dumps(reservoir_data, ensure_ascii=False, indent=2)
            for line in pretty_data.split("\n"):
                yield f"  {line}\n"

            # Шаг 3: Следующий этап
            yield f"[{calculation_id}] Запуск расчетного алгоритма Байеса...\n"
            await asyncio.sleep(0.5)

            yield f"[{calculation_id}] Расчет успешно завершен!\n"

        except Exception as e:
            yield f"ОШИБКА НА СЕРВЕРЕ: {str(e)}\n"

    return StreamingResponse(log_generator(), media_type="text/plain; charset=utf-8")

#============================================




#============================================
@app.get(
    "/props/{id}",
    tags=["Модель [Calc]: Расчеты"],
    summary="Загрузка основных свойств расчета",
)
async def props(id: int = 1017):
    # 1. Забираем ID свойств из базы meta
    mp = await cod_id_from_entity(
      "Prop", ["Prop_CalcStartYear", "Prop_CalcEndYear"]
    )
    start_prop_id = mp.get("Prop_CalcStartYear")
    end_prop_id = mp.get("Prop_CalcEndYear")

    if not start_prop_id or not end_prop_id:
        raise HTTPException(
        status_code=404,
        detail=(
            "В базе meta не найдены обязательные свойства Prop_CalcStartYear"
            " или Prop_CalcEndYear"
        ),
    )

    # 2. Собираем SQL с подставленными ID свойств
    query = f"""
        select 
            v1.strVal as "CalcStartYear",
            v2.strVal as "CalcEndYear"
        from Obj o
            join DataProp d1 on d1.isObj=1 and d1.objOrRelObj=o.id and d1.prop={start_prop_id}
            join DataPropVal v1 on v1.dataprop=d1.id
            join DataProp d2 on d2.isObj=1 and d2.objOrRelObj=o.id and d2.prop={end_prop_id}
            join DataPropVal v2 on v2.dataprop=d2.id
        where o.id={id}
    """
    data = await select_query(query, {}, "fish_calc")

    # 3. Защита от падения, если расчет с таким ID вообще не существует
    if not data:
        raise HTTPException(
            status_code=404, detail=f"Расчет с ID {id} не найден в базе fish_calc"
        )
    return data[0]


@app.get("/reservoir", tags=["Модель [Calc]: Расчеты"], summary="Загрузка свойств водоема")
async def reservoir(id: int = 1017):
    mp = await cod_id_from_entity("Prop", ["Prop_CalcStartYear", "Prop_CalcEndYear"])
    query = f"""
        select 
            v1.strVal as CalcStartYear,
            v2.strVal as CalcEndYear
        from Obj o
            join DataProp d1 on d1.isObj=1 and d1.objOrRelObj=o.id and d1.prop={mp.get('Prop_CalcStartYear')}
            join DataPropVal v1 on v1.dataprop=d1.id
            join DataProp d2 on d2.isObj=1 and d2.objOrRelObj=o.id and d2.prop={mp.get('Prop_CalcEndYear')}
            join DataPropVal v2 on v2.dataprop=d2.id
        where o.id={id}
    """
    data = await select_query(query, {}, "fish_calc")
    return data



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
