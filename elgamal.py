import secrets

from params import G, P, Q
from util import de_hex, para_hex


def aleatorio_zq() -> int:
    return secrets.randbelow(Q - 1) + 1


def elemento_valido(y: int) -> bool:
    return 1 < y < P and pow(y, Q, P) == 1


def cifrar(h: int, m: int):
    r = aleatorio_zq()
    c1 = pow(G, r, P)
    c2 = pow(G, m, P) * pow(h, r, P) % P
    return (c1, c2), r


def multiplicar(cifras):
    c1_total, c2_total = 1, 1
    for c1, c2 in cifras:
        c1_total = c1_total * c1 % P
        c2_total = c2_total * c2 % P
    return c1_total, c2_total


def apurar(cedulas, n_candidatos: int):
    return [multiplicar([cedula[j] for cedula in cedulas]) for j in range(n_candidatos)]


def log_discreto(g_t: int, maximo: int) -> int:
    atual = 1
    for t in range(maximo + 1):
        if atual == g_t:
            return t
        atual = atual * G % P
    raise ValueError("nenhum T entre 0 e o máximo: decifração inválida")


def cedula_para_json(cedula):
    return [[para_hex(c1), para_hex(c2)] for c1, c2 in cedula]


def cedula_de_json(dados):
    return [(de_hex(c1), de_hex(c2)) for c1, c2 in dados]
