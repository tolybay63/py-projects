import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from db_utils import close_all_pools, select_query, cod_id_from_entity, id_propval


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

@app.get("/personnel")
async def load_personnel_by_position(pv_position: int=1256, cod_prop: str='Prop_Personnel'):
    cls_dict = await cod_id_from_entity("Cls", ["Cls_Personnel"])
    cls = cls_dict['Cls_Personnel']
    pv = await id_propval("cls", cls, cod_prop)
    params_prop = await cod_id_from_entity("Prop", ["Prop_UserSecondName", "Prop_UserFirstName", "Prop_UserMiddleName", "Prop_Position", "Prop_Location"])

    query = f"""
            select o.id, o.cls, v.name, v.fullName, {pv} as pv,
                v14.propVal as pvPosition, null as fvPosition, null as namePosition,
                v15.obj as objLocation, v15.propVal as pvLocation, null as nameLocation
            from Obj o 
                left join ObjVer v on o.id=v.ownerver and v.lastver=1
                left join DataProp d2 on d2.objorrelobj=o.id and d2.prop=$1
                left join DataPropVal v2 on d2.id=v2.dataprop
                left join DataProp d4 on d4.objorrelobj=o.id and d4.prop=$2
                left join DataPropVal v4 on d4.id=v4.dataprop
                left join DataProp d5 on d5.objorrelobj=o.id and d5.prop=$3
                left join DataPropVal v5 on d5.id=v5.dataprop
                left join DataProp d14 on d14.objorrelobj=o.id and d14.prop=$4
                inner join DataPropVal v14 on d14.id=v14.dataprop and v14.propVal={pv_position}     
                left join DataProp d15 on d15.objorrelobj=o.id and d15.prop=$5
                left join DataPropVal v15 on d15.id=v15.dataprop
            where o.cls={cls}
    """
    res = await select_query(query, params_prop, "dtj_personnaldata")
    return res

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
