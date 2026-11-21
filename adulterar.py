import argparse

import quadro
import servidor
from params import G, P
from util import ErroVotacao, caminho_publico, de_hex, gravar_json, ler_json, para_hex


def adulterar_cedula(indice: int, recalcular: bool):
    dados = quadro.ler()
    alvo = dados["entradas"][indice]
    c1, c2 = alvo["cedula"][0]
    alvo["cedula"][0] = [c1, para_hex(de_hex(c2) * G % P)]
    if recalcular:
        anterior = dados["genese"]
        for entrada in dados["entradas"]:
            entrada["hash_anterior"] = anterior
            entrada["hash"] = quadro.hash_entrada(entrada)
            anterior = entrada["hash"]
    gravar_json(caminho_publico(quadro.ARQUIVO), dados)
    modo = "com a cadeia recalculada" if recalcular else "sem recalcular hashes"
    print(f"Cédula {indice} adulterada ({modo}): +1 voto para o candidato 1.")


def adulterar_decifracao():
    params = servidor.ler_publico("params.json")
    apuracao = ler_json(caminho_publico("apuracao.json"))
    resultado = ler_json(caminho_publico("resultado.json"))
    candidatos = params["candidatos"]
    perdedor = next((j for j in range(1, len(candidatos)) if resultado["totais"][candidatos[j]] > 0), None)
    if perdedor is None:
        raise ErroVotacao("Nenhum candidato além do primeiro tem votos para serem desviados")
    id_autoridade = str(params["n_autoridades"])
    parciais = apuracao["parciais"][id_autoridade]
    parciais[0]["d"] = para_hex(de_hex(parciais[0]["d"]) * pow(G, -1, P) % P)
    parciais[perdedor]["d"] = para_hex(de_hex(parciais[perdedor]["d"]) * G % P)
    resultado["totais"][candidatos[0]] += 1
    resultado["totais"][candidatos[perdedor]] -= 1
    gravar_json(caminho_publico("apuracao.json"), apuracao)
    gravar_json(caminho_publico("resultado.json"), resultado)
    print(f"Autoridade {id_autoridade} publicou decifrações falsas: 1 voto desviado de "
          f"{candidatos[perdedor]} para {candidatos[0]}, com a soma dos totais intacta.")


def main():
    parser = argparse.ArgumentParser(description="Ataques simulados para a demonstração")
    parser.add_argument("--indice", type=int, default=0)
    parser.add_argument("--recalcular", action="store_true")
    parser.add_argument("--decifracao", action="store_true", help="simula uma autoridade desonesta")
    args = parser.parse_args()
    if args.decifracao:
        adulterar_decifracao()
    else:
        adulterar_cedula(args.indice, args.recalcular)


if __name__ == "__main__":
    main()
