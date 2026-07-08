import psycopg2
import uvicorn
from fastapi import FastAPI
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host="127.0.0.1",
    user = "pg",
    password = "1q2w3e4R",
    port = "5432",
    dbname = "dtj_model"
)
if conn:
    print("Подключено")

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в Fast API!"}

@app.get("/factors", tags=["Факторы"], summary="Список всех факторов")
async def factors():
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("select * from factor where parent is null")
    results = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in results]


@app.get("/factor/{id}", tags=["Факторы"], summary="Указанный фактор")
async def factor(id: int):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("select * from factor where id={}".format(id))
    results = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in results]

@app.get("/factors_vals", tags=["Факторы"], summary="Список всех факторов со значениями")
async def factors_vals():
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("select * from factor")
    results = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in results]


@app.get("/factor_vals/{id}", tags=["Факторы"], summary="Список значений указанного фактора")
async def factor_vals(id: int):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("select * from factor where id={0} and parent is null union select * from factor where parent={0}".format(id, id))
    results = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in results]


@app.get("/factor_vals_by_cod/{cod_factor}", tags=["Факторы"], summary="Список значений указанного фактора")
async def factor_vals(cod_factor: str):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
            select fv.id, fv.cod, fv.name
            from Factor fv
                     join Factor f on fv.parent = f.id
            where f.cod = %s
            order by fv.ord \
            """

    cursor.execute(query, (cod_factor,))

    results = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in results]


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


