from util import caminho_publico, canonico, gravar_json, ler_json, sha256_hex

ARQUIVO = "quadro.json"


def calcular_genese(params, autoridades, eleitores) -> str:
    return sha256_hex(canonico({"params": params, "autoridades": autoridades, "eleitores": eleitores}))


def hash_entrada(entrada) -> str:
    sem_hash = {chave: valor for chave, valor in entrada.items() if chave != "hash"}
    return sha256_hex(canonico(sem_hash))


def criar(genese: str):
    gravar_json(caminho_publico(ARQUIVO), {"genese": genese, "entradas": []})


def ler():
    return ler_json(caminho_publico(ARQUIVO))


def ultimo_hash(quadro) -> str:
    entradas = quadro["entradas"]
    return entradas[-1]["hash"] if entradas else quadro["genese"]


def ja_votou(id_eleitor: str) -> bool:
    return any(entrada["eleitor"] == id_eleitor for entrada in ler()["entradas"])


def acrescentar(id_eleitor: str, cedula_json, provas_cedula, assinatura_eleitor: str):
    quadro = ler()
    entrada = {
        "indice": len(quadro["entradas"]),
        "eleitor": id_eleitor,
        "cedula": cedula_json,
        "provas": provas_cedula,
        "assinatura": assinatura_eleitor,
        "hash_anterior": ultimo_hash(quadro),
    }
    entrada["hash"] = hash_entrada(entrada)
    quadro["entradas"].append(entrada)
    gravar_json(caminho_publico(ARQUIVO), quadro)
    return entrada
