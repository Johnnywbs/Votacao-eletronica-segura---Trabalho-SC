# Sistema de Votação Eletrônica Seguro


Projeto e implementação, em Python, de um sistema de votação eletrônica que conduz uma eleição completa, do cadastro dos eleitores à apuração e auditoria do resultado. Os votos nunca são decifrados individualmente: apenas o total de cada candidato é revelado, e qualquer pessoa pode conferir o resultado usando somente dados públicos. As propriedades de segurança devem valer mesmo diante de participantes maliciosos, incluindo o próprio administrador do sistema.

## Datas

| Evento | Data |
|---|---|
| Entrega dos arquivos no Aprender3 | 23/11/2026 |
| Sorteio e divulgação da ordem das apresentações | 23/11/2026 |
| Apresentações presenciais | 25/11, 30/11 e 07/12/2026 |

Todos os grupos devem estar prontos para apresentar a partir de 25/11. A entrega é feita somente pelo Aprender3; links para repositórios públicos não são aceitos.

## Entregas e pontuação

| Item | Pontos |
|---|---|
| Código completo da aplicação | 3,5 |
| Instruções claras de compilação e execução | 0,5 |
| Relatório técnico (máximo de 10 páginas) | 3,0 |
| Apresentação presencial | 3,0 |

Critérios de avaliação do código:

| Critério | Pontos |
|---|---|
| Cifragem dos votos e apuração homomórfica corretas | 1,0 |
| Geração da chave conjunta e decifração pelas autoridades | 0,75 |
| Quadro público encadeado por hashes e detecção de adulteração | 0,75 |
| Assinaturas, elegibilidade, unicidade e recibo do eleitor | 0,5 |
| Programa auditor independente | 0,5 |

## Como a eleição funciona

1. **Configuração.** Define-se o grupo (primo de pelo menos 2048 bits, podendo ser padronizado), pelo menos 2 candidatos e pelo menos 3 autoridades eleitorais.
2. **Chave conjunta.** Cada autoridade gera sua chave privada `x_i` e publica `h_i = g^x_i`. A chave pública da eleição é o produto `h = ∏ h_i`. Ninguém conhece a chave privada completa.
3. **Cadastro.** Cada eleitor possui um par de chaves RSA cadastrado antes do início da votação.
4. **Votação.** Para cada candidato, o eleitor cifra 1 (candidato escolhido) ou 0 (demais) como `(g^r, g^m · h^r)` e assina a cédula. O servidor aceita apenas eleitores cadastrados e apenas um voto por eleitor, publica a cédula no quadro público e emite um recibo assinado.
5. **Encerramento e apuração.** As cifras de todas as cédulas são multiplicadas, por candidato, e apenas o total é decifrado, com a participação de todas as autoridades.
6. **Auditoria.** Um programa separado do servidor, usando apenas dados públicos, verifica a eleição e indica se ela é válida ou foi adulterada.

## Arquitetura obrigatória

- **ElGamal exponencial.** Cada voto `m ∈ {0, 1}` é cifrado como `(g^r, g^m · h^r)`. A apuração multiplica as cifras de todas as cédulas, de modo que apenas o total de votos de cada candidato seja decifrado.
- **Chave conjunta das autoridades.** Pelo menos 3 autoridades. Cada uma gera `x_i`; a chave pública da eleição é o produto dos `h_i`. A decifração exige a participação de todas, e nenhuma delas, nem o administrador, conhece a chave privada completa.
- **Quadro público.** Somente de acréscimo, encadeado por funções hash, contendo a identificação do eleitor, a cédula cifrada e a assinatura do eleitor.
- **Assinaturas digitais.** Cada eleitor tem um par de chaves cadastrado antes da votação e assina sua cédula. O servidor emite ao eleitor um recibo assinado da cédula recebida.

## Requisitos de segurança

| Requisito | Descrição |
|---|---|
| Sigilo do voto | Nenhuma entidade isolada, incluindo o administrador, descobre o voto de um eleitor, nem pela ordem ou pelo momento da votação |
| Integridade | Nenhuma cédula registrada pode ser alterada, removida, reordenada ou inserida indevidamente sem detecção |
| Elegibilidade | Somente eleitores previamente cadastrados podem votar |
| Unicidade | Cada eleitor vota no máximo uma vez |
| Justiça | Nenhum resultado parcial é conhecido antes do encerramento |
| Verificabilidade individual | O eleitor pode conferir que sua cédula consta no quadro público |
| Auditabilidade | Auditor independente verifica cadeia de hashes, assinaturas, elegibilidade, unicidade e produto homomórfico |

## Restrições

- Não é permitido usar sistemas ou bibliotecas de votação eletrônica prontos, nem bibliotecas que implementem ElGamal, cifragem homomórfica ou os protocolos do trabalho.
- São permitidas apenas primitivas básicas: aritmética modular, funções hash, geradores de números aleatórios criptograficamente seguros e bibliotecas de assinatura RSA.
- Os parâmetros do grupo devem ter tamanho adequado à segurança atual (primo de pelo menos 2048 bits). Grupos padronizados são permitidos.
- Uso de IA para gerar código ou partes do relatório só é permitido se o aluno compreender plenamente e souber explicar em detalhe cada trecho produzido.

## Divisão do trabalho

### Pessoa 1: cifragem e apuração

- Parâmetros do grupo (primo de pelo menos 2048 bits)
- ElGamal exponencial: cifrar 0 ou 1 como `(g^r, g^m · h^r)`, uma cifra por candidato
- Produto das cifras de todas as cédulas e obtenção do total a partir de `g^T`
- CLI que conduz as etapas e instruções de compilação e execução
- Relatório: esquema de cifragem e apuração, parâmetros e justificativa, item (i), modelo de ameaças
- Demo: eleição completa com 3 eleitores e 3 autoridades

### Pessoa 2: autoridades

- Cada autoridade gera `x_i` e publica `h_i`
- Chave da eleição como produto dos `h_i`
- Decifração do total com a participação de todas
- Falha da apuração quando falta uma autoridade
- Relatório: chave conjunta e decifração, itens (ii) e (iii)
- Demo: apuração sem todas as autoridades

### Pessoa 3: eleitor e servidor

- Par de chaves RSA por eleitor e cadastro antes da votação
- Assinatura da cédula pelo eleitor
- Servidor: verificação de assinatura, elegibilidade e unicidade
- Recibo assinado pelo servidor
- Conferência, pelo eleitor, de que a cédula está no quadro
- Relatório: autenticação dos eleitores, verificação individual, item (iv)
- Demo: voto duplo rejeitado

### Pessoa 4: quadro e auditor

- Quadro somente de acréscimo, encadeado por hash, com identificação do eleitor, cédula cifrada e assinatura
- Auditor independente do servidor, lendo só dados públicos: cadeia de hashes, assinaturas, elegibilidade, unicidade, produto homomórfico, veredito válida ou adulterada
- Relatório: integridade do quadro, procedimento de auditoria
- Demo: adulteração de uma cédula e detecção

### Todos

- Arquitetura e análise de como cada requisito é atendido
- Dificuldades encontradas e aprendizados
- Preparo para a arguição individual

## Fora do enunciado, mas que vamos tratar

1. **Formato único da cédula em bytes** (pessoas 1, 3 e 4). O que é assinado e o que entra no hash precisa ser gerado do mesmo jeito por todos, senão as verificações falham.
2. **Última autoridade escolhendo a chave** (pessoa 2). Se os `h_i` são publicados em sequência, a última autoridade pode calcular o seu a partir dos outros e passar a conhecer a chave privada completa. Cada autoridade publica o hash de `h_i` antes de revelar o valor.
3. **Servidor reescrevendo o quadro** (pessoas 3 e 4). O servidor pode remover uma cédula e recalcular toda a cadeia sem que o auditor perceba. O recibo inclui o hash da entrada no quadro, e assim o eleitor detecta a remoção ao conferir sua cédula.
4. **Cédulas inseridas depois do encerramento** (pessoa 4). O hash final do quadro é publicado no encerramento, antes da apuração, e conferido pelo auditor.

Limitação apenas citada no relatório, sem implementação: uma autoridade pode fornecer uma decifração parcial errada e alterar o total, e o auditor não tem como verificar isso com os mecanismos exigidos.

## Relatório técnico

Máximo de 10 páginas, contendo:

- Descrição completa da arquitetura, incluindo as entidades do sistema (eleitores, servidor de votação, autoridades eleitorais, quadro público e auditor) e suas responsabilidades
- Modelo de ameaças: adversários considerados (administrador malicioso, autoridade desonesta, eleitor desonesto, observador da rede) e o que cada um é capaz de fazer
- Esquema de cifragem dos votos e apuração sem decifrar votos individuais
- Geração da chave conjunta e decifração do resultado pelas autoridades
- Mecanismos de integridade do quadro público e de autenticação dos eleitores
- Procedimento de auditoria e de verificação individual do voto
- Parâmetros e algoritmos criptográficos utilizados (grupo, tamanho de chaves, função hash) e justificativa
- Análise de segurança: como cada requisito é atendido e quais são as limitações
- Principais dificuldades e aprendizados

Itens obrigatórios da análise de segurança:

| Item | Pergunta | Resposta |
|---|---|---|
| (i) | O que acontece se um eleitor cifrar um valor diferente de 0 ou 1? | Com os mecanismos exigidos, não é detectado e distorce o total. Limitação. |
| (ii) | O que acontece se todas as autoridades conspirarem? | Conseguem decifrar cédulas individuais, e o sigilo acaba. |
| (iii) | O que acontece se uma autoridade não participar da apuração? | Não há apuração. |
| (iv) | O recibo permite ao eleitor provar a terceiros em quem votou? | O eleitor conhece o `r` usado na cifragem e pode revelá-lo para provar o voto. |

## Apresentação

10 minutos de apresentação e demonstração, seguidos de até 10 minutos de arguição. Todos os integrantes apresentam pelo menos uma parte. A arguição é individual, e a nota pode ser diferente entre os integrantes.

A demonstração ao vivo deve incluir:

- [ ] Uma eleição completa com pelo menos 3 eleitores e 3 autoridades
- [ ] A tentativa de um eleitor votar duas vezes e a sua rejeição
- [ ] A adulteração de uma cédula no quadro público e a sua detecção pelo auditor
- [ ] A tentativa de apuração sem a participação de todas as autoridades e a sua falha

## Como executar

A preencher quando o código estiver pronto.
