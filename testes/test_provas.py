import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elgamal import aleatorio_zq, cifrar
from params import G, P, Q
from provas import (contexto_cedula, contexto_chave, enunciado_soma, gerar_cedula, provar_conhecimento,
                    provar_mesmo_log, provar_voto, verificar_cedula, verificar_conhecimento, verificar_mesmo_log,
                    verificar_voto)
from util import para_hex


class TesteProvasDeVoto(unittest.TestCase):
    def setUp(self):
        self.x = aleatorio_zq()
        self.h = pow(G, self.x, P)
        self.contexto = contexto_cedula("teste", "ana")

    def test_cedula_honesta(self):
        cifras, provas = gerar_cedula(self.h, 2, 3, self.contexto)
        self.assertTrue(verificar_cedula(self.h, cifras, provas, self.contexto))

    def test_prova_presa_ao_eleitor(self):
        cifras, provas = gerar_cedula(self.h, 0, 3, self.contexto)
        self.assertFalse(verificar_cedula(self.h, cifras, provas, contexto_cedula("teste", "beto")))

    def test_valor_dois_nao_tem_prova(self):
        cifra, r = cifrar(self.h, 2)
        for alegado in (0, 1):
            prova = provar_voto(self.h, cifra, alegado, r, self.contexto)
            self.assertFalse(verificar_voto(self.h, cifra, prova, self.contexto))

    def test_dois_votos_na_mesma_cedula(self):
        pares = [cifrar(self.h, 1), cifrar(self.h, 1), cifrar(self.h, 0)]
        cifras, rs = [cifra for cifra, _ in pares], [r for _, r in pares]
        votos = [provar_voto(self.h, cifra, m, r, self.contexto)
                 for (cifra, r), m in zip(pares, (1, 1, 0), strict=True)]
        provas = {"votos": votos,
                  "soma": provar_mesmo_log("soma", self.contexto, sum(rs) % Q, enunciado_soma(self.h, cifras))}
        self.assertTrue(all(verificar_voto(self.h, cifra, prova, self.contexto)
                            for cifra, prova in zip(cifras, votos, strict=True)))
        self.assertFalse(verificar_cedula(self.h, cifras, provas, self.contexto))

    def test_prova_adulterada(self):
        cifras, provas = gerar_cedula(self.h, 1, 2, self.contexto)
        provas["votos"][0]["s0"] = para_hex((int(provas["votos"][0]["s0"], 16) + 1) % Q)
        self.assertFalse(verificar_cedula(self.h, cifras, provas, self.contexto))


class TesteProvaDeDecifracao(unittest.TestCase):
    def setUp(self):
        self.x = aleatorio_zq()
        self.h_i = pow(G, self.x, P)
        self.c1 = pow(G, aleatorio_zq(), P)
        self.d = pow(self.c1, self.x, P)
        self.contexto = {"eleicao": "teste", "autoridade": "1", "candidato": 0}

    def provar(self, x, d):
        return provar_mesmo_log("decifracao", self.contexto, x, (G, self.h_i, self.c1, d))

    def verificar(self, prova, d):
        return verificar_mesmo_log("decifracao", self.contexto, prova, (G, self.h_i, self.c1, d))

    def test_decifracao_honesta(self):
        self.assertTrue(self.verificar(self.provar(self.x, self.d), self.d))

    def test_decifracao_desviada(self):
        self.assertFalse(self.verificar(self.provar(self.x, self.d), self.d * G % P))

    def test_chave_errada(self):
        falso = aleatorio_zq()
        d_falso = pow(self.c1, falso, P)
        self.assertFalse(self.verificar(self.provar(falso, d_falso), d_falso))


class TesteProvaDeConhecimento(unittest.TestCase):
    def setUp(self):
        self.x = aleatorio_zq()
        self.h = pow(G, self.x, P)
        self.contexto = contexto_chave("teste", 1)

    def test_chave_honesta(self):
        prova = provar_conhecimento(self.x, self.h, self.contexto)
        self.assertTrue(verificar_conhecimento(self.h, prova, self.contexto))

    def test_prova_presa_a_autoridade(self):
        prova = provar_conhecimento(self.x, self.h, self.contexto)
        self.assertFalse(verificar_conhecimento(self.h, prova, contexto_chave("teste", 2)))

    def test_prova_nao_serve_para_outra_chave(self):
        prova = provar_conhecimento(self.x, self.h, self.contexto)
        outra = self.h * G % P
        self.assertFalse(verificar_conhecimento(outra, prova, self.contexto))

    def test_sem_conhecer_x_a_prova_falha(self):
        prova = provar_conhecimento(aleatorio_zq(), self.h, self.contexto)
        self.assertFalse(verificar_conhecimento(self.h, prova, self.contexto))


if __name__ == "__main__":
    unittest.main()
