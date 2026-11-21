import argparse
import shutil
import sys

import autoridade
import eleitor
import servidor
from util import ErroVotacao, raiz


def resetar(_):
    for nome in ("publico", "privado"):
        shutil.rmtree(raiz() / nome, ignore_errors=True)
    print("Dados apagados.")


def configurar(args):
    servidor.configurar(args.eleicao, args.candidatos, args.autoridades)
    print(f"Eleição '{args.eleicao}' configurada: {', '.join(args.candidatos)}; {args.autoridades} autoridades.")


def autoridade_gerar(args):
    autoridade.gerar_chave(args.id)
    print(f"Autoridade {args.id}: x_{args.id} guardado; h_{args.id} e prova de Schnorr publicados.")


def autoridade_conferir(args):
    chave = autoridade.conferir(args.id)
    print(f"Autoridade {args.id}: seu h_{args.id} está publicado, todas as provas de Schnorr conferem "
          f"e h = produto dos h_i ({chave[:16]}...).")


def cadastrar(args):
    eleitor.gerar_e_cadastrar(args.eleitor)
    print(f"Eleitor '{args.eleitor}' cadastrado.")


def abrir_votacao(_):
    servidor.abrir_votacao()
    print("Votação aberta. Lista de eleitores e chave conjunta congeladas.")


def votar(args):
    recibo = eleitor.votar(args.eleitor, args.candidato)
    print(f"Voto de '{args.eleitor}' aceito (provas de validade conferidas). "
          f"Recibo: posição {recibo['indice']}, hash {recibo['hash_entrada'][:16]}...")


def encerrar(_):
    hash_final = servidor.encerrar()
    print("Votação encerrada. Hash final do quadro assinado e publicado.")
    print(f"Publique este hash fora do sistema: {hash_final}")


def autoridade_decifrar(args):
    autoridade.decifrar_parcial(args.id)
    print(f"Autoridade {args.id}: decifração parcial e prova de Chaum-Pedersen publicadas.")


def apurar(args):
    totais = autoridade.apurar_resultado(forcar=args.forcar)
    print("Provas das autoridades conferidas. Resultado:")
    for nome, total in totais.items():
        print(f"  {nome}: {total}")


def verificar_recibo(args):
    print(eleitor.verificar_recibo(args.eleitor))


def montar_parser():
    parser = argparse.ArgumentParser(description="Sistema de votação eletrônica seguro")
    sub = parser.add_subparsers(dest="comando", required=True)

    def comando(nome, funcao, ajuda):
        p = sub.add_parser(nome, help=ajuda)
        p.set_defaults(funcao=funcao)
        return p

    comando("resetar", resetar, "apaga publico/ e privado/")
    p = comando("configurar", configurar, "cria a eleição")
    p.add_argument("--eleicao", required=True)
    p.add_argument("--candidatos", nargs="+", required=True)
    p.add_argument("--autoridades", type=int, default=3)
    for nome, funcao, ajuda in [("autoridade-gerar", autoridade_gerar, "gera x_i e publica h_i com prova de Schnorr"),
                                ("autoridade-conferir", autoridade_conferir, "autoridade confere sua chave publicada"),
                                ("autoridade-decifrar", autoridade_decifrar, "publica a decifração parcial com prova")]:
        comando(nome, funcao, ajuda).add_argument("--id", type=int, required=True)
    comando("cadastrar", cadastrar, "gera as chaves e cadastra um eleitor").add_argument("--eleitor", required=True)
    comando("abrir-votacao", abrir_votacao, "inicia a votação")
    p = comando("votar", votar, "cifra, prova, assina e envia a cédula")
    p.add_argument("--eleitor", required=True)
    p.add_argument("--candidato", required=True, help="nome do candidato")
    comando("encerrar", encerrar, "encerra a votação")
    comando("apurar", apurar, "confere as provas e combina as decifrações").add_argument(
        "--forcar", action="store_true", help="tenta mesmo faltando autoridade (para a demo)")
    comando("verificar-recibo", verificar_recibo, "eleitor confere sua cédula").add_argument("--eleitor", required=True)
    return parser


def main():
    args = montar_parser().parse_args()
    try:
        args.funcao(args)
    except ErroVotacao as erro:
        print(f"REJEITADO: {erro}")
        sys.exit(1)
    except FileNotFoundError as erro:
        print(f"ERRO: arquivo não encontrado ({erro.filename}). A etapa anterior foi executada?")
        sys.exit(1)


if __name__ == "__main__":
    main()
