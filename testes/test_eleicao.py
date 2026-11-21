import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import autoridade
import eleitor
import quadro
import servidor
from util import ErroVotacao, caminho_publico
from voto_invalido import cedula_invalida

RAIZ = Path(__file__).resolve().parent.parent


def rodar(*comando):
    return subprocess.run([sys.executable, *comando], cwd=RAIZ, env=os.environ.copy(),
                          capture_output=True, text=True, check=False)


class TesteEleicao(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        os.environ["VOTACAO_DIR"] = self.pasta.name
        servidor.configurar("teste", ["A", "B"], 3)
        for i in (1, 2, 3):
            autoridade.gerar_chave(i)
        for nome in ("ana", "beto", "caio", "davi"):
            eleitor.gerar_e_cadastrar(nome)

    def tearDown(self):
        self.pasta.cleanup()

    def votar_todos(self):
        servidor.abrir_votacao()
        for nome, voto in (("ana", "A"), ("beto", "B"), ("caio", "A")):
            eleitor.votar(nome, voto)

    def decifrar_todas(self):
        for i in (1, 2, 3):
            autoridade.decifrar_parcial(i)

    def apurar_completo(self):
        servidor.encerrar()
        self.decifrar_todas()
        return autoridade.apurar_resultado()

    def auditar(self, *extra):
        return rodar("auditor.py", str(Path(self.pasta.name) / "publico"), *extra)

    def test_votacao_so_abre_com_todas_as_chaves(self):
        servidor.configurar("outra", ["A", "B"], 3)
        autoridade.gerar_chave(1)
        eleitor.gerar_e_cadastrar("ana")
        self.assertIsNone(servidor.ler_publico("autoridades.json")["chave_conjunta"])
        with self.assertRaisesRegex(ErroVotacao, "Faltam chaves"):
            servidor.abrir_votacao()

    def test_autoridade_confere_chave_honesta(self):
        self.assertEqual(autoridade.conferir(1), servidor.ler_publico("autoridades.json")["chave_conjunta"])

    def test_resultado_correto(self):
        self.votar_todos()
        self.assertEqual(self.apurar_completo(), {"A": 2, "B": 1})

    def test_voto_duplo_rejeitado(self):
        self.votar_todos()
        with self.assertRaisesRegex(ErroVotacao, "já votou"):
            eleitor.votar("ana", "B")

    def test_eleitor_nao_cadastrado(self):
        servidor.abrir_votacao()
        with self.assertRaisesRegex(ErroVotacao, "não cadastrado"):
            servidor.receber_cedula("intruso", [["2", "2"], ["2", "2"]], {}, "00")

    def test_cadastro_depois_de_abrir(self):
        servidor.abrir_votacao()
        with self.assertRaises(ErroVotacao):
            eleitor.gerar_e_cadastrar("atrasado")

    def test_assinatura_de_outro_eleitor(self):
        servidor.abrir_votacao()
        recibo_ana = eleitor.votar("ana", "A")
        entrada = quadro.ler()["entradas"][recibo_ana["indice"]]
        with self.assertRaisesRegex(ErroVotacao, "Assinatura"):
            servidor.receber_cedula("beto", entrada["cedula"], entrada["provas"], entrada["assinatura"])

    def test_voto_com_valor_dois_rejeitado(self):
        servidor.abrir_votacao()
        with self.assertRaisesRegex(ErroVotacao, "Prova de validade"):
            servidor.receber_cedula("davi", *cedula_invalida("davi", 2))

    def test_auditor_pega_cedula_invalida_inserida_direto(self):
        self.votar_todos()
        cedula_json, provas, assinatura_eleitor = cedula_invalida("davi", 2)
        quadro.acrescentar("davi", cedula_json, provas, assinatura_eleitor)
        servidor.encerrar()
        resultado = self.auditar()
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("prova de que cada voto é 0 ou 1", resultado.stdout)

    def test_voto_depois_de_encerrar(self):
        self.votar_todos()
        servidor.encerrar()
        with self.assertRaises(ErroVotacao):
            eleitor.votar("davi", "A")

    def test_decifrar_antes_de_encerrar(self):
        self.votar_todos()
        with self.assertRaises(ErroVotacao):
            autoridade.decifrar_parcial(1)

    def test_apuracao_sem_uma_autoridade(self):
        self.votar_todos()
        servidor.encerrar()
        autoridade.decifrar_parcial(1)
        autoridade.decifrar_parcial(2)
        with self.assertRaisesRegex(ErroVotacao, "faltam"):
            autoridade.apurar_resultado()
        with self.assertRaisesRegex(ErroVotacao, "não deu um total"):
            autoridade.apurar_resultado(forcar=True)

    def test_apuracao_recusa_decifracao_falsa(self):
        self.votar_todos()
        self.apurar_completo()
        rodar("adulterar.py", "--decifracao")
        with self.assertRaisesRegex(ErroVotacao, "Chaum-Pedersen"):
            autoridade.apurar_resultado()

    def test_recibo(self):
        self.votar_todos()
        self.assertIn("confere", eleitor.verificar_recibo("beto"))

    def test_auditor_eleicao_valida(self):
        self.votar_todos()
        self.apurar_completo()
        hash_final = servidor.ler_publico("cabeca.json")["hash_final"]
        resultado = self.auditar("--hash-esperado", hash_final)
        self.assertEqual(resultado.returncode, 0, resultado.stdout)
        self.assertIn("ELEIÇÃO VÁLIDA", resultado.stdout)

    def test_auditor_detecta_adulteracao_de_cedula(self):
        self.votar_todos()
        self.apurar_completo()
        hash_final = servidor.ler_publico("cabeca.json")["hash_final"]
        for extra in ([], ["--recalcular"]):
            original = caminho_publico("quadro.json").read_text()
            rodar("adulterar.py", "--indice", "1", *extra)
            resultado = self.auditar("--hash-esperado", hash_final)
            self.assertEqual(resultado.returncode, 1, resultado.stdout)
            self.assertIn("assinatura do eleitor inválida", resultado.stdout)
            caminho_publico("quadro.json").write_text(original)

    def test_auditor_detecta_autoridade_desonesta(self):
        self.votar_todos()
        self.apurar_completo()
        rodar("adulterar.py", "--decifracao")
        resultado = self.auditar()
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("decifração parcial falsificada", resultado.stdout)
        self.assertIn("[OK]    soma dos totais", resultado.stdout)

    def test_auditor_detecta_remocao(self):
        self.votar_todos()
        self.apurar_completo()
        dados = json.loads(caminho_publico("quadro.json").read_text())
        dados["entradas"].pop()
        caminho_publico("quadro.json").write_text(json.dumps(dados))
        self.assertEqual(self.auditar().returncode, 1)

    def test_auditor_detecta_quadro_reconstruido(self):
        self.votar_todos()
        self.apurar_completo()
        resultado = self.auditar("--hash-esperado", "0" * 64)
        self.assertIn("hash final igual ao publicado fora do sistema", resultado.stdout)
        self.assertEqual(resultado.returncode, 1)


if __name__ == "__main__":
    unittest.main()
