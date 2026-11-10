# Sistema de Votação Eletrônica Seguro

Sistema de votação eletrônica em Python que conduz uma eleição completa, do cadastro dos eleitores à apuração e auditoria do resultado. Os votos nunca são decifrados individualmente: apenas o total de cada candidato é revelado, e qualquer pessoa pode conferir o resultado usando somente dados públicos.

O sistema é projetado para manter suas propriedades de segurança mesmo diante de participantes maliciosos, incluindo o próprio administrador.

## Entidades

| Entidade | Responsabilidade |
|---|---|
| Eleitor | Gera seu par de chaves RSA, cifra e assina a cédula, confere que ela consta no quadro público |
| Servidor de votação | Verifica assinatura, elegibilidade e unicidade, publica a cédula no quadro e emite o recibo assinado |
| Autoridades eleitorais | Geram a chave conjunta da eleição e decifram, juntas, apenas o total de cada candidato |
| Quadro público | Registro somente de acréscimo, encadeado por hash, com todas as cédulas aceitas |
| Auditor | Programa independente do servidor que valida a eleição a partir dos dados públicos |

## Como funciona

### 1. Configuração

Define-se o grupo `(p, q, g)`, os candidatos (pelo menos 2) e as autoridades eleitorais (pelo menos 3).

### 2. Chave conjunta

Cada autoridade gera sua chave privada `x_i` e publica `h_i = g^x_i`. A chave pública da eleição é o produto:

```
h = h_1 · h_2 · ... · h_n
```

A chave privada correspondente, `x = x_1 + x_2 + ... + x_n`, nunca é montada em lugar nenhum. Nenhuma autoridade, nem o administrador, a conhece.

Antes de revelar `h_i`, cada autoridade publica o hash desse valor. Isso impede que a última autoridade escolha sua chave em função das demais e passe a conhecer a chave privada completa.

### 3. Cadastro de eleitores

Cada eleitor gera um par de chaves RSA. As chaves públicas formam a lista de eleitores, fechada antes do início da votação.

### 4. Votação

O voto é cifrado com ElGamal exponencial. Para cada candidato, o eleitor produz uma cifra de 1 (candidato escolhido) ou de 0 (demais):

```
(g^r, g^m · h^r)    com m ∈ {0, 1} e r aleatório
```

O eleitor assina a cédula com sua chave RSA e a envia ao servidor, que:

1. verifica a assinatura;
2. confere que o eleitor está cadastrado (elegibilidade);
3. confere que o eleitor ainda não votou (unicidade);
4. acrescenta a cédula ao quadro público;
5. devolve um recibo assinado, contendo o hash da entrada no quadro.

### 5. Quadro público

Cada entrada contém a identificação do eleitor, a cédula cifrada, a assinatura do eleitor e o hash da entrada anterior. Alterar, remover ou reordenar qualquer cédula quebra a cadeia de hashes.

No encerramento, o hash final do quadro é publicado, de modo que nenhuma cédula possa ser inserida depois.

### 6. Apuração

As cifras de todas as cédulas são multiplicadas, componente a componente, para cada candidato:

```
(A, B) = (∏ g^r_j, ∏ g^m_j · h^r_j) = (g^R, g^T · h^R)
```

onde `T` é o total de votos do candidato. Cada autoridade fornece sua decifração parcial `d_i = A^x_i`, e então:

```
g^T = B / (d_1 · d_2 · ... · d_n)
```

`T` é obtido por busca, pois é no máximo o número de eleitores. Se alguma autoridade não participar, a apuração falha.

### 7. Auditoria

O auditor lê apenas os dados públicos e verifica:

- a cadeia de hashes do quadro;
- a assinatura de cada cédula;
- que todo votante está na lista de eleitores cadastrados;
- que nenhum eleitor votou mais de uma vez;
- que o produto homomórfico das cédulas corresponde ao que foi apurado.

Ao final, indica se a eleição é válida ou se foi adulterada.

## Propriedades de segurança

| Propriedade | Como é atendida |
|---|---|
| Sigilo do voto | Cédulas individuais nunca são decifradas; a decifração exige todas as autoridades e é aplicada apenas ao produto |
| Integridade | Quadro encadeado por hash, recibo assinado pelo servidor e hash final publicado no encerramento |
| Elegibilidade | Assinatura RSA verificada contra a lista de eleitores cadastrados |
| Unicidade | O servidor rejeita a segunda cédula de um mesmo eleitor, e o auditor confere |
| Justiça | Nenhum total pode ser decifrado sem todas as autoridades, que só atuam após o encerramento |
| Verificabilidade individual | O eleitor localiza sua cédula no quadro e a compara com o recibo |
| Auditabilidade | Auditor independente, baseado apenas em dados públicos |

## Parâmetros criptográficos

| Componente | Escolha |
|---|---|
| Grupo | Grupo padronizado com primo de 2048 bits (RFC 3526, grupo 14) |
| Cifragem | ElGamal exponencial, implementado sobre aritmética modular |
| Assinatura | RSA de 2048 bits |
| Hash | SHA-256 |
| Aleatoriedade | Módulo `secrets` do Python |

ElGamal, a operação homomórfica e a chave conjunta são implementados diretamente sobre aritmética modular. Bibliotecas externas são usadas apenas para hash, aleatoriedade e assinatura RSA.

## Limitações

- **Voto fora de {0, 1}.** Não há prova de que a cifra contém 0 ou 1. Um eleitor desonesto pode cifrar outro valor e distorcer o total sem ser detectado.
- **Conluio de todas as autoridades.** Juntas, elas conseguem decifrar cédulas individuais, e o sigilo deixa de existir.
- **Autoridade ausente.** A decifração exige todas as autoridades. Se uma não participar, não há apuração.
- **Recibo e coerção.** O eleitor conhece o `r` usado na cifragem e pode revelá-lo para provar a terceiros em quem votou.
- **Decifração parcial incorreta.** Uma autoridade pode fornecer um `d_i` errado e alterar o total, e o auditor não tem como verificar isso.

## Como executar

A preencher.
