from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controller.rotas import rota_contrato


app = FastAPI(title="ContratosCheck")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(rota_contrato)
