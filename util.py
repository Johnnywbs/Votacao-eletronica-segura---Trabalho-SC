import hashlib
import json
import os
from pathlib import Path


class ErroVotacao(Exception):
    pass


def raiz() -> Path:
    return Path(os.environ.get("VOTACAO_DIR", "."))


def caminho_publico(nome: str) -> Path:
    return raiz() / "publico" / nome


def caminho_privado(entidade: str, nome: str) -> Path:
    return raiz() / "privado" / entidade / nome


def canonico(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def para_hex(n: int) -> str:
    return format(n, "x")


def de_hex(texto: str) -> int:
    return int(texto, 16)


def ler_json(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def gravar_json(caminho, obj):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(obj, arquivo, indent=2, ensure_ascii=False)


def gravar_texto(caminho, texto: str):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
