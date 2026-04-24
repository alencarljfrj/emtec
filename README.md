# emtec - estrutura de scraping (VS Code)

Projeto pronto para rodar uma raspagem **profunda** focada em:
1. Atas de Registro de Preços ainda vigentes (CIMPAR Zona da Mata).
2. Último aditivo/renovação relacionado ao **Grupo VR** e ao objeto de construção/manutenção de estradas vicinais rurais (prefeitura de Juiz de Fora).

## 1) Pré-requisitos

- Python 3.11+
- VS Code com extensão Python

## 2) Instalação rápida

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -U pip
pip install -e .
```

## 3) Configuração

Edite `config/sources.yaml` para ajustar:
- URLs iniciais (`seed_urls`)
- domínios permitidos (`domains_allowlist`)
- profundidade (`max_depth`)
- número máximo de páginas (`max_pages`)
- palavras-chave para ARP, vigência e Grupo VR

## 4) Execução

```bash
atas-scraper run --config config/sources.yaml
```

Saídas geradas em `output/`:
- `resultados_*.json`
- `resultados_*.csv`

## 5) Como o scraper classifica os achados

- `ata_vigente`: texto contém sinal de "ata de registro de preços" + termos de vigência.
- `aditivo_grupo_vr`: texto contém termos do pacote Grupo VR/renovação/estradas vicinais.

## 6) Dicas para aumentar cobertura

- Suba `max_depth` para 6+ em portais com paginação complexa.
- Adicione subdomínios e domínios auxiliares (portais de transparência/documentos).
- Amplie `keywords_grupo_vr` com variações de razão social e número de contrato.
- Faça nova varredura semanal para capturar renovações recém-publicadas.

## 7) Observação jurídica-operacional

Este projeto faz **coleta técnica de evidências públicas**. Recomenda-se validação humana final dos documentos oficiais (extrato + íntegra + data de vigência) antes de qualquer decisão.
