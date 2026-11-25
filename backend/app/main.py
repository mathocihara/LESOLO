
import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.consulta import router as consultas_router
from app.routes.explicacao import router as explicacao_router
from app.routes.historico import router as historico_router
from app.routes.preferencias import router as preferencias_router
from app.routes.usuario import router as usuarios_router

from app.config.settings import settings
from app.database.conexao import SessionLocal, engine
from app.services.autenticacao import ServicoAutenticacao
from app.services.registro import ServicoRegistro

logger = logging.getLogger(__name__)


async def _limpar_contas_vencidas() -> None:
    """Executa a retenção definitiva de contas uma vez por hora."""
    while True:
        if engine is not None:
            try:
                with SessionLocal() as sessao:
                    removidas = ServicoAutenticacao(sessao).excluir_contas_vencidas()
                with SessionLocal() as sessao:
                    registros_removidos = ServicoRegistro(sessao).excluir_temporarios_vencidos()
                if removidas:
                    logger.info("Solicitações de exclusão vencidas processadas: %s", removidas)
                if registros_removidos:
                    logger.info("Registros temporários vencidos processados: %s", registros_removidos)
            except Exception:
                logger.exception("Falha ao processar solicitações de exclusão vencidas.")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_: FastAPI):
    tarefa = asyncio.create_task(_limpar_contas_vencidas())
    try:
        yield
    finally:
        tarefa.cancel()
        with suppress(asyncio.CancelledError):
            await tarefa


# ==========================================
# INICIALIZACAO DA API
# ==========================================

app = FastAPI(
    title=settings.APP_NAME,
    description="API do sistema LESOLO",
    version="1.0.0",
    lifespan=lifespan,
)


# ==========================================
# CONFIGURACAO CORS
# ==========================================

# Permite que o frontend React acesse o backend.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins(),
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
