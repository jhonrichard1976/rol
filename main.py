import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, ForeignKey
from databases import Database
from typing import List, Optional
from fastapi import Path
DATABASE_URL = os.environ.get("PG_URL", "postgresql://postgres:1234@192.168.1.153/sigte_auth")
database = Database(DATABASE_URL)
metadata = MetaData()

# Define a new table with SQLAlchemy
asignaciones_rol = Table(
    "asignaciones_rol",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("rol_id", Integer),
    Column("user_id", Integer),
    Column("code_rol", Integer),
)


# Define Pydantic models/schemas
class AsignacionesRolIn(BaseModel):
    rol_id: Optional[int] = None
    user_id: Optional[int] = None
    code_rol: Optional[int] = None


class AsignacionesRol(BaseModel):
    id: int
    rol_id: int
    user_id: int
    code_rol: int


app = FastAPI()


# Event handlers to set up and close database connection
@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


# Endpoints
@app.post("/asignaciones/", response_model=AsignacionesRol)
async def create_role_assignment(assignment: AsignacionesRolIn):
    # Verificar si ya existe la asignación
    existing_query = asignaciones_rol.select().where(
        (asignaciones_rol.c.user_id == assignment.user_id) &
        (asignaciones_rol.c.rol_id == assignment.rol_id)
    )
    existing_assignment = await database.fetch_one(existing_query)

    if existing_assignment:
        raise HTTPException(
            status_code=409,
            detail=f"El usuario con ID {assignment.user_id} ya tiene asignado el rol con ID {assignment.rol_id}"
        )

    # Crear nueva asignación si no existe
    query = asignaciones_rol.insert().values(**assignment.dict())
    last_record_id = await database.execute(query)
    return {**assignment.dict(), "id": last_record_id}



@app.get("/asignaciones/", response_model=List[AsignacionesRol])
async def read_all_role_assignments():
    query = asignaciones_rol.select()
    return await database.fetch_all(query)


@app.get("/asignaciones/user/{user_id}", response_model=List[AsignacionesRol])
async def read_role_assignments_by_user(user_id: int):
    query = asignaciones_rol.select().where(asignaciones_rol.c.user_id == user_id)
    return await database.fetch_all(query)

@app.get("/asignaciones/user/{user_id}/codes", response_model=List[int])
async def read_role_codes_by_user(user_id: int):
    query = asignaciones_rol.select().where(asignaciones_rol.c.user_id == user_id)
    result = await database.fetch_all(query)
    role_codes = [item['code_rol'] for item in result]
    return role_codes

@app.patch("/asignaciones/{asignacion_id}", response_model=AsignacionesRol)
async def update_role(asignacion_id: int, role: AsignacionesRolIn):
    update_data = role.model_dump(exclude_unset=True)
    query = asignaciones_rol.update().where(asignaciones_rol.c.id == asignacion_id).values(**update_data)
    await database.execute(query)

    # Recuperar y devolver la entidad actualizada
    query = asignaciones_rol.select().where(asignaciones_rol.c.id == asignacion_id)
    updated_role = await database.fetch_one(query)
    if updated_role is not None:
        return updated_role
    raise HTTPException(status_code=404, detail=f"Asignacion con id {asignacion_id} not found")


@app.delete("/asignaciones/{asignacion_id}", response_model=dict)
async def delete_role_assignment(asignacion_id: int):
    # Verificar si la asignación existe
    exists_query = asignaciones_rol.select().where(asignaciones_rol.c.id == asignacion_id)
    existing_assignment = await database.fetch_one(exists_query)

    if not existing_assignment:
        raise HTTPException(
            status_code=404,
            detail=f"Asignación con id {asignacion_id} no encontrada"
        )

    # Eliminar la asignación si existe
    delete_query = asignaciones_rol.delete().where(asignaciones_rol.c.id == asignacion_id)
    await database.execute(delete_query)
    return {"message": f"Asignación con id {asignacion_id} eliminada correctamente"}



# Add more endpoints as needed for CRUD operations
