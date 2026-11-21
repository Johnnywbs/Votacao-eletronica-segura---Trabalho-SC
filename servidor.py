import quadro
from assinatura import assinar, carregar_privada, gerar_par, privada_para_pem, publica_para_pem, verificar
from elgamal import cedula_de_json, elemento_valido
from params import G, P, Q
from provas import conferir_chaves, contexto_cedula, verificar_cedula
from util import (ErroVotacao, caminho_privado, caminho_publico, canonico, de_hex, gravar_json,
                  gravar_texto, ler_json, para_hex)

PREPARACAO, VOTACAO, ENCERRADA = "preparacao", "votacao", "encerrada"
MIN_CANDIDATOS = 2
MIN_AUTORIDADES = 3


def ler_publico(nome):
    return ler_json(caminho_publico(nome))


def exigir_fase(fase: str):
    atual = ler_publico("estado.json")["fase"]
    if atual != fase:
        raise ErroVotacao(f"Operação exige a fase '{fase}', mas a eleição está em '{atual}'")


def mudar_fase(fase: str):
    gravar_json(caminho_publico("estado.json"), {"fase": fase})


def configurar(id_eleicao: str, candidatos, n_autoridades: int):
    if len(candidatos) < MIN_CANDIDATOS:
        raise ErroVotacao(f"São necessários pelo menos {MIN_CANDIDATOS} candidatos")
    if len(set(candidatos)) != len(candidatos):
        raise ErroVotacao("Candidatos repetidos")
    if n_autoridades < MIN_AUTORIDADES:
        raise ErroVotacao(f"São necessárias pelo menos {MIN_AUTORIDADES} autoridades")
    chave = gerar_par()
    gravar_texto(caminho_privado("servidor", "chave.pem"), privada_para_pem(chave))
    gravar_json(caminho_publico("params.json"), {
        "eleicao": id_eleicao,
        "candidatos": list(candidatos),
        "n_autoridades": n_autoridades,
        "p": para_hex(P), "q": para_hex(Q), "g": para_hex(G),
        "chave_servidor": publica_para_pem(chave),
    })
    gravar_json(caminho_publico("autoridades.json"), {"autoridades": {}, "chave_conjunta": None})
    gravar_json(caminho_publico("eleitores.json"), {"eleitores": {}})
    mudar_fase(PREPARACAO)


def cadastrar(id_eleitor: str, chave_publica_pem: str):
    exigir_fase(PREPARACAO)
    dados = ler_publico("eleitores.json")
    if id_eleitor in dados["eleitores"]:
        raise ErroVotacao(f"Eleitor '{id_eleitor}' já cadastrado")
    dados["eleitores"][id_eleitor] = chave_publica_pem
    gravar_json(caminho_publico("eleitores.json"), dados)


def abrir_votacao():
    exigir_fase(PREPARACAO)
    params = ler_publico("params.json")
    autoridades = ler_publico("autoridades.json")
    eleitores = ler_publico("eleitores.json")
    conferir_chaves(params["eleicao"], params["n_autoridades"], autoridades)
    if not eleitores["eleitores"]:
        raise ErroVotacao("Nenhum eleitor cadastrado")
    quadro.criar(quadro.calcular_genese(params, autoridades, eleitores))
    mudar_fase(VOTACAO)


def mensagem_cedula(id_eleicao: str, id_eleitor: str, cedula_json, provas_cedula) -> bytes:
    return canonico({"eleicao": id_eleicao, "eleitor": id_eleitor, "cedula": cedula_json, "provas": provas_cedula})


def validar_cedula(params, id_eleitor: str, cedula_json, provas_cedula):
    try:
        cedula = cedula_de_json(cedula_json)
    except (TypeError, ValueError):
        raise ErroVotacao("Cédula mal formada") from None
    if len(cedula) != len(params["candidatos"]):
        raise ErroVotacao("Cédula com número errado de cifras")
    if not all(elemento_valido(c1) and elemento_valido(c2) for c1, c2 in cedula):
        raise ErroVotacao("Cédula com valores fora do grupo")
    h = de_hex(ler_publico("autoridades.json")["chave_conjunta"])
    if not verificar_cedula(h, cedula, provas_cedula, contexto_cedula(params["eleicao"], id_eleitor)):
        raise ErroVotacao("Prova de validade inválida: cada cifra deve conter 0 ou 1 e a cédula exatamente um voto")


def receber_cedula(id_eleitor: str, cedula_json, provas_cedula, assinatura_eleitor: str):
    exigir_fase(VOTACAO)
    params = ler_publico("params.json")
    eleitores = ler_publico("eleitores.json")["eleitores"]
    if id_eleitor not in eleitores:
        raise ErroVotacao(f"Eleitor '{id_eleitor}' não cadastrado (elegibilidade)")
    mensagem = mensagem_cedula(params["eleicao"], id_eleitor, cedula_json, provas_cedula)
    if not verificar(eleitores[id_eleitor], mensagem, assinatura_eleitor):
        raise ErroVotacao("Assinatura do eleitor inválida")
    if quadro.ja_votou(id_eleitor):
        raise ErroVotacao(f"Eleitor '{id_eleitor}' já votou (unicidade)")
    validar_cedula(params, id_eleitor, cedula_json, provas_cedula)
    entrada = quadro.acrescentar(id_eleitor, cedula_json, provas_cedula, assinatura_eleitor)
    return emitir_recibo(params["eleicao"], entrada)


def assinar_como_servidor(conteudo) -> str:
    chave = carregar_privada(caminho_privado("servidor", "chave.pem").read_text(encoding="utf-8"))
    return assinar(chave, canonico(conteudo))


def emitir_recibo(id_eleicao: str, entrada):
    conteudo = {"eleicao": id_eleicao, "indice": entrada["indice"], "hash_entrada": entrada["hash"]}
    return {**conteudo, "assinatura_servidor": assinar_como_servidor(conteudo)}


def encerrar():
    exigir_fase(VOTACAO)
    atual = quadro.ler()
    conteudo = {
        "eleicao": ler_publico("params.json")["eleicao"],
        "total_cedulas": len(atual["entradas"]),
        "hash_final": quadro.ultimo_hash(atual),
    }
    gravar_json(caminho_publico("cabeca.json"), {**conteudo, "assinatura_servidor": assinar_como_servidor(conteudo)})
    mudar_fase(ENCERRADA)
    return conteudo["hash_final"]
