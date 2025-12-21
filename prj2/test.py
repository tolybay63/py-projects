import asyncio

from db_utils import select_query, cod_id_from_entity


async def test1():
    print("test1")
    query = "SELECT id, cod FROM prop WHERE cod like 'Prop_%'"
    res1 = await select_query(query, {}, "dtj_model")
    result_dict = {item['cod']: item['id'] for item in res1}
    print(result_dict)

    keys = ['Prop_Position', 'Prop_NumberSource', 'Prop_Description']
    filtered_dict = {k: result_dict[k] for k in keys if k in result_dict}
    filtered_dict.setdefault("cls", 1000)

    print(filtered_dict)

async def test2(entity: str, cods: list):
    print("test2")
    query = f"SELECT id, cod FROM {entity} WHERE cod like '{entity}_%'"
    res1 = await select_query(query, {}, "dtj_model")
    result_dict = {item['cod']: item['id'] for item in res1}
    filtered_dict = {k: result_dict[k] for k in cods if k in result_dict}

    print(filtered_dict)

async def test2_map(entity: str, cod: str):
    print("test2_map")
    query = f"SELECT id, cod FROM {entity} WHERE cod like '{cod}'"
    res1 = await select_query(query, {}, "dtj_model")
    result_dict = {item['cod']: item['id'] for item in res1}
    print(result_dict)


async def test3(entity: str, id_entity: int, cod_prop: str):
    print("test3")
    query = f"""
        select pv.id, pv.prop from PropVal pv, Prop p
        where pv.prop=p.id and pv.{entity}={id_entity} and p.cod like '{cod_prop}'    
    """
    res = await select_query(query, {}, "dtj_model")
    if len(res) > 0:
        print(res[0]["id"])
    else:
        raise 'NotFoundPossibleValues-{cod_prop}'


async def test4():
    print("test4")
    params_prop = await cod_id_from_entity("Prop", ["Prop_UserSecondName", "Prop_UserFirstName", "Prop_UserMiddleName", "Prop_Position", "Prop_Location"])
    print("params_prop", params_prop)

async def test4_1():
    await test2("Prop", ["Prop_UserSecondName", "Prop_UserFirstName", "Prop_UserMiddleName", "Prop_Position", "Prop_Location"])

async def map_entity_id_from_pv(entity: str, cod_prop: str, key_is_propval: bool = False):
    query = f"""
        select pv.id, pv.factorVal from PropVal pv, Prop p
        where pv.prop=p.id and p.cod='{cod_prop}' and pv.{entity} is not null    
    """
    res = await select_query(query, {}, "dtj_model")

    print( res )
    if key_is_propval:
        rr = {item['id']: item[entity] for item in res}
    else:
        rr = {item[entity]: item['id'] for item in res}

    print( rr )

#asyncio.run(test1())
#asyncio.run(test2("Cls", ["Cls_Personnel"]))
#asyncio.run(test3("Cls", 1150,"Prop_ObjectType"))
#asyncio.run(test4())
#asyncio.run(test4_1())

#asyncio.run(test2_map("Prop", "Prop_UserSecondName"))
#asyncio.run(test2_map("Prop", "Prop_User%"))
asyncio.run(map_entity_id_from_pv("factorval", "Prop_Position", True))
