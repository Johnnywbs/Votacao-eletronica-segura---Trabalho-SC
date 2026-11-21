#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
export PYTHONUTF8=1
if [ -z "${PY:-}" ]; then
  if command -v python >/dev/null 2>&1; then PY=python; else PY=python3; fi
fi

pausa() {
  echo
  echo "### $1"
  if [ "${PAUSA:-1}" = "1" ]; then read -r -p "[Enter para continuar] "; fi
}

pausa "1. Configuração: 3 candidatos e 3 autoridades"
$PY main.py resetar
$PY main.py configurar --eleicao turma2026 --candidatos Azul Verde Amarelo --autoridades 3

pausa "2. Chave conjunta: cada autoridade publica h_i com prova de Schnorr e confere a chave"
for i in 1 2 3; do $PY main.py autoridade-gerar --id $i; done
for i in 1 2 3; do $PY main.py autoridade-conferir --id $i; done

pausa "3. Cadastro de 4 eleitores e abertura da votação"
for e in alice bruno carla davi; do $PY main.py cadastrar --eleitor $e; done
$PY main.py abrir-votacao

pausa "4. Votação (cada cédula leva provas de que cada voto é 0 ou 1)"
$PY main.py votar --eleitor alice --candidato Azul
$PY main.py votar --eleitor bruno --candidato Verde
$PY main.py votar --eleitor carla --candidato Azul

pausa "5. Alice tenta votar de novo (deve ser rejeitada)"
$PY main.py votar --eleitor alice --candidato Verde

pausa "6. Davi (desonesto) tenta cifrar o valor 2 (deve ser rejeitado)"
$PY voto_invalido.py --eleitor davi --valor 2

pausa "7. Encerramento: hash final assinado e divulgado"
$PY main.py encerrar
HASH=$($PY -c "import json; print(json.load(open('publico/cabeca.json'))['hash_final'])")

pausa "8. Só as autoridades 1 e 2 decifram: a apuração falha"
$PY main.py autoridade-decifrar --id 1
$PY main.py autoridade-decifrar --id 2
$PY main.py apurar
echo "Forçando a conta mesmo sem a autoridade 3:"
$PY main.py apurar --forcar

pausa "9. Autoridade 3 decifra e o resultado sai"
$PY main.py autoridade-decifrar --id 3
$PY main.py apurar

pausa "10. Verificação individual e auditoria (com o hash divulgado)"
$PY main.py verificar-recibo --eleitor alice
$PY auditor.py publico --hash-esperado "$HASH"
rm -rf .backup_demo && cp -r publico .backup_demo

pausa "11. Administrador adultera a cédula 0 no quadro"
$PY adulterar.py --indice 0
$PY auditor.py publico
rm -rf publico && cp -r .backup_demo publico

pausa "12. Adulteração com a cadeia de hashes recalculada"
$PY adulterar.py --indice 0 --recalcular
$PY auditor.py publico --hash-esperado "$HASH"
$PY main.py verificar-recibo --eleitor alice
rm -rf publico && cp -r .backup_demo publico

pausa "13. Autoridade desonesta desvia um voto na decifração"
$PY adulterar.py --decifracao
$PY auditor.py publico
rm -rf publico && cp -r .backup_demo publico && rm -rf .backup_demo
echo
echo "Dados restaurados para a eleição válida."
