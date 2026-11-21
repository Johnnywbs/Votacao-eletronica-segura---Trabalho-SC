import argparse
import hashlib
import json
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

MIN_AUTORIDADES = 3
MIN_CANDIDATOS = 2
PSS = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)


def canonico(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def assinatura_valida(chave_pem: str, mensagem: bytes, assinatura_hex: str) -> bool:
    try:
        chave = serialization.load_pem_public_key(chave_pem.encode())
        chave.verify(bytes.fromhex(assinatura_hex), mensagem, PSS, hashes.SHA256())
        return True
    except (InvalidSignature, ValueError):
        return False


class Auditoria:
    def __init__(self, pasta: Path, hash_esperado=None):
        self.pasta = pasta
        self.hash_esperado = hash_esperado
        self.falhas = []

    def ler(self, nome):
        caminho = self.pasta / nome
        return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None

    def registrar(self, condicao: bool, descricao: str, detalhe: str = "") -> bool:
        if condicao:
            print(f"[OK]    {descricao}")
        else:
            self.falhas.append(descricao)
            print(f"[FALHA] {descricao}{': ' + detalhe if detalhe else ''}")
        return condicao

    def no_subgrupo(self, y: int) -> bool:
        return 1 < y < self.p and pow(y, self.q, self.p) == 1

    def desafio(self, rotulo, contexto, *valores) -> int:
        dados = canonico([rotulo, contexto, [format(v, "x") for v in valores]])
        return int(sha256_hex(dados), 16) % self.q

    def prova_voto_valida(self, cifra, prova, contexto) -> bool:
        p, g, h = self.p, self.g, self.h
        c1, c2 = cifra
        c = [int(prova["c0"], 16), int(prova["c1"], 16)]
        s = [int(prova["s0"], 16), int(prova["s1"], 16)]
        a, b = [], []
        for k in (0, 1):
            alvo = c2 * pow(g, -k, p) % p
            a.append(pow(g, s[k], p) * pow(c1, -c[k], p) % p)
            b.append(pow(h, s[k], p) * pow(alvo, -c[k], p) % p)
        return (c[0] + c[1]) % self.q == self.desafio("voto", contexto, h, c1, c2, a[0], b[0], a[1], b[1])

    def mesmo_log_valido(self, rotulo, contexto, prova, enunciado) -> bool:
        g1, y1, g2, y2 = enunciado
        p = self.p
        c, s = int(prova["c"], 16), int(prova["s"], 16)
        t1 = pow(g1, s, p) * pow(y1, -c, p) % p
        t2 = pow(g2, s, p) * pow(y2, -c, p) % p
        return c == self.desafio(rotulo, contexto, g1, y1, g2, y2, t1, t2)

    def enunciado_soma(self, cifras):
        a, b = 1, 1
        for c1, c2 in cifras:
            a, b = a * c1 % self.p, b * c2 % self.p
        return self.g, a, self.h, b * pow(self.g, -1, self.p) % self.p

    def prova_conhecimento_valida(self, h, prova, contexto) -> bool:
        try:
            c, s = int(prova["c"], 16), int(prova["s"], 16)
        except (KeyError, TypeError, ValueError):
            return False
        t = pow(self.g, s, self.p) * pow(h, -c, self.p) % self.p
        return c == self.desafio("chave", contexto, h, t)

    def verificar_grupo(self, params):
        self.p, self.q, self.g = (int(params[k], 16) for k in ("p", "q", "g"))
        self.registrar(self.q == (self.p - 1) // 2, "p = 2q + 1")
        self.registrar(self.g != 1 and pow(self.g, self.q, self.p) == 1, "g gera o subgrupo de ordem q")
        self.registrar(len(params["candidatos"]) >= MIN_CANDIDATOS, "pelo menos 2 candidatos")

    def verificar_autoridades(self, params, autoridades):
        registros = autoridades["autoridades"]
        self.registrar(len(registros) == params["n_autoridades"] >= MIN_AUTORIDADES,
                       f"{params['n_autoridades']} autoridades (mínimo {MIN_AUTORIDADES})")
        self.h_autoridade = {}
        produto = 1
        for id_autoridade, registro in registros.items():
            h = int(registro["h"], 16)
            self.registrar(self.no_subgrupo(h), f"autoridade {id_autoridade}: h_i está no subgrupo")
            contexto = {"eleicao": params["eleicao"], "autoridade": id_autoridade}
            self.registrar(self.prova_conhecimento_valida(h, registro.get("prova"), contexto),
                           f"autoridade {id_autoridade}: prova de Schnorr de que conhece x_i",
                           "ninguém demonstrou conhecer x_i: chave pública substituída")
            self.h_autoridade[id_autoridade] = h
            produto = produto * h % self.p
        self.h = int(autoridades["chave_conjunta"], 16) if autoridades["chave_conjunta"] else 0
        self.registrar(self.h == produto, "chave conjunta h = produto dos h_i")

    def verificar_cadeia(self, params, autoridades, eleitores, quadro):
        genese = sha256_hex(canonico({"params": params, "autoridades": autoridades, "eleitores": eleitores}))
        integra = self.registrar(quadro["genese"] == genese, "gênese do quadro confere com a configuração")
        anterior = quadro["genese"]
        for posicao, entrada in enumerate(quadro["entradas"]):
            sem_hash = {k: v for k, v in entrada.items() if k != "hash"}
            ok = (entrada["indice"] == posicao and entrada["hash_anterior"] == anterior
                  and sha256_hex(canonico(sem_hash)) == entrada["hash"])
            if not ok:
                integra = False
                self.registrar(False, f"cadeia de hashes na entrada {posicao}", "hash ou encadeamento não confere")
            anterior = entrada["hash"]
        if integra:
            self.registrar(True, f"cadeia de hashes íntegra ({len(quadro['entradas'])} entradas)")

    def verificar_cabeca(self, params, quadro, cabeca):
        if cabeca is None:
            self.registrar(False, "hash final publicado no encerramento", "cabeca.json ausente")
            return
        conteudo = {k: v for k, v in cabeca.items() if k != "assinatura_servidor"}
        ultimo = quadro["entradas"][-1]["hash"] if quadro["entradas"] else quadro["genese"]
        self.registrar(assinatura_valida(params["chave_servidor"], canonico(conteudo), cabeca["assinatura_servidor"]),
                       "assinatura do servidor no hash final")
        self.registrar(cabeca["hash_final"] == ultimo and cabeca["total_cedulas"] == len(quadro["entradas"]),
                       "hash final e total de cédulas conferem com o quadro",
                       "cédulas inseridas, removidas ou cadeia recalculada")
        if self.hash_esperado:
            self.registrar(self.hash_esperado == ultimo == cabeca["hash_final"],
                           "hash final igual ao publicado fora do sistema",
                           "o quadro foi reconstruído depois do encerramento")

    def cedula_valida(self, params, entrada):
        contexto = {"eleicao": params["eleicao"], "eleitor": entrada["eleitor"]}
        try:
            cifras = [(int(c1, 16), int(c2, 16)) for c1, c2 in entrada["cedula"]]
            formato = (len(cifras) == len(params["candidatos"])
                       and all(self.no_subgrupo(c1) and self.no_subgrupo(c2) for c1, c2 in cifras))
            provas = entrada["provas"]
            votos_ok = formato and len(provas["votos"]) == len(cifras) and all(
                self.prova_voto_valida(cifra, prova, contexto)
                for cifra, prova in zip(cifras, provas["votos"], strict=True))
            soma_ok = votos_ok and self.mesmo_log_valido("soma", contexto, provas["soma"], self.enunciado_soma(cifras))
            return formato, soma_ok
        except (KeyError, TypeError, ValueError):
            return False, False

    def verificar_cedulas(self, params, eleitores, quadro):
        cadastrados = eleitores["eleitores"]
        vistos = set()
        problemas = 0
        for entrada in quadro["entradas"]:
            id_eleitor = entrada["eleitor"]
            mensagem = canonico({"eleicao": params["eleicao"], "eleitor": id_eleitor,
                                 "cedula": entrada["cedula"], "provas": entrada.get("provas")})
            formato, provas_ok = self.cedula_valida(params, entrada)
            verificacoes = [
                (id_eleitor in cadastrados, "eleitor não cadastrado"),
                (id_eleitor not in vistos, "eleitor votou mais de uma vez"),
                (id_eleitor in cadastrados
                 and assinatura_valida(cadastrados[id_eleitor], mensagem, entrada["assinatura"]),
                 "assinatura do eleitor inválida"),
                (formato, "cédula mal formada"),
                (provas_ok, "prova de que cada voto é 0 ou 1 e a soma é 1 inválida"),
            ]
            for motivo in [motivo for ok, motivo in verificacoes if not ok]:
                problemas += 1
                self.registrar(False, f"cédula {entrada['indice']} ({id_eleitor})", motivo)
            vistos.add(id_eleitor)
        if problemas == 0:
            self.registrar(True, "assinaturas, elegibilidade, unicidade e provas de validade de todas as cédulas")

    def produto_das_cedulas(self, n_candidatos, quadro):
        produto = [[1, 1] for _ in range(n_candidatos)]
        for entrada in quadro["entradas"]:
            for j, (c1, c2) in enumerate(entrada["cedula"]):
                produto[j][0] = produto[j][0] * int(c1, 16) % self.p
                produto[j][1] = produto[j][1] * int(c2, 16) % self.p
        return produto

    def verificar_decifracoes(self, params, apuracao, produto):
        ids = {str(i) for i in range(1, params["n_autoridades"] + 1)}
        self.registrar(set(apuracao["parciais"]) == ids, "decifrações parciais de todas as autoridades")
        for id_autoridade, parciais in apuracao["parciais"].items():
            h_i = self.h_autoridade.get(id_autoridade, 0)
            try:
                ok = len(parciais) == len(produto) and all(
                    self.no_subgrupo(int(item["d"], 16)) and self.mesmo_log_valido(
                        "decifracao", {"eleicao": params["eleicao"], "autoridade": id_autoridade, "candidato": j},
                        item["prova"], (self.g, h_i, produto[j][0], int(item["d"], 16)))
                    for j, item in enumerate(parciais))
            except (KeyError, TypeError, ValueError):
                ok = False
            self.registrar(ok, f"prova de Chaum-Pedersen da autoridade {id_autoridade}",
                           "decifração parcial falsificada")

    def verificar_totais(self, params, quadro, apuracao, resultado, produto):
        for j, nome in enumerate(params["candidatos"]):
            produto_d = 1
            for parciais in apuracao["parciais"].values():
                produto_d = produto_d * int(parciais[j]["d"], 16) % self.p
            g_t = produto[j][1] * pow(produto_d, -1, self.p) % self.p
            total = resultado["totais"].get(nome, -1)
            self.registrar(total >= 0 and g_t == pow(self.g, total, self.p),
                           f"total de {nome} = {total} confere com C2 / (produto dos d_i)")
        soma = sum(resultado["totais"].values())
        self.registrar(soma == len(quadro["entradas"]),
                       f"soma dos totais ({soma}) = número de cédulas ({len(quadro['entradas'])})")

    def verificar_apuracao(self, params, quadro, apuracao, resultado):
        if apuracao is None or resultado is None:
            print("[--]    apuração ainda não publicada: produto e resultado não verificados")
            return
        produto = self.produto_das_cedulas(len(params["candidatos"]), quadro)
        publicado = [[int(c1, 16), int(c2, 16)] for c1, c2 in apuracao["produto"]]
        self.registrar(produto == publicado, "produto homomórfico das cédulas confere com o apurado")
        self.verificar_decifracoes(params, apuracao, produto)
        self.verificar_totais(params, quadro, apuracao, resultado, produto)

    def executar(self) -> bool:
        params, autoridades = self.ler("params.json"), self.ler("autoridades.json")
        eleitores, quadro = self.ler("eleitores.json"), self.ler("quadro.json")
        if None in (params, autoridades, eleitores, quadro):
            print("[FALHA] arquivos públicos obrigatórios ausentes")
            return False
        print("== Parâmetros e autoridades ==")
        self.verificar_grupo(params)
        self.verificar_autoridades(params, autoridades)
        print("== Quadro público ==")
        self.verificar_cadeia(params, autoridades, eleitores, quadro)
        self.verificar_cabeca(params, quadro, self.ler("cabeca.json"))
        self.verificar_cedulas(params, eleitores, quadro)
        print("== Apuração ==")
        self.verificar_apuracao(params, quadro, self.ler("apuracao.json"), self.ler("resultado.json"))
        return not self.falhas


def main():
    parser = argparse.ArgumentParser(description="Auditor independente da eleição")
    parser.add_argument("pasta", nargs="?", default="publico")
    parser.add_argument("--hash-esperado", help="hash final divulgado fora do sistema no encerramento")
    args = parser.parse_args()
    valida = Auditoria(Path(args.pasta), args.hash_esperado).executar()
    print()
    print("ELEIÇÃO VÁLIDA" if valida else "ELEIÇÃO ADULTERADA OU INVÁLIDA")
    sys.exit(0 if valida else 1)


if __name__ == "__main__":
    main()
