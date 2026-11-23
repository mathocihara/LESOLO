from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.conexao import Base, obter_sessao
from app.main import app
from app.models import DadosGeograficos, StatusRegistro
from app.repositories.usuario_repositorio import UsuarioRepositorio
from app.services.registro import ServicoRegistro


class _RespostaASGI:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def json(self):
        return json.loads(self._body) if self._body else None


class _ClienteASGI:
    """Cliente HTTP mínimo para os testes, sem dependência externa de httpx."""

    def __init__(self, aplicacao) -> None:
        self._aplicacao = aplicacao
        self._cookies: dict[str, str] = {}

    def get(self, path: str) -> _RespostaASGI:
        return self.request("GET", path)

    def post(self, path: str, json_body: dict | None = None) -> _RespostaASGI:
        return self.request("POST", path, json_body)

    def put(self, path: str, json_body: dict | None = None) -> _RespostaASGI:
        return self.request("PUT", path, json_body)

    def delete(self, path: str) -> _RespostaASGI:
        return self.request("DELETE", path)

    def request(
        self,
        method: str,
        path: str,
        json_body: dict | None = None,
    ) -> _RespostaASGI:
        return asyncio.run(self._request(method, path, json_body))

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict | None,
    ) -> _RespostaASGI:
        parsed_path = urlsplit(path)
        body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        headers = [(b"host", b"testserver"), (b"accept", b"application/json")]
        if json_body is not None:
            headers.extend(
                [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ]
            )
        if self._cookies:
            cookie_header = "; ".join(
                f"{name}={value}" for name, value in self._cookies.items()
            )
            headers.append((b"cookie", cookie_header.encode("ascii")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": parsed_path.path,
            "raw_path": parsed_path.path.encode("utf-8"),
            "query_string": parsed_path.query.encode("ascii"),
            "root_path": "",
            "headers": headers,
            "client": ("testclient", 12345),
            "server": ("testserver", 80),
            "state": {},
        }
        mensagens = []
        corpo_enviado = False

        async def receber():
            nonlocal corpo_enviado
            if not corpo_enviado:
                corpo_enviado = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def enviar(mensagem):
            mensagens.append(mensagem)

        await self._aplicacao(scope, receber, enviar)
        inicio = next(item for item in mensagens if item["type"] == "http.response.start")
        corpo = b"".join(
            item.get("body", b"")
            for item in mensagens
            if item["type"] == "http.response.body"
        )
        cabecalhos_resposta: dict[str, str] = {}
        for nome, valor in inicio.get("headers", []):
            nome_texto = nome.decode("latin-1").lower()
            valor_texto = valor.decode("latin-1")
            if nome_texto == "set-cookie":
                self._atualizar_cookies(valor_texto)
            cabecalhos_resposta[nome_texto] = valor_texto
        return _RespostaASGI(inicio["status"], cabecalhos_resposta, corpo)

    def _atualizar_cookies(self, cabecalho: str) -> None:
        cookies = SimpleCookie()
        cookies.load(cabecalho)
        for nome, cookie in cookies.items():
            if cookie.value == "" or cookie["max-age"] == "0":
                self._cookies.pop(nome, None)
            else:
                self._cookies[nome] = cookie.value


class TesteRotasAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.fabrica_sessoes = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            expire_on_commit=False,
        )

        def obter_sessao_teste():
            sessao = cls.fabrica_sessoes()
            try:
                yield sessao
            finally:
                sessao.close()

        cls.obter_sessao_teste = staticmethod(obter_sessao_teste)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.pop(obter_sessao, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        app.dependency_overrides[obter_sessao] = self.obter_sessao_teste
        self.cliente = _ClienteASGI(app)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(obter_sessao, None)

    def _cadastro_e_login(self, cliente: _ClienteASGI, email: str) -> None:
        cadastro = cliente.post(
            "/api/usuarios/cadastro",
            {"nome": "Pessoa de Teste", "email": email, "senha": "senha-segura-123"},
        )
        self.assertEqual(cadastro.status_code, 201, cadastro.json())
        login = cliente.post(
            "/api/usuarios/login",
            {"email": email, "senha": "senha-segura-123"},
        )
        self.assertEqual(login.status_code, 200, login.json())

    def _criar_registro(
        self,
        email: str,
        status: StatusRegistro,
        data_consulta: datetime,
    ):
        with self.fabrica_sessoes() as sessao:
            usuario = UsuarioRepositorio(sessao).buscar_por_email(email)
            return ServicoRegistro(sessao).criarTemporario(
                usuarioId=usuario.id,
                latitude=Decimal("-25.43"),
                longitude=Decimal("-49.27"),
                dadosGeograficos=DadosGeograficos(
                    mde=Decimal("900.25"),
                    declividade=Decimal("12.5"),
                    tipo_solo="Latossolo",
                    aptidao_agricola="A1",
                ),
                dataConsulta=data_consulta,
            )

    def test_cadastro_login_logout_e_resposta_sem_segredos(self) -> None:
        cadastro = self.cliente.post(
            "/api/usuarios/cadastro",
            {
                "nome": "  Pessoa Um ",
                "email": "  pessoa@example.test ",
                "senha": "senha-segura-123",
            },
        )
        self.assertEqual(cadastro.status_code, 201, cadastro.json())
        self.assertEqual(cadastro.json(), {"nome": "Pessoa Um", "email": "pessoa@example.test"})
        self.assertNotIn("senha", cadastro.json())
        self.assertNotIn("senha_hash", cadastro.json())

        login = self.cliente.post(
            "/api/usuarios/login",
            {"email": "pessoa@example.test", "senha": "senha-segura-123"},
        )
        self.assertEqual(login.status_code, 200, login.json())
        self.assertIn("set-cookie", login.headers)
        self.assertIn("httponly", login.headers["set-cookie"].lower())
        self.assertNotIn("sessao", json.dumps(login.json()).lower())

        logout = self.cliente.post("/api/usuarios/logout")
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(self.cliente.get("/api/preferencias").status_code, 401)

    def test_acesso_sem_autenticacao_e_rotas_existentes(self) -> None:
        self.assertEqual(self.cliente.get("/api/historico").status_code, 401)
        self.assertEqual(self.cliente.get("/api/preferencias").status_code, 401)

        caminhos = app.openapi()["paths"]
        self.assertIn("/api/consultas/consultar", caminhos)
        self.assertIn("/api/explicacao", caminhos)

    def test_historico_isolado_salvar_excluir_e_limpar(self) -> None:
        outro_cliente = _ClienteASGI(app)
        self._cadastro_e_login(self.cliente, "um@example.test")
        self._cadastro_e_login(outro_cliente, "dois@example.test")

        permanente = self._criar_registro(
            "um@example.test",
            StatusRegistro.TEMPORARIO,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        with self.fabrica_sessoes() as sessao:
            ServicoRegistro(sessao).salvarComoPermanente(
                permanente.id,
                UsuarioRepositorio(sessao).buscar_por_email("um@example.test").id,
                "Registro próprio",
            )
        temporario = self._criar_registro(
            "um@example.test",
            StatusRegistro.TEMPORARIO,
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        registro_alheio = self._criar_registro(
            "dois@example.test",
            StatusRegistro.TEMPORARIO,
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
        with self.fabrica_sessoes() as sessao:
            ServicoRegistro(sessao).salvarComoPermanente(
                registro_alheio.id,
                UsuarioRepositorio(sessao).buscar_por_email("dois@example.test").id,
                "Registro de outra pessoa",
            )

        historico = self.cliente.get("/api/historico")
        self.assertEqual(historico.status_code, 200)
        self.assertEqual([item["id"] for item in historico.json()], [str(permanente.id)])
        self.assertEqual(
            self.cliente.get(f"/api/historico/{registro_alheio.id}").status_code,
            404,
        )
        self.assertEqual(self.cliente.get(f"/api/historico/{temporario.id}").status_code, 404)

        salvo = self.cliente.post(f"/api/historico/{temporario.id}/salvar", {})
        self.assertEqual(salvo.status_code, 200, salvo.json())
        self.assertEqual(salvo.json()["status"], "PERMANENTE")
        self.assertIsNotNone(salvo.json()["nome"])
        self.assertEqual(
            self.cliente.delete(f"/api/historico/{registro_alheio.id}").status_code,
            404,
        )
        self.assertEqual(self.cliente.delete(f"/api/historico/{temporario.id}").status_code, 204)

        permanente_novo = self._criar_registro(
            "um@example.test",
            StatusRegistro.TEMPORARIO,
            datetime(2026, 1, 4, tzinfo=timezone.utc),
        )
        with self.fabrica_sessoes() as sessao:
            ServicoRegistro(sessao).salvarComoPermanente(
                permanente_novo.id,
                UsuarioRepositorio(sessao).buscar_por_email("um@example.test").id,
                "Outro próprio",
            )
        temporario_preservado = self._criar_registro(
            "um@example.test",
            StatusRegistro.TEMPORARIO,
            datetime(2026, 1, 5, tzinfo=timezone.utc),
        )

        limpeza = self.cliente.delete("/api/historico")
        self.assertEqual(limpeza.status_code, 200, limpeza.json())
        self.assertEqual(limpeza.json(), {"excluidos": 2})
        self.assertEqual(self.cliente.get("/api/historico").json(), [])
        temporarios_restantes = self.cliente.get("/api/historico?status=TEMPORARIO")
        self.assertEqual(temporarios_restantes.status_code, 200)
        self.assertEqual(
            [item["id"] for item in temporarios_restantes.json()],
            [str(temporario_preservado.id)],
        )
        self.assertEqual(len(outro_cliente.get("/api/historico").json()), 1)

    def test_atualizacao_de_preferencias_isolada_por_usuario(self) -> None:
        outro_cliente = _ClienteASGI(app)
        self._cadastro_e_login(self.cliente, "prefs-um@example.test")
        self._cadastro_e_login(outro_cliente, "prefs-dois@example.test")

        padrao = self.cliente.get("/api/preferencias")
        padrao_outro = outro_cliente.get("/api/preferencias")
        self.assertEqual(padrao.status_code, 200)
        self.assertEqual(
            padrao.json(),
            {"tema": "escuro", "alto_contraste": False, "notificacoes": False},
        )
        self.assertEqual(padrao_outro.json()["tema"], "escuro")

        atualizada = self.cliente.put(
            "/api/preferencias",
            {"tema": "claro", "alto_contraste": True, "notificacoes": True},
        )
        self.assertEqual(atualizada.status_code, 200, atualizada.json())
        self.assertEqual(atualizada.json()["tema"], "claro")
        self.assertTrue(atualizada.json()["alto_contraste"])
        self.assertTrue(atualizada.json()["notificacoes"])
        self.assertEqual(outro_cliente.get("/api/preferencias").json(), padrao_outro.json())
        self.assertEqual(
            self.cliente.put("/api/preferencias", {"usuario_id": str(uuid.uuid4())}).status_code,
            422,
        )


if __name__ == "__main__":
    unittest.main()
