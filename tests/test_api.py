import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402

cliente = TestClient(api.app)


def test_saude():
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_extrai_pedido(monkeypatch):
    monkeypatch.setattr(api, "gerar_texto", lambda m: (
        '{"itens":[{"produto":"espetinho de carne","qtd":2,"obs":null}],"endereco":null,"pagamento":"pix"}'))
    r = cliente.post("/extrair-pedido", json={"mensagem": "quero 2 de carne, pago no pix"})
    assert r.status_code == 200
    assert r.json()["itens"][0] == {"produto": "espetinho de carne", "qtd": 2, "obs": None}
    assert r.json()["pagamento"] == "pix"


def test_saida_invalida_vira_502(monkeypatch):
    monkeypatch.setattr(api, "gerar_texto", lambda m: "não sei")
    assert cliente.post("/extrair-pedido", json={"mensagem": "oi"}).status_code == 502


def test_mensagem_vazia_vira_422():
    assert cliente.post("/extrair-pedido", json={"mensagem": ""}).status_code == 422
