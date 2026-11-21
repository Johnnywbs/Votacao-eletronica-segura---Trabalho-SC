import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elgamal import aleatorio_zq, apurar, cifrar, elemento_valido, log_discreto, multiplicar
from params import G, P, Q


def cifrar_cedula(h, escolha, n_candidatos):
    return [cifrar(h, 1 if j == escolha else 0)[0] for j in range(n_candidatos)]


def decifrar_com_chave(x, cifra):
    c1, c2 = cifra
    return c2 * pow(c1, -x, P) % P


class TesteGrupoPequeno(unittest.TestCase):
    def test_cifra_e_decifra_a_mao(self):
        p, g, x, r, m = 23, 4, 3, 5, 1
        h = pow(g, x, p)
        c1, c2 = pow(g, r, p), pow(g, m, p) * pow(h, r, p) % p
        self.assertEqual(c2 * pow(c1, -x, p) % p, pow(g, m, p))


class TesteElGamal(unittest.TestCase):
    def setUp(self):
        self.x = aleatorio_zq()
        self.h = pow(G, self.x, P)

    def test_grupo(self):
        self.assertEqual(P.bit_length(), 2048)
        self.assertEqual(pow(G, Q, P), 1)

    def test_cifragem_aleatorizada(self):
        self.assertNotEqual(cifrar(self.h, 1)[0], cifrar(self.h, 1)[0])

    def test_homomorfismo(self):
        cifras = [cifrar(self.h, m)[0] for m in (1, 1, 0)]
        g_t = decifrar_com_chave(self.x, multiplicar(cifras))
        self.assertEqual(log_discreto(g_t, 3), 2)

    def test_cedula_tem_um_unico_voto(self):
        cedula = cifrar_cedula(self.h, 1, 3)
        valores = [log_discreto(decifrar_com_chave(self.x, cifra), 1) for cifra in cedula]
        self.assertEqual(valores, [0, 1, 0])
        self.assertTrue(all(elemento_valido(c1) and elemento_valido(c2) for c1, c2 in cedula))

    def test_apuracao_de_cinco_cedulas(self):
        escolhas = [0, 2, 2, 1, 2]
        cedulas = [cifrar_cedula(self.h, escolha, 3) for escolha in escolhas]
        totais = [log_discreto(decifrar_com_chave(self.x, total), 5) for total in apurar(cedulas, 3)]
        self.assertEqual(totais, [1, 1, 3])

    def test_log_discreto_fora_do_intervalo(self):
        with self.assertRaises(ValueError):
            log_discreto(pow(G, 10, P), 5)


if __name__ == "__main__":
    unittest.main()
