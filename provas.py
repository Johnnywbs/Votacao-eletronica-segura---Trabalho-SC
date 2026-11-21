from elgamal import aleatorio_zq, cifrar, elemento_valido, multiplicar
from params import G, P, Q
from util import ErroVotacao, canonico, de_hex, para_hex, sha256_hex


def desafio(rotulo: str, contexto, *valores) -> int:
    dados = canonico([rotulo, contexto, [para_hex(v) for v in valores]])
    return int(sha256_hex(dados), 16) % Q


def contexto_cedula(id_eleicao: str, id_eleitor: str):
    return {"eleicao": id_eleicao, "eleitor": id_eleitor}


def contexto_decifracao(id_eleicao: str, id_autoridade, candidato: int):
    return {"eleicao": id_eleicao, "autoridade": str(id_autoridade), "candidato": candidato}


def contexto_chave(id_eleicao: str, id_autoridade):
    return {"eleicao": id_eleicao, "autoridade": str(id_autoridade)}


def provar_conhecimento(x: int, h: int, contexto):
    w = aleatorio_zq()
    t = pow(G, w, P)
    c = desafio("chave", contexto, h, t)
    return {"c": para_hex(c), "s": para_hex((w + c * x) % Q)}


def verificar_conhecimento(h: int, prova, contexto) -> bool:
    try:
        c, s = de_hex(prova["c"]), de_hex(prova["s"])
    except (KeyError, TypeError, ValueError):
        return False
    t = pow(G, s, P) * pow(h, -c, P) % P
    return c == desafio("chave", contexto, h, t)


def produto_das_chaves(id_eleicao: str, n_autoridades: int, dados) -> int:
    registros = dados["autoridades"]
    if set(registros) != {str(i) for i in range(1, n_autoridades + 1)}:
        raise ErroVotacao("Faltam chaves de autoridades (ou há ids inesperados)")
    produto = 1
    for id_autoridade, registro in sorted(registros.items()):
        h = de_hex(registro["h"])
        if not elemento_valido(h):
            raise ErroVotacao(f"Autoridade {id_autoridade}: h_i fora do subgrupo")
        if not verificar_conhecimento(h, registro.get("prova"), contexto_chave(id_eleicao, id_autoridade)):
            raise ErroVotacao(f"Autoridade {id_autoridade}: prova de Schnorr inválida "
                              "(ninguém demonstrou conhecer x_i; chave pública substituída?)")
        produto = produto * h % P
    return produto


def conferir_chaves(id_eleicao: str, n_autoridades: int, dados) -> int:
    produto = produto_das_chaves(id_eleicao, n_autoridades, dados)
    if dados.get("chave_conjunta") is None or de_hex(dados["chave_conjunta"]) != produto:
        raise ErroVotacao("Chave conjunta diferente do produto dos h_i")
    return produto


def provar_voto(h: int, cifra, m: int, r: int, contexto):
    c1, c2 = cifra
    a, b, c, s = [0, 0], [0, 0], [0, 0], [0, 0]
    falso = 1 - m
    c[falso], s[falso] = aleatorio_zq(), aleatorio_zq()
    alvo_falso = c2 * pow(G, -falso, P) % P
    a[falso] = pow(G, s[falso], P) * pow(c1, -c[falso], P) % P
    b[falso] = pow(h, s[falso], P) * pow(alvo_falso, -c[falso], P) % P
    w = aleatorio_zq()
    a[m], b[m] = pow(G, w, P), pow(h, w, P)
    total = desafio("voto", contexto, h, c1, c2, a[0], b[0], a[1], b[1])
    c[m] = (total - c[falso]) % Q
    s[m] = (w + c[m] * r) % Q
    return {"c0": para_hex(c[0]), "c1": para_hex(c[1]), "s0": para_hex(s[0]), "s1": para_hex(s[1])}


def verificar_voto(h: int, cifra, prova, contexto) -> bool:
    c1, c2 = cifra
    c = [de_hex(prova["c0"]), de_hex(prova["c1"])]
    s = [de_hex(prova["s0"]), de_hex(prova["s1"])]
    a, b = [], []
    for k in (0, 1):
        alvo = c2 * pow(G, -k, P) % P
        a.append(pow(G, s[k], P) * pow(c1, -c[k], P) % P)
        b.append(pow(h, s[k], P) * pow(alvo, -c[k], P) % P)
    return (c[0] + c[1]) % Q == desafio("voto", contexto, h, c1, c2, a[0], b[0], a[1], b[1])


def provar_mesmo_log(rotulo: str, contexto, x: int, enunciado):
    g1, y1, g2, y2 = enunciado
    w = aleatorio_zq()
    c = desafio(rotulo, contexto, g1, y1, g2, y2, pow(g1, w, P), pow(g2, w, P))
    return {"c": para_hex(c), "s": para_hex((w + c * x) % Q)}


def verificar_mesmo_log(rotulo: str, contexto, prova, enunciado) -> bool:
    g1, y1, g2, y2 = enunciado
    try:
        c, s = de_hex(prova["c"]), de_hex(prova["s"])
    except (KeyError, TypeError, ValueError):
        return False
    t1 = pow(g1, s, P) * pow(y1, -c, P) % P
    t2 = pow(g2, s, P) * pow(y2, -c, P) % P
    return c == desafio(rotulo, contexto, g1, y1, g2, y2, t1, t2)


def enunciado_soma(h: int, cifras):
    a, b = multiplicar(cifras)
    return G, a, h, b * pow(G, -1, P) % P


def gerar_cedula(h: int, escolha: int, n_candidatos: int, contexto):
    if not 0 <= escolha < n_candidatos:
        raise ValueError("candidato inexistente")
    cifras, rs, provas_votos = [], [], []
    for j in range(n_candidatos):
        m = 1 if j == escolha else 0
        cifra, r = cifrar(h, m)
        cifras.append(cifra)
        rs.append(r)
        provas_votos.append(provar_voto(h, cifra, m, r, contexto))
    soma = provar_mesmo_log("soma", contexto, sum(rs) % Q, enunciado_soma(h, cifras))
    return cifras, {"votos": provas_votos, "soma": soma}


def verificar_cedula(h: int, cifras, provas_cedula, contexto) -> bool:
    try:
        votos = provas_cedula["votos"]
        return (len(votos) == len(cifras)
                and all(verificar_voto(h, cifra, prova, contexto) for cifra, prova in zip(cifras, votos, strict=True))
                and verificar_mesmo_log("soma", contexto, provas_cedula["soma"], enunciado_soma(h, cifras)))
    except (KeyError, TypeError, ValueError):
        return False
