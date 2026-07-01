# Requisitos Básicos do MVP - Isomera

Este arquivo lista os requisitos funcionais e não funcionais para o **MVP (Minimum Viable Product)** do projeto **Isomera**.

---

## **Requisitos Funcionais**

### **Entradas**
1. **Número de domínios**:
   - O usuário deve informar o número de domínios a serem criados.
   
2. **Configuração de tabelas por domínio**:
   - O usuário pode definir a quantidade de **SOR**, **SOT** e **SPEC** para cada domínio:
     - Exemplo: 
       - Domínio 1: 2 SOR, 1 SOT.
       - Domínio 2: 4 SOR, 2 SOT, 1 SPEC.
       - Domínio 3: 1 SOT, 1 SPEC.

3. **Distribuições de probabilidade para relações**:
   - O usuário deve escolher uma das 10 distribuições de probabilidade mais comuns para reger a criação das relações:
     - **Default**: Se nenhuma distribuição for especificada, o app seleciona aleatoriamente entre as 10 mais comuns.

4. **Máximo de linhas por tabela**:
   - O usuário deve especificar o número máximo de linhas que uma tabela pode conter.
   - O número real será gerado de forma randômica dentro desse limite.

5. **Número de colunas por tabela**:
   - O número de colunas é gerado de forma randômica.
   - O usuário pode ajustar o limite mínimo/máximo de colunas.

6. **Tipagem das colunas**:
   - Tipos de dados disponíveis: `string`, `integer`, `date`, etc.
   - Comprimento (length) das colunas é gerado de forma randômica dentro de limites razoáveis.

---

### **Regras de Relações**
1. **Definição das relações**:
   - Relações possíveis: `INSERT`, `JOIN`, `CREATE`, `VIEW`, `SUBQUERY`, etc.
   - **Regra geral**:
     - **SOR**: São as origens (dados do sistema).
     - **SOT**: Podem ser criadas a partir de uma ou mais **SOR**.
     - **SPEC**: Podem ser criadas a partir de uma ou mais **SOT**.
     - Exceções permitidas:
       - Uma **SOT** pode ser criada com base em uma ou mais **SPEC**.
       - Uma **SPEC** pode ser criada com base em uma ou mais **SOR**.

2. **Distribuição aleatória de relações**:
   - As relações entre tabelas devem ser geradas aleatoriamente de acordo com as distribuições escolhidas pelo usuário.

3. **Chaves primárias (PKs)**:
   - Todas as tabelas devem ter pelo menos uma **PK**.
   - Relações como **JOIN** devem respeitar as **PKs** e garantir consistência entre os domínios.

---

### **Visualização**
1. **Lineage**:
   - Visualização básica do fluxo de dados entre as tabelas (SOR → SOT → SPEC).
   - Representação hierárquica simples.

---

### **Validação e Qualidade**
1. **Check de qualidade**:
   - O app deve validar se as relações entre tabelas fazem sentido.
   - Regras:
     - Garantir que todas as **PKs** sejam únicas.
     - Garantir que relações de **JOIN** utilizem colunas compatíveis.
   - **Sugestão de Implementação**:
     - Validar se todas as relações têm correspondências lógicas e estão conectadas corretamente no lineage.
     - Gerar um relatório de inconsistências, caso existam.

---

## **Requisitos Não Funcionais**
1. **Simplicidade**:
   - A interface gráfica deve ser minimalista e intuitiva.
   - Implementação inicial focada apenas na visualização do lineage.

2. **Desempenho**:
   - A geração das tabelas, relações e lineage deve ser concluída em menos de 2 segundos para até 100 tabelas.

3. **Portabilidade**:
   - Compatível com SQLite3 no MVP.

4. **Escalabilidade futura**:
   - Estrutura de código modular para facilitar a inclusão de mais funcionalidades (FKs, métricas de qualidade, etc.).

---

## **Possíveis Melhorias Futuras (Além do MVP)**
1. **Adição de Foreign Keys (FKs)**:
   - Garantir consistência relacional com **PK-FK**.

2. **Exportação avançada**:
   - Adicionar suporte para exportação em outros formatos, como **JSON**.

3. **Visualizações interativas**:
   - Melhorar a visualização do lineage com interatividade (zoom, pan, detalhes ao clicar).

4. **Simulação de cenários**:
   - Permitir que o usuário ajuste distribuições ou regras e veja o impacto no lineage.

---

## **Resumo**
O MVP do Isomera se concentra em:
1. Criar uma arquitetura de dados simples com tabelas, relações e lineage.
2. Garantir que os dados gerados sejam consistentes e façam sentido em uma arquitetura de dados básica.
3. Oferecer uma visualização básica (lineage) para o usuário.

Esse escopo foi definido para ser implementado em 2 semanas com as horas disponíveis no cronograma.

---
## **Dependencias Python**

Para carregar os modelos GNN via pickle, o ambiente precisa ter:

- `torch`
- `torch-geometric`

---
## **Proposta de Interface para o MVP**

Esta seção descreve a interface gráfica do MVP, incorporando a possibilidade de selecionar distribuições de probabilidade para cada escolha, tornando o processo mais flexível e customizável.

---

### **Estrutura Geral da Interface**

A interface será dividida em três seções principais:
1. **Área de Configuração de Parâmetros** (Esquerda)
2. **Botões de Ação** (Centralizados na parte inferior)
3. **Área de Visualização do Lineage** (Direita)

---

### **1. Área de Configuração de Parâmetros**
- Localizada na lateral esquerda da tela.
- Contém os seguintes componentes:

| **Elemento**                     | **Tipo de Input**           | **Descrição**                                                                                   |
|-----------------------------------|-----------------------------|-------------------------------------------------------------------------------------------------|
| **Número de Domínios**            | Campo numérico              | Permite que o usuário informe o número de domínios a serem criados.                            |
| **Configuração por Domínio**      | Lista expansível            | Cada domínio pode ser configurado com:                                                         |
|                                   |                             | - Quantidade de SOR, SOT e SPEC.                                                               |
|                                   |                             | - Distribuições para linhas, colunas e tipos de dados.                                         |
| **Distribuições por Tabela**      | Dropdown com múltipla escolha | Permite escolher distribuições para diferentes características (linhas, colunas, tipagem).     |
| **Máximo de Linhas por Tabela**   | Campo numérico com dropdown | Define o limite máximo de linhas e permite escolher distribuições específicas (ex.: normal, uniforme). |
| **Número de Colunas por Tabela**  | Campo numérico com slider   | Permite configurar o intervalo (mínimo e máximo) de colunas por tabela com base em distribuições. |
| **Tipos de Dados por Coluna**     | Dropdown ou checkbox        | O usuário seleciona tipos de dados (string, integer, date, etc.) e associa distribuições.      |
| **Validar Relações**              | Botão toggle                | Ativa ou desativa a validação automática de relações entre tabelas.                            |

---

### **2. Botões de Ação**
- Localizados na parte inferior central da interface.
- Contêm os seguintes botões principais:

| **Botão**               | **Descrição**                                                                                   |
|--------------------------|-----------------------------------------------------------------------------------------------|
| **Gerar Lineage**        | Gera o lineage com base nos parâmetros configurados.                                          |
| **Exportar para XML**    | Exporta o lineage gerado no formato XML.                                                      |
| **Exportar para SQL**    | Gera o script SQL para criação das tabelas e insere os dados no padrão SQLite3.               |
| **Resetar Configuração** | Limpa todos os campos de configuração para iniciar um novo projeto.                           |

---

### **3. Área de Visualização do Lineage**
- Localizada no lado direito da tela.
- Exibe o **lineage** em uma visualização hierárquica básica.
- Características:
  - **Grafo Simples**:
    - Mostra as tabelas (SOR, SOT, SPEC) como nós.
    - Conexões entre os nós representam as relações (INSERT, JOIN, etc.).
  - **Cores Diferenciadas**:
    - Cada tipo de tabela (SOR, SOT, SPEC) é representado por uma cor distinta.
  - **Zoom e Pan**:
    - Permite ampliar ou mover a visualização.
  - **Detalhes ao Clicar**:
    - Exibe informações detalhadas da tabela ao clicar em um nó.

---

### **Detalhamento das Distribuições**

Cada componente configurável deve permitir a seleção de distribuições de probabilidade para personalizar o comportamento:

1. **Linhas por Tabela**:
   - O usuário escolhe uma ou mais distribuições, como:
     - Uniforme
     - Normal
     - Poisson
   - Exemplo: "Usar distribuição normal com média de 100 e desvio padrão de 15 para definir o número de linhas."

2. **Colunas por Tabela**:
   - Distribuições configuráveis para a quantidade de colunas por tabela.
   - Exemplo: "Distribuição uniforme entre 5 e 15 colunas."

3. **Tipos de Dados**:
   - Distribuições para a escolha dos tipos de dados:
     - 60% `integer`
     - 30% `string`
     - 10% `date`

4. **Relações**:
   - Configurações para definir relações entre tabelas (SOR → SOT → SPEC) baseadas em distribuições:
     - JOIN: 50%
     - INSERT: 30%
     - SUBQUERY: 20%

---

### **Exemplo Visual da Interface**

#### **Seção Esquerda (Configuração de Parâmetros)**
- Organize os campos de entrada em um layout vertical com grupos claros:
  - **Domínios e Configurações**:
    - Para cada domínio, inclua inputs para número de SOR, SOT, SPEC e distribuições específicas.
  - **Distribuições Globais**:
    - Configure distribuições padrões para linhas, colunas e tipos de dados.

#### **Parte Inferior (Botões de Ação)**
- Coloque os botões centralizados e em sequência horizontal:
  - **Gerar Lineage**, **Exportar para XML**, **Exportar para SQL**, **Resetar**.

#### **Seção Direita (Visualização do Lineage)**
- Use um espaço grande para o grafo.
- Adicione um placeholder simples no protótipo para representar os nós e conexões.

```plaintext
+---------------------------+---------------------------+
| Configuração de Parâmetros| Visualização do Lineage   |
|---------------------------|---------------------------|
| Número de Domínios: [___] | +-----------------------+ |
| Máx Linhas: [___]         | | [SOR] -- [SOT]        | |
| Tipagem: [x] String       | |   \-- [SPEC]          | |
|         [ ] Integer       | +-----------------------+ |
+---------------------------+---------------------------+
| [ Gerar ] [ Exportar ] [ Resetar ]                   |
+-----------------------------------------------------+
```

---

### **Dicas para o Protótipo no Draw.io**
1. **Use Retângulos**:
   - Representar campos de entrada e botões.
2. **Conexões Diretas**:
   - Desenhe linhas para ilustrar relações entre os nós na área de visualização.
3. **Cores Básicas**:
   - Diferencie visualmente os grupos de tabelas (SOR, SOT, SPEC).

---

### **Design Clean e Funcional**
Este layout garante que o usuário possa configurar rapidamente os parâmetros e visualizar os resultados sem sobrecarregar a interface. A simplicidade é essencial para o MVP, permitindo que a funcionalidade principal seja validada antes de melhorias adicionais.

#### Exemplos do Dall-E

![imagem](img/DALL·E%202024-11-22%2002.41.16%20-%20A%20clean,%20structured%20interface%20mockup%20for%20a%20data%20lineage%20application.%20On%20the%20left,%20a%20vertical%20panel%20titled%20'Configuration%20Parameters'%20with%20clearly%20spac.webp)

![imagem](img/bdad81d8-4bbd-4090-80af-024dc59400b3.webp)

![imagem](img/cad5c5b6-acd2-4949-9ec5-43a3681d4816.webp)

![imagem](img/61de8e47-4745-4cb2-86e4-d24b0f7a2382.webp)
