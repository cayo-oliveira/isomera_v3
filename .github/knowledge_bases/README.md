# Knowledge Bases — Referência & Guidelines

Toda referência, padrão, contexto e guideline vive aqui como **markdown files**.

São injetadas automaticamente nos prompts dos agentes quando relevantes.

## KBs planejadas

| Arquivo | Foco | Uso |
|---------|------|-----|
| `ieee_smc_standards.md` | Padrão IEEE SMC | Jamilson, Larissa (estrutura + escrita) |
| `isomera_context.md` | Contexto Isomera v1/v2 | Todos agentes |
| `writing_style_guide.md` | Guia de tom, clareza, narrativa | Larissa (editorial) |
| `methodology_guide.md` | Metodologia Isomera v2 | Paulo, Maysa (rigor) |
| `fedssa_context.md` | FedSSA review (IID, non-IID, etc.) | Paulo (teoria) |
| `vmamba_foundation.md` | VMamba foundation (SSM, SS2D, etc.) | Todos (contexto técnico) |
| `vmamba_mesh_encoding.md` | CanonSort, tensorização e componentes VMamba-Mesh | Paulo, Maysa, Orchestrator |
| `vmamba_mesh_reproducibility.md` | Reprodução de artigo, benchmarks e métricas esperadas | Paulo, Maysa, Orchestrator |
| `vmamba_mesh_interpretability.md` | ERF, rotas SS2D, canais e sensibilidade | Paulo, Maysa, Larissa |
| `vmamba_trainable_video_runbook.md` | VMamba-T/VMamba-Mesh-T, hiperparâmetros testados, roteiro de vídeo e campanha pendente | Todos (apresentação + validação) |
| `experimental_protocol.md` | Como validar, treinar, testar | Paulo (validação) |
| `graph_isomorphism_kb.md` | VF2, Node Match, isomorfismo | Maysa (algoritmos) |

## Como usar uma KB

### Em um agente

```markdown
# Paulo — Revisor Teórico

Você consulta a Knowledge Base:
- `.github/knowledge_bases/methodology_guide.md`
- `.github/knowledge_bases/experimental_protocol.md`

Quando encontrar problema teórico, cite a seção da KB relevante.
```

### Em uma skill

```yaml
# .github/skills/article_review/config.yaml

agents:
  paulo:
    knowledge_bases:
      - methodology_guide.md
      - experimental_protocol.md
    
  larissa:
    knowledge_bases:
      - writing_style_guide.md
      - ieee_smc_standards.md
```

### Injeção automática no prompt

```python
# TexLab/VS Code loader

def create_agent_prompt(agent_name, context):
    agent_spec = load_agent(agent_name)
    kbs = agent_spec.knowledge_bases
    
    kb_context = "\n\n".join([
        load_kb(kb) for kb in kbs
    ])
    
    prompt = f"""
{agent_spec.persona}

## Knowledge Base Context

{kb_context}

## Sua tarefa

{context}
"""
    return prompt
```

## Conteúdo esperado de uma KB

```markdown
# [Nome da KB]

## 1. Definições

[Termos-chave com definição precisa]

## 2. Princípios

[Princípios fundamentais, exemplos]

## 3. Checklist ou Guidelines

[Items verificáveis, formatação esperada]

## 4. Referências

[Links para papers, docs, files]

## 5. Exemplos

[Casos práticos, snippets de código]
```

## Como adicionar nova KB

1. Criar arquivo: `.github/knowledge_bases/seu_topico.md`
2. Estruturar conforme template acima
3. Registrar qual agente a usa
4. Testar com execução real
5. Versionar com Git

## Histórico

- 2026-06-10: consolidada a rodada Isomera `2.5.0` / `Trainable Mesh Workbench`, com KBs de VMamba, VMamba-Mesh, reprodutibilidade, interpretabilidade e VMamba-T/VMamba-Mesh-T.
- 2026-06-10: registrada a KB `vmamba_trainable_video_runbook.md` com resultados SPEC v2 e Full Lineage, campanhas CPU/MPS, hard-negative mining, manifest Codex/GPT-5, false-positive replay, métricas, ICs e roteiro de demonstração no Isomera.
- Pré-existentes: `context.md`, `plano_execucao_v2.md` e demais documentos de arquitetura em `.github/`.
