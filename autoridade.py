import quadro
import servidor
from elgamal import aleatorio_zq, apurar, cedula_de_json, elemento_valido, log_discreto
from params import G, P
from provas import (conferir_chaves, contexto_chave, contexto_decifracao, produto_das_chaves,
                    provar_conhecimento, provar_mesmo_log, verificar_mesmo_log)
from util import ErroVotacao, caminho_privado, caminho_publico, de_hex, gravar_json, ler_json, para_hex


def pasta(id_autoridade: int) -> str:
    return f"autoridade_{id_autoridade}"


def ler_privado(id_autoridade: int):
    caminho = caminho_privado(pasta(id_autoridade), "chave.json")
    if not caminho.exists():
        raise ErroVotacao(f"Autoridade {id_autoridade} não gerou chave")
    return ler_json(caminho)


def gerar_chave(id_autoridade: int):
    servidor.exigir_fase(servidor.PREPARACAO)
    params = servidor.ler_publico("params.json")
    n = params["n_autoridades"]
    dados = servidor.ler_publico("autoridades.json")
    if not 1 <= id_autoridade <= n:
        raise ErroVotacao(f"Id de autoridade deve estar entre 1 e {n}")
    if str(id_autoridade) in dados["autoridades"]:
        raise ErroVotacao(f"Autoridade {id_autoridade} já gerou sua chave")
    x = aleatorio_zq()
    h = pow(G, x, P)
    gravar_json(caminho_privado(pasta(id_autoridade), "chave.json"), {"x": para_hex(x), "h": para_hex(h)})
    prova = provar_conhecimento(x, h, contexto_chave(params["eleicao"], id_autoridade))
    dados["autoridades"][str(id_autoridade)] = {"h": para_hex(h), "prova": prova}
    if len(dados["autoridades"]) == n:
        dados["chave_conjunta"] = para_hex(produto_das_chaves(params["eleicao"], n, dados))
    gravar_json(caminho_publico("autoridades.json"), dados)


def conferir(id_autoridade: int) -> str:
    params = servidor.ler_publico("params.json")
    dados = servidor.ler_publico("autoridades.json")
    h = de_hex(ler_privado(id_autoridade)["h"])
    publicado = dados["autoridades"].get(str(id_autoridade), {}).get("h")
    if publicado != para_hex(h):
        raise ErroVotacao(f"O h_{id_autoridade} publicado não é o desta autoridade: chave substituída")
    conferir_chaves(params["eleicao"], params["n_autoridades"], dados)
    return dados["chave_conjunta"]


def chave_publica(id_autoridade) -> int:
    return de_hex(servidor.ler_publico("autoridades.json")["autoridades"][str(id_autoridade)]["h"])


def produto_do_quadro():
    params = servidor.ler_publico("params.json")
    cedulas = [cedula_de_json(entrada["cedula"]) for entrada in quadro.ler()["entradas"]]
    return apurar(cedulas, len(params["candidatos"]))


def ler_apuracao():
    caminho = caminho_publico("apuracao.json")
    return ler_json(caminho) if caminho.exists() else {"produto": None, "parciais": {}}


def decifrar_parcial(id_autoridade: int):
    servidor.exigir_fase(servidor.ENCERRADA)
    x = de_hex(ler_privado(id_autoridade)["x"])
    h_i = chave_publica(id_autoridade)
    eleicao = servidor.ler_publico("params.json")["eleicao"]
    produto = produto_do_quadro()
    parciais = []
    for j, (c1, _) in enumerate(produto):
        d = pow(c1, x, P)
        prova = provar_mesmo_log("decifracao", contexto_decifracao(eleicao, id_autoridade, j), x, (G, h_i, c1, d))
        parciais.append({"d": para_hex(d), "prova": prova})
    apuracao = ler_apuracao()
    apuracao["produto"] = [[para_hex(c1), para_hex(c2)] for c1, c2 in produto]
    apuracao["parciais"][str(id_autoridade)] = parciais
    gravar_json(caminho_publico("apuracao.json"), apuracao)


def validar_parciais(eleicao: str, id_autoridade: str, produto, parciais):
    h_i = chave_publica(id_autoridade)
    if len(parciais) != len(produto):
        raise ErroVotacao(f"Decifração da autoridade {id_autoridade} incompleta")
    for j, ((c1, _), item) in enumerate(zip(produto, parciais, strict=True)):
        d = de_hex(item["d"])
        contexto = contexto_decifracao(eleicao, id_autoridade, j)
        if not (elemento_valido(d) and verificar_mesmo_log("decifracao", contexto, item["prova"], (G, h_i, c1, d))):
            raise ErroVotacao(f"Decifração da autoridade {id_autoridade} é inválida (prova de Chaum-Pedersen falhou)")


def combinar(c2: int, parciais) -> int:
    produto_d = 1
    for d in parciais:
        produto_d = produto_d * d % P
    return c2 * pow(produto_d, -1, P) % P


def apurar_resultado(forcar: bool = False):
    servidor.exigir_fase(servidor.ENCERRADA)
    params = servidor.ler_publico("params.json")
    apuracao = ler_apuracao()
    esperadas = {str(i) for i in range(1, params["n_autoridades"] + 1)}
    faltando = sorted(esperadas - set(apuracao["parciais"]))
    if faltando and not forcar:
        raise ErroVotacao(f"Apuração exige todas as autoridades; faltam: {', '.join(faltando)}")
    produto = produto_do_quadro()
    for id_autoridade, parciais in apuracao["parciais"].items():
        validar_parciais(params["eleicao"], id_autoridade, produto, parciais)
    total_cedulas = len(quadro.ler()["entradas"])
    totais = {}
    for j, nome in enumerate(params["candidatos"]):
        d_candidato = [de_hex(lista[j]["d"]) for lista in apuracao["parciais"].values()]
        try:
            totais[nome] = log_discreto(combinar(produto[j][1], d_candidato), total_cedulas)
        except ValueError:
            raise ErroVotacao(f"Decifração de '{nome}' não deu um total entre 0 e {total_cedulas}: "
                              "falta a parte de alguma autoridade") from None
    gravar_json(caminho_publico("resultado.json"),
                {"eleicao": params["eleicao"], "total_cedulas": total_cedulas, "totais": totais})
    return totais
