from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.settings import Settings, settings
from app.database.conexao import Base, obter_sessao
from app.main import app
from app.models import DadosGeograficos, Sessao, StatusRegistro
from app.repositories.usuario_repositorio import UsuarioRepositorio
from app.services.registro import ServicoRegistro
from app.services.preferencias_usuario import ServicoPreferenciasUsuario
from app.models.registro_consulta import RegistroConsulta
from app.models.preferencia_usuario import PreferenciaUsuario
from app.routes.dependencias import NOME_COOKIE_SESSAO


class _RespostaASGI:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def json(self):
        return json.loads(self._body) if self._body else None


class _ClienteASGI:
    """Cliente HTTP mínimo para os testes, sem dependência externa de httpx."""

    def __init__(self, aplicacao, cookies: dict[str, str] | None = None) -> None:
        self._aplicacao = aplicacao
        self._cookies: dict[str, str] = dict(cookies or {})

    def get(self, path: str) -> _RespostaASGI:
        return self.request("GET", path)

    def post(
        self,
        path: str,
        json_body: dict | None = None,
        *,
        include_origin: bool = True,
        origin: str | None = None,
        fetch_site: str | None = None,
    ) -> _RespostaASGI:
        return self.request(
            "POST", path, json_body, include_origin, origin, fetch_site
        )

    def put(
        self,
        path: str,
        json_body: dict | None = None,
        *,
        include_origin: bool = True,
        origin: str | None = None,
        fetch_site: str | None = None,
    ) -> _RespostaASGI:
        return self.request(
            "PUT", path, json_body, include_origin, origin, fetch_site
        )

    def patch(self, path: str, json_body: dict | None = None) -> _RespostaASGI:
        return self.request("PATCH", path, json_body)

    def delete(
        self,
        path: str,
        json_body: dict | None = None,
        *,
        include_origin: bool = True,
        origin: str | None = None,
        fetch_site: str | None = None,
    ) -> _RespostaASGI:
        return self.request("DELETE", path, json_body, include_origin, origin, fetch_site)

    def request(
        self,
        method: str,
        path: str,
        json_body: dict | None = None,
        include_origin: bool = True,
        origin: str | None = None,
        fetch_site: str | None = None,
    ) -> _RespostaASGI:
        return asyncio.run(
            self._request(method, path, json_body, include_origin, origin, fetch_site)
        )

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict | None,
        include_origin: bool,
        origin: str | None,
        fetch_site: str | None,
    ) -> _RespostaASGI:
        parsed_path = urlsplit(path)
        body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        headers = [(b"host", b"testserver"), (b"accept", b"application/json")]
        if include_origin:
            trusted_origin = origin if origin is not None else settings.frontend_origins()[0]
            headers.append((b"origin", trusted_origin.encode("ascii")))
        if fetch_site is not None:
            headers.append((b"sec-fetch-site", fetch_site.encode("ascii")))
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
        self.assertIn(f"max-age={settings.SESSION_TTL_SECONDS}", login.headers["set-cookie"].lower())
        self.assertIn("expires=", login.headers["set-cookie"].lower())
        self.assertNotIn("sessao", json.dumps(login.json()).lower())
        self.assertEqual(self.cliente.get("/api/preferencias").status_code, 200)

        navegador_reaberto = _ClienteASGI(app, cookies=self.cliente._cookies)
        self.assertEqual(navegador_reaberto.get("/api/usuarios/me").status_code, 200)
        with self.fabrica_sessoes() as sessao:
            usuario = UsuarioRepositorio(sessao).buscar_por_email("pessoa@example.test")
            sessao_db = sessao.query(Sessao).filter_by(usuario_id=usuario.id).one()
            self.assertTrue(sessao_db.persistente)

        logout = self.cliente.post("/api/usuarios/logout")
        self.assertEqual(logout.status_code, 204)
        expirada = self.cliente.get("/api/preferencias")
        self.assertEqual(expirada.status_code, 401)
        self.assertIn("max-age=0", expirada.headers.get("set-cookie", "").lower())
        self.assertEqual(navegador_reaberto.get("/api/preferencias").status_code, 401)

    def test_acesso_sem_autenticacao_e_rotas_existentes(self) -> None:
        self.assertEqual(self.cliente.get("/api/historico").status_code, 401)
        self.assertEqual(self.cliente.get("/api/preferencias").status_code, 401)

        caminhos = app.openapi()["paths"]
        self.assertIn("/api/consultas/consultar", caminhos)
        self.assertIn("/api/explicacao", caminhos)

    def test_consulta_repetida_permite_criar_atualizar_e_isola_usuarios(self) -> None:
        self._cadastro_e_login(self.cliente, "repetida-um@example.test")
        resultado_completo = {
            "latitude": -25.43,
            "longitude": -49.27,
            "altitude_m": 900.25,
            "declividade_percentual": 12.5,
            "tipo_solo": "Latossolo",
            "aptidao_agricola": "A1",
            "status_consulta": "COMPLETA",
            "dados_ausentes": [],
            "falhas_fontes": [],
        }
        with patch("app.routes.consulta.consultar_coordenada", return_value=resultado_completo):
            primeira = self.cliente.post(
                "/api/consultas/consultar", {"latitude": -25.43, "longitude": -49.27}
            )
        self.assertEqual(primeira.status_code, 200, primeira.json())
        registro_id = primeira.json()["id"]
        self.assertEqual(primeira.json()["status_consulta"], "COMPLETA")
        with self.fabrica_sessoes() as sessao:
            usuario = UsuarioRepositorio(sessao).buscar_por_email("repetida-um@example.test")
            ServicoRegistro(sessao).salvarComoPermanente(uuid.UUID(registro_id), usuario.id, "Talhão")

        with patch("app.routes.consulta.consultar_coordenada") as geo:
            repeticao = self.cliente.post(
                "/api/consultas/consultar",
                {"latitude": -25.4300004, "longitude": -49.2700004},
            )
            geo.assert_not_called()
        self.assertEqual(repeticao.status_code, 409)
        self.assertEqual(repeticao.json()["detail"]["code"], "CONSULTA_REPETIDA")
        self.assertEqual([item["id"] for item in repeticao.json()["detail"]["registros"]], [registro_id])

        resultado_parcial = {
            **resultado_completo,
            "altitude_m": None,
            "declividade_percentual": 15.0,
            "status_consulta": "PARCIAL",
            "dados_ausentes": ["altitude_m"],
            "falhas_fontes": ["altitude_m"],
        }
        with patch("app.routes.consulta.consultar_coordenada", return_value=resultado_parcial):
            atualizado = self.cliente.post(
                "/api/consultas/consultar",
                {
                    "latitude": -25.4300004,
                    "longitude": -49.2700004,
                    "acao_repeticao": "ATUALIZAR",
                    "registro_id": registro_id,
                },
            )
        self.assertEqual(atualizado.status_code, 200, atualizado.json())
        self.assertEqual(atualizado.json()["id"], registro_id)
        self.assertEqual(atualizado.json()["status"], "PERMANENTE")
        self.assertEqual(atualizado.json()["altitude_m"], 900.25)
        self.assertEqual(atualizado.json()["declividade_percentual"], 15.0)
        self.assertEqual(atualizado.json()["dados_desatualizados"], ["altitude_m"])

        with patch("app.routes.consulta.consultar_coordenada", return_value=resultado_completo):
            solicitar_novo = self.cliente.post(
                "/api/consultas/consultar", {"latitude": -25.43, "longitude": -49.27}
            )
            novo = self.cliente.post(
                "/api/consultas/consultar",
                {"latitude": -25.43, "longitude": -49.27, "acao_repeticao": "NOVO"},
            )
        self.assertEqual(solicitar_novo.status_code, 409)
        self.assertEqual(novo.status_code, 200, novo.json())
        self.assertNotEqual(novo.json()["id"], registro_id)

        outro_cliente = _ClienteASGI(app)
        self._cadastro_e_login(outro_cliente, "repetida-dois@example.test")
        with patch("app.routes.consulta.consultar_coordenada", return_value=resultado_completo):
            outra_conta = outro_cliente.post(
                "/api/consultas/consultar", {"latitude": -25.43, "longitude": -49.27}
            )
        self.assertEqual(outra_conta.status_code, 200, outra_conta.json())

        sem_resultados = {
            "latitude": -25.5,
            "longitude": -49.5,
            "altitude_m": None,
            "declividade_percentual": None,
            "tipo_solo": None,
            "aptidao_agricola": None,
            "status_consulta": "SEM_RESULTADOS",
            "dados_ausentes": ["altitude_m", "declividade_percentual", "tipo_solo", "aptidao_agricola"],
            "falhas_fontes": [],
        }
        with patch("app.routes.consulta.consultar_coordenada", return_value=sem_resultados):
            resposta_vazia = self.cliente.post(
                "/api/consultas/consultar", {"latitude": -25.5, "longitude": -49.5}
            )
        self.assertEqual(resposta_vazia.status_code, 200, resposta_vazia.json())
        self.assertEqual(resposta_vazia.json()["status_consulta"], "SEM_RESULTADOS")
        self.assertIsNone(resposta_vazia.json()["altitude_m"])
        self.assertEqual(resposta_vazia.json()["dados_ausentes"], sem_resultados["dados_ausentes"])
        with self.fabrica_sessoes() as sessao:
            registro = sessao.get(RegistroConsulta, uuid.UUID(resposta_vazia.json()["id"]))
            self.assertEqual(registro.status_consulta, "SEM_RESULTADOS")
            self.assertIsNone(registro.altitude_m)

    def test_rejeita_mutacoes_sem_origin_e_aceita_origem_confiavel(self) -> None:
        cadastro_sem_origem = self.cliente.post(
            "/api/usuarios/cadastro",
            {"nome": "Pessoa", "email": "sem-origin@example.test", "senha": "senha-segura-123"},
            include_origin=False,
        )
        self.assertEqual(cadastro_sem_origem.status_code, 403)

        self._cadastro_e_login(self.cliente, "csrf@example.test")
        sem_protecao = self.cliente.put(
            "/api/preferencias",
            {"tema": "claro"},
            include_origin=False,
        )
        self.assertEqual(sem_protecao.status_code, 403)

        origem_invalida = self.cliente.put(
            "/api/preferencias",
            {"tema": "claro"},
            origin="https://atacante.example",
            fetch_site="cross-site",
        )
        self.assertEqual(origem_invalida.status_code, 403)

        com_protecao = self.cliente.put("/api/preferencias", {"tema": "claro"})
        self.assertEqual(com_protecao.status_code, 200, com_protecao.json())

    def test_edita_dados_de_conta_com_reautenticacao_e_sem_expor_senha(self) -> None:
        cadastro = self.cliente.post(
            "/api/usuarios/cadastro",
            {"nome": "Pessoa Conta", "email": "conta-edicao@example.test", "senha": "senha-segura-123"},
        )
        self.assertEqual(cadastro.status_code, 201)
        self.assertEqual(self.cliente.post(
            "/api/usuarios/login",
            {"email": "conta-edicao@example.test", "senha": "senha-segura-123"},
        ).status_code, 200)

        sem_reautenticacao = self.cliente.patch(
            "/api/usuarios/me",
            {"nome": "Nome Novo", "senha_atual": "senha-incorreta"},
        )
        self.assertEqual(sem_reautenticacao.status_code, 400)

        atualizado = self.cliente.patch(
            "/api/usuarios/me",
            {
                "nome": "Pessoa Atualizada",
                "email": "pessoa-atualizada@example.test",
                "data_nascimento": "1990-05-12",
                "nova_senha": "senha-nova-123",
                "senha_atual": "senha-segura-123",
            },
        )
        self.assertEqual(atualizado.status_code, 200, atualizado.json())
        self.assertEqual(atualizado.json(), {
            "nome": "Pessoa Atualizada",
            "email": "pessoa-atualizada@example.test",
            "data_nascimento": "1990-05-12",
        })
        self.assertNotIn("senha", json.dumps(atualizado.json()).lower())
        self.assertNotIn("senha_hash", json.dumps(atualizado.json()).lower())
        with self.fabrica_sessoes() as sessao:
            usuario = UsuarioRepositorio(sessao).buscar_por_email("pessoa-atualizada@example.test")
            self.assertTrue(usuario.senha_hash.startswith("$argon2id$"))
        novo_login = _ClienteASGI(app).post(
            "/api/usuarios/login",
            {"email": "pessoa-atualizada@example.test", "senha": "senha-nova-123"},
        )
        self.assertEqual(novo_login.status_code, 200)

    def test_excluir_conta_exige_confirmacao_senha_e_preserva_outros_usuarios(self) -> None:
        self.cliente.post(
            "/api/usuarios/cadastro",
            {"nome": "Conta Excluída", "email": "conta-exclusao@example.test", "senha": "senha-segura-123"},
        )
        self.cliente.post(
            "/api/usuarios/login",
            {"email": "conta-exclusao@example.test", "senha": "senha-segura-123"},
        )
        outro_cliente = _ClienteASGI(app)
        outro_cliente.post(
            "/api/usuarios/cadastro",
            {"nome": "Conta Preservada", "email": "conta-preservada@example.test", "senha": "senha-segura-123"},
        )
        outro_cliente.post(
            "/api/usuarios/login",
            {"email": "conta-preservada@example.test", "senha": "senha-segura-123"},
        )

        with self.fabrica_sessoes() as sessao:
            usuario = UsuarioRepositorio(sessao).buscar_por_email("conta-exclusao@example.test")
            outro_usuario = UsuarioRepositorio(sessao).buscar_por_email("conta-preservada@example.test")
            self._criar_registro("conta-exclusao@example.test", StatusRegistro.PERMANENTE, datetime.now(timezone.utc))
            self._criar_registro("conta-preservada@example.test", StatusRegistro.PERMANENTE, datetime.now(timezone.utc))
            ServicoPreferenciasUsuario(sessao).buscar(usuario.id)
            ServicoPreferenciasUsuario(sessao).buscar(outro_usuario.id)
            usuario_id = usuario.id
            outro_usuario_id = outro_usuario.id

        sem_senha = self.cliente.delete(
            "/api/usuarios/me", {"senha_atual": "incorreta", "confirmacao": "EXCLUIR"}
        )
        self.assertEqual(sem_senha.status_code, 401)
        confirmada = self.cliente.delete(
            "/api/usuarios/me", {"senha_atual": "senha-segura-123", "confirmacao": "EXCLUIR"}
        )
        self.assertEqual(confirmada.status_code, 202)
        self.assertNotIn("max-age=0", confirmada.headers.get("set-cookie", "").lower())

        with self.fabrica_sessoes() as sessao:
            conta = UsuarioRepositorio(sessao).buscar_por_id(usuario_id)
            self.assertIsNotNone(conta)
            self.assertIsNotNone(conta.exclusao_solicitada_em)
            self.assertIsNotNone(UsuarioRepositorio(sessao).buscar_por_id(outro_usuario_id))
            self.assertEqual(sessao.query(RegistroConsulta).filter_by(usuario_id=usuario_id).count(), 1)
            self.assertEqual(sessao.query(PreferenciaUsuario).filter_by(usuario_id=usuario_id).count(), 1)
            self.assertEqual(sessao.query(Sessao).filter_by(usuario_id=usuario_id).count(), 1)
            self.assertEqual(sessao.query(RegistroConsulta).filter_by(usuario_id=outro_usuario_id).count(), 1)
            self.assertEqual(sessao.query(PreferenciaUsuario).filter_by(usuario_id=outro_usuario_id).count(), 1)
            self.assertEqual(sessao.query(Sessao).filter_by(usuario_id=outro_usuario_id).count(), 1)

        self.assertEqual(self.cliente.get("/api/usuarios/me").status_code, 200)
        with self.fabrica_sessoes() as sessao:
            conta = UsuarioRepositorio(sessao).buscar_por_id(usuario_id)
            self.assertIsNone(conta.exclusao_solicitada_em)

    def test_rejeita_sessao_expirada(self) -> None:
        self._cadastro_e_login(self.cliente, "expirada@example.test")
        valor_sessao = self.cliente._cookies[NOME_COOKIE_SESSAO]
        sessao_id = uuid.UUID(valor_sessao)

        with self.fabrica_sessoes() as sessao_banco:
            registro_sessao = sessao_banco.get(Sessao, sessao_id)
            registro_sessao.data_criacao = datetime.now(timezone.utc) - timedelta(
                seconds=settings.SESSION_TTL_SECONDS + 1
            )
            sessao_banco.commit()

        self.assertEqual(self.cliente.get("/api/preferencias").status_code, 401)
        with self.fabrica_sessoes() as sessao_banco:
            self.assertFalse(sessao_banco.get(Sessao, sessao_id).ativa)

    def test_cors_e_cookie_separam_desenvolvimento_e_producao(self) -> None:
        desenvolvimento = Settings(
            _env_file=None,
            APP_ENV="development",
            FRONTEND_URL="http://localhost:5173",
        )
        producao = Settings(
            _env_file=None,
            APP_ENV="production",
            FRONTEND_URL="https://lesolo.example.org",
        )

        self.assertEqual(desenvolvimento.frontend_origins(), ["http://localhost:5173"])
        self.assertFalse(desenvolvimento.secure_cookies)
        self.assertEqual(producao.frontend_origins(), ["https://lesolo.example.org"])
        self.assertTrue(producao.secure_cookies)
        with self.assertRaises(ValueError):
            Settings(
                _env_file=None,
                APP_ENV="production",
                FRONTEND_URL="*",
            ).frontend_origins()
        with self.assertRaises(ValueError):
            Settings(
                _env_file=None,
                APP_ENV="production",
                FRONTEND_URL="https://*.example.org",
            ).frontend_origins()
        with self.assertRaises(ValueError):
            Settings(
                _env_file=None,
                APP_ENV="production",
                FRONTEND_URL="http://localhost:5173",
            ).frontend_origins()

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
        temporario_consultado = self.cliente.get(f"/api/historico/{temporario.id}")
        self.assertEqual(temporario_consultado.status_code, 200)
        self.assertEqual(temporario_consultado.json()["status"], "TEMPORARIO")

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
