# Isomera Complete Manual

Pacote de manual visual e estudo teorico do Isomera.

Arquivos principais:

- `isomera_manual_presentation.html`: apresentacao HTML simples, com storytelling, teoria e rotas principais.
- `isomera_complete_manual.tex`: fonte do manual/livro em LaTeX.
- `isomera_complete_manual.pdf`: manual compilado com teoria, pratica, screenshots e rotas do aplicativo.
- `screenshots/`: capturas reais do Isomera e figuras finais do estudo VMamba-Mesh.
- `capture_isomera_screenshots.py`: script usado para capturar telas do app local em `http://localhost:8514`.

Fluxo de reproducao:

```bash
python3 -m streamlit run main/ui/app.py --server.port 8514 --server.address localhost --server.headless true
python3 main/docs/manuals/isomera_complete_manual/capture_isomera_screenshots.py
cd main/docs/manuals/isomera_complete_manual
tectonic isomera_complete_manual.tex
```

O manual combina:

- teoria de Data Mesh, grafos de linhagem e duplicidade;
- explicacao de SOR/SOT/SPEC, matriz de adjacencia e tensor C0-C5;
- navegacao pratica em Home, Benchmark & Examples, Scenario Studio, Study Lab, Model Lab, Research Reports, Admin, Logs, Help e About;
- resultados e interpretabilidade do estudo VMamba-Mesh;
- checklist de demonstracao e aplicacao em ambiente corporativo.
