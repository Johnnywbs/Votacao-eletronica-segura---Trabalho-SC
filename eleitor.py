import quadro
import servidor
from assinatura import assinar, carregar_privada, gerar_par, privada_para_pem, publica_para_pem, verificar
from elgamal import cedula_para_json
from provas import conferir_chaves, contexto_cedula, gerar_cedula
from util import ErroVotacao, caminho_privado, canonico, gravar_json, gravar_texto, ler_json


def pasta(id_eleitor: str) -> str:
    return f"eleitor_{id_eleitor}"


def gerar_e_cadastrar(id_eleitor: str):
    chave = gerar_par()
    servidor.cadastrar(id_eleitor, publica_para_pem(chave))
    gravar_texto(caminho_privado(pasta(id_eleitor), "chave.pem"), privada_para_pem(chave))


def indice_candidato(candidato: str, candidatos) -> int:
    if candidato in candidatos:
        return candidatos.index(candidato)
    raise ErroVotacao(f"Candidato '{candidato}' não existe. Opções: {', '.join(candidatos)}")


def carregar_chave(id_eleitor: str):
    caminho = caminho_privado(pasta(id_eleitor), "chave.pem")
    if not caminho.exists():
        raise ErroVotacao(f"Eleitor '{id_eleitor}' não tem chave (não cadastrado)")
    return carregar_privada(caminho.read_text(encoding="utf-8"))


def votar(id_eleitor: str, candidato: str):
    params = servidor.ler_publico("params.json")
    h = conferir_chaves(params["eleicao"], params["n_autoridades"], servidor.ler_publico("autoridades.json"))
    escolha = indice_candidato(candidato, params["candidatos"])
    contexto = contexto_cedula(params["eleicao"], id_eleitor)
    cifras, provas_cedula = gerar_cedula(h, escolha, len(params["candidatos"]), contexto)
    cedula_json = cedula_para_json(cifras)
    mensagem = servidor.mensagem_cedula(params["eleicao"], id_eleitor, cedula_json, provas_cedula)
    assinatura_eleitor = assinar(carregar_chave(id_eleitor), mensagem)
    recibo = servidor.receber_cedula(id_eleitor, cedula_json, provas_cedula, assinatura_eleitor)
    gravar_json(caminho_privado(pasta(id_eleitor), "recibo.json"), recibo)
    return recibo


def verificar_recibo(id_eleitor: str) -> str:
    recibo = ler_json(caminho_privado(pasta(id_eleitor), "recibo.json"))
    conteudo = {chave: valor for chave, valor in recibo.items() if chave != "assinatura_servidor"}
    chave_servidor = servidor.ler_publico("params.json")["chave_servidor"]
    if not verificar(chave_servidor, canonico(conteudo), recibo["assinatura_servidor"]):
        raise ErroVotacao("Recibo com assinatura do servidor inválida")
    entradas = quadro.ler()["entradas"]
    indice = recibo["indice"]
    if indice >= len(entradas):
        raise ErroVotacao("Cédula do recibo não está no quadro (removida?)")
    entrada = entradas[indice]
    if entrada["eleitor"] != id_eleitor or entrada["hash"] != recibo["hash_entrada"]:
        raise ErroVotacao("Entrada do quadro não confere com o recibo")
    if quadro.hash_entrada(entrada) != recibo["hash_entrada"]:
        raise ErroVotacao("Conteúdo da cédula no quadro foi alterado")
    return f"Cédula de '{id_eleitor}' confere: posição {indice} do quadro, hash {recibo['hash_entrada'][:16]}..."
