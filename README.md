# Sistema de Votação Eletrônica Seguro

Sistema de votação eletrônica em Python que conduz uma eleição completa, do cadastro dos eleitores à apuração e auditoria do resultado. Os votos nunca são decifrados individualmente: apenas o total de cada candidato é revelado, e qualquer pessoa pode conferir o resultado usando somente dados públicos.

O sistema mantém suas propriedades de segurança mesmo diante de participantes maliciosos: eleitores que tentam votar duas vezes ou cifrar valores inválidos, autoridades que tentam falsificar a decifração e um administrador que tenta adulterar o quadro público.

## Entidades

| Entidade | Responsabilidade |
| --- | --- |
| Eleitor | Gera seu par de chaves RSA, cifra a cédula, prova que ela é válida, assina e confere que ela consta no quadro público |
| Servidor de votação | Verifica assinatura, elegibilidade, unicidade e as provas de validade, publica a cédula no quadro e emite o recibo assinado |
| Autoridades eleitorais | Geram a chave conjunta (cada uma prova que conhece sua parte) e decifram, juntas, apenas o total de cada candidato, provando que decifraram corretamente |
| Quadro público | Registro somente de acréscimo, encadeado por hash, com todas as cédulas aceitas e suas provas |
| Auditor | Programa independente do servidor que valida a eleição, inclusive todas as provas, a partir dos dados públicos |

## Como funciona

### 1. Configuração

Define-se o grupo `(p, q, g)`, os candidatos (pelo menos 2) e as autoridades eleitorais (pelo menos 3). O servidor gera seu par RSA e publica a chave pública.

### 2. Chave conjunta

Cada autoridade gera sua chave privada `x_i` e publica `h_i = g^x_i`. A chave pública da eleição é o produto:

```
h = h_1 · h_2 · ... · h_n = g^(x_1 + x_2 + ... + x_n)
```

A chave privada correspondente nunca é montada em lugar nenhum. Junto com `h_i`, cada autoridade publica uma **prova de Schnorr** de que conhece `x_i`, amarrada à eleição e ao seu número. Sem ela, uma autoridade que publicasse por último, ou o administrador, que edita o arquivo público, poderia trocar `h_3` por `g^a / (h_1 · h_2)` e passar a conhecer a chave inteira; como ninguém conhece o logaritmo desse valor, ninguém consegue gerar a prova. O servidor confere as provas antes de abrir a votação, cada autoridade confere que seu `h_i` está publicado (`autoridade-conferir`) e o eleitor confere tudo de novo antes de cifrar.

### 3. Cadastro de eleitores

Cada eleitor gera um par de chaves RSA. As chaves públicas formam a lista de eleitores, fechada antes do início da votação.

### 4. Votação

Para cada candidato, o eleitor cifra 1 (escolhido) ou 0 (demais) com ElGamal exponencial:

```
(g^r, g^m · h^r)    com m ∈ {0, 1} e r aleatório
```

Junto com a cédula, o eleitor envia provas de conhecimento zero não interativas (Fiat-Shamir):

- para cada cifra, uma **prova disjuntiva de Chaum-Pedersen (CDS)** de que ela contém 0 **ou** 1, sem revelar qual;
- para a cédula inteira, uma **prova de que o produto das cifras contém exatamente 1**, ou seja, um único voto.

As provas são amarradas à eleição e ao eleitor, então não podem ser copiadas. O eleitor assina cédula e provas com sua chave RSA. O servidor:

1. confere que o eleitor está cadastrado (elegibilidade);
2. verifica a assinatura;
3. confere que o eleitor ainda não votou (unicidade);
4. confere o formato e **verifica as provas de validade**;
5. acrescenta a cédula ao quadro público;
6. devolve um recibo assinado, com o hash da entrada no quadro.

### 5. Quadro público

Cada entrada contém o eleitor, a cédula cifrada, as provas, a assinatura do eleitor e o hash da entrada anterior. A primeira entrada aponta para um hash de gênese calculado sobre a configuração da eleição. No encerramento, o servidor assina o hash final e o comando mostra esse hash para ser **divulgado fora do sistema** (por exemplo, enviado aos fiscais). O auditor compara o quadro com esse valor.

### 6. Apuração

As cifras de todas as cédulas são multiplicadas, para cada candidato:

```
(A, B) = (g^R, g^T · h^R)
```

Cada autoridade recalcula esse produto a partir do quadro público, publica `d_i = A^x_i` com uma **prova de Chaum-Pedersen** de que usou o mesmo `x_i` da sua chave pública. A apuração confere todas as provas e calcula:

```
g^T = B / (d_1 · d_2 · ... · d_n)
```

`T` é obtido por busca, pois é no máximo o número de eleitores. Sem todas as autoridades, a apuração falha; uma decifração falsificada é rejeitada e a autoridade responsável é identificada.

### 7. Auditoria

O auditor lê apenas os dados públicos e verifica:

- os parâmetros do grupo (p = 2q + 1 e g de ordem q);
- as provas de Schnorr das autoridades e a chave conjunta;
- a cadeia de hashes, o hash final assinado e, se informado, o hash divulgado fora do sistema;
- a assinatura, a elegibilidade, a unicidade e as provas de validade de cada cédula;
- o produto homomórfico das cédulas;
- a prova de Chaum-Pedersen de cada decifração parcial;
- que cada total publicado confere com as decifrações e que a soma dos totais é o número de cédulas.

## Propriedades de segurança

| Propriedade | Como é atendida |
| --- | --- |
| Sigilo do voto | Cédulas nunca são decifradas individualmente; a decifração exige todas as autoridades e se aplica apenas ao produto; as provas não revelam o voto; a prova de Schnorr de cada `h_i` impede que o administrador monte uma chave conjunta que ele conheça |
| Integridade | Quadro encadeado por hash, assinaturas dos eleitores, recibo assinado, hash final assinado e divulgado externamente |
| Elegibilidade | Assinatura RSA verificada contra a lista de eleitores cadastrados |
| Unicidade | O servidor rejeita a segunda cédula de um mesmo eleitor, e o auditor confere |
| Validade das cédulas | Provas de conhecimento zero de que cada cifra é 0 ou 1 e de que há exatamente um voto |
| Apuração correta | Prova de Chaum-Pedersen em cada decifração parcial |
| Justiça | Nenhum total pode ser decifrado sem todas as autoridades, que só atuam após o encerramento |
| Verificabilidade individual | O eleitor localiza sua cédula no quadro e a compara com o recibo |
| Auditabilidade | Auditor independente, baseado apenas em dados públicos |

## Parâmetros criptográficos

| Componente | Escolha |
| --- | --- |
| Grupo | RFC 3526, grupo 14: primo seguro de 2048 bits, g = 2 |
| Cifragem | ElGamal exponencial, implementado sobre aritmética modular |
| Provas | Schnorr (conhecimento de `x_i`), Chaum-Pedersen e sua versão disjuntiva (CDS), não interativas por Fiat-Shamir com SHA-256 |
| Assinatura | RSA de 2048 bits com PSS e SHA-256 |
| Hash | SHA-256 |
| Aleatoriedade | Módulo `secrets` do Python |

ElGamal, a operação homomórfica, a chave conjunta e as provas de conhecimento zero são implementados diretamente sobre aritmética modular. Bibliotecas externas são usadas apenas para hash, aleatoriedade e assinatura RSA.

## Limitações

- **Conluio de todas as autoridades.** Juntas, elas conseguem decifrar cédulas individuais, e o sigilo deixa de existir.
- **Autoridade ausente.** A decifração exige todas as autoridades. Se uma não participar, não há apuração (um esquema t-de-n de Shamir resolveria).
- **Recibo e coerção.** O eleitor pode guardar o `r` usado na cifragem e revelá-lo para provar a terceiros em quem votou.
- **Simulação em uma máquina.** Na demonstração, todas as entidades rodam no mesmo computador e as chaves privadas (de autoridades, eleitores e servidor) ficam em arquivos sem senha em `privado/`. Numa implantação real, cada entidade rodaria em uma máquina própria.
- **Integridade do quadro contra o administrador.** Quem controla o servidor pode recusar cédulas ou reconstruir o arquivo do quadro. A recusa é percebida pela falta de recibo, e a reconstrução é detectada pelas assinaturas dos eleitores, pelos recibos e pelo hash final divulgado fora do sistema; o sistema depende de esse hash ser de fato divulgado e conferido.
- **Substituição de todas as autoridades.** A prova de Schnorr impede que o administrador conheça a chave conjunta enquanto pelo menos um `h_i` verdadeiro estiver publicado. Se ele trocar todas as autoridades por chaves suas, as provas fecham; isso só é percebido pelas próprias autoridades (`autoridade-conferir`) ou se cada uma divulgar o hash do seu `h_i` fora do sistema, como o hash final.
- **Cadastro de eleitores.** O administrador controla a lista durante a preparação e pode incluir eleitores fantasmas ou trocar a chave de um eleitor. A lista fica congelada na gênese ao abrir a votação; cada eleitor deve conferir sua chave antes disso.

## Como executar

### Requisitos

- Python 3.10 ou superior
- Biblioteca `cryptography`

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
```

### Demonstração completa

```bash
./roteiro_demo.sh          # com pausas entre as etapas (Enter para avançar)
PAUSA=0 ./roteiro_demo.sh  # sem pausas
```

No Windows, rode pelo Git Bash. O roteiro já força a saída em UTF-8; para rodar comandos manualmente no Git Bash, execute antes `export PYTHONUTF8=1`, senão os acentos podem aparecer trocados. O roteiro cobre os quatro itens exigidos (eleição com 3 eleitores e 3 autoridades, voto duplo rejeitado, apuração sem todas as autoridades falhando e adulteração detectada pelo auditor) e três ataques extras: voto com valor 2, cadeia de hashes recalculada e autoridade que falsifica a decifração.

### Passo a passo manual

```bash
python main.py resetar
python main.py configurar --eleicao turma2026 --candidatos Azul Verde Amarelo --autoridades 3
python main.py autoridade-gerar --id 1                    # repetir para 2 e 3
python main.py autoridade-conferir --id 1                 # repetir para 2 e 3
python main.py cadastrar --eleitor alice                  # repetir para cada eleitor
python main.py abrir-votacao
python main.py votar --eleitor alice --candidato Azul
python main.py encerrar                                   # anote o hash final mostrado
python main.py autoridade-decifrar --id 1                 # repetir para 2 e 3
python main.py apurar
python main.py verificar-recibo --eleitor alice
python auditor.py publico --hash-esperado <hash final>
```

`python main.py --help` lista todos os comandos.

### Testes

```bash
python -m unittest discover -s testes -t .
```

## Estrutura do código

| Arquivo | Conteúdo |
| --- | --- |
| `params.py` | Grupo da RFC 3526 e verificação de que g gera o subgrupo de ordem q |
| `elgamal.py` | Cifragem, produto homomórfico e logaritmo discreto pequeno |
| `provas.py` | Provas de conhecimento zero: conhecimento de x_i (Schnorr), voto 0 ou 1 (CDS), soma igual a 1 e decifração correta (Chaum-Pedersen); conferência das chaves das autoridades |
| `assinatura.py` | Geração de chaves, assinatura e verificação RSA-PSS |
| `util.py` | JSON canônico, SHA-256 e leitura/escrita de arquivos |
| `autoridade.py` | Geração de x_i com prova de Schnorr, chave conjunta, conferência pela autoridade, decifração parcial com prova e apuração |
| `quadro.py` | Quadro público encadeado por hash |
| `servidor.py` | Fases da eleição, cadastro, recepção e validação de cédulas, recibo e encerramento |
| `eleitor.py` | Chaves do eleitor, voto com provas e verificação do recibo |
| `main.py` | Interface de linha de comando |
| `auditor.py` | Auditor independente (não importa nenhum outro módulo do projeto) |
| `adulterar.py` | Ataques do administrador (cédula) e da autoridade desonesta, usados na demonstração |
| `voto_invalido.py` | Ataque do eleitor desonesto, usado na demonstração |
| `roteiro_demo.sh` | Roteiro da apresentação |
| `testes/` | Testes automatizados |
| `EXPLICACAO.txt` | Explicação de cada arquivo e função do código |

Os dados ficam em `publico/` (lidos pelo auditor) e `privado/` (uma pasta por entidade).
