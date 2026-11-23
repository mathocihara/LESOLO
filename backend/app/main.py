
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.consulta import router as consultas_router
from app.routes.explicacao import router as explicacao_router
from app.routes.historico import router as historico_router
from app.routes.preferencias import router as preferencias_router
from app.routes.usuario import router as usuarios_router

from app.config.settings import settings


# ==========================================
# INICIALIZACAO DA API
# ==========================================

app = FastAPI(
    title=settings.APP_NAME,
    description="API do sistema LESOLO",
    version="1.0.0"
)


# ==========================================
# CONFIGURACAO CORS
# ==========================================

# Permite que o frontend React acesse o backend.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# ROTA INICIAL
# ==========================================

@app.get("/")
def inicio():
    return {
        "mensagem": "API LESOLO funcionando!",
        "status": "online"
    }


# ==========================================
# VERIFICACAO DA API
# ==========================================

@app.get("/api/health")
def verificar_api():
    return {
        "sistema": "LESOLO",
        "status": "funcionando"
    }


app.include_router(consultas_router)
app.include_router(explicacao_router)
app.include_router(usuarios_router)
app.include_router(historico_router)
app.include_router(preferencias_router)
