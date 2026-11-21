import argparse
import sys

import eleitor
import servidor
from assinatura import assinar
from elgamal import cedula_para_json, cifrar
from params import Q
from provas import contexto_cedula, enunciado_soma, provar_mesmo_log, provar_voto
from util import ErroVotacao, de_hex


def cedula_invalida(id_eleitor: str, valor: int):
    params = servidor.ler_publico("params.json")
    h = de_hex(servidor.ler_publico("autoridades.json")["chave_conjunta"])
    contexto = contexto_cedula(params["eleicao"], id_eleitor)
    pares = [cifrar(h, valor if j == 0 else 0) for j in range(len(params["candidatos"]))]
    cifras = [cifra for cifra, _ in pares]
    rs = [r for _, r in pares]
    provas = {"votos": [provar_voto(h, cifra, 1 if j == 0 else 0, r, contexto) for j, (cifra, r) in enumerate(pares)],
              "soma": provar_mesmo_log("soma", contexto, sum(rs) % Q, enunciado_soma(h, cifras))}
    cedula_json = cedula_para_json(cifras)
    mensagem = servidor.mensagem_cedula(params["eleicao"], id_eleitor, cedula_json, provas)
    return cedula_json, provas, assinar(eleitor.carregar_chave(id_eleitor), mensagem)


def main():
    parser = argparse.ArgumentParser(description="Eleitor desonesto: tenta cifrar um valor fora de {0, 1}")
    parser.add_argument("--eleitor", required=True)
    parser.add_argument("--valor", type=int, default=2)
    args = parser.parse_args()
    candidato = servidor.ler_publico("params.json")["candidatos"][0]
    print(f"'{args.eleitor}' tenta enviar uma cédula com valor {args.valor} para {candidato}...")
    try:
        servidor.receber_cedula(args.eleitor, *cedula_invalida(args.eleitor, args.valor))
        print("ACEITO (isso não deveria acontecer)")
    except ErroVotacao as erro:
        print(f"REJEITADO: {erro}")
        sys.exit(1)


if __name__ == "__main__":
    main()
