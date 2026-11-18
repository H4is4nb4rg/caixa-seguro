# Caixa Seguro

**MVP de controle e rastreabilidade do caixa para a Maria Bunita Moda**, pequena loja de moda feminina, plus size e acessórios.

Projeto acadêmico da disciplina **Projeto de Software** (Análise e Desenvolvimento de Sistemas, Cruzeiro do Sul), alinhado ao **ODS 8 — Trabalho Decente e Crescimento Econômico** (metas 8.2 e 8.3).

## O problema

Na loja, vendas, descontos, trocas, sangrias e pagamentos eram comunicados verbalmente ou pelo WhatsApp, sem registro estruturado. O acesso ao caixa era pouco restrito e, quando havia diferença no fechamento, não era possível saber quem movimentou o caixa, quando e por quê.

## A solução (MVP)

| Requisito | Descrição | Status |
|---|---|---|
| RF01 | Login com perfis (proprietária, caixa, vendedora) | ✅ |
| RF02 | Abertura do caixa com valor inicial e responsável | ✅ |
| RF03 | Registro de movimentação com responsável e horário definidos pelo servidor | ✅ |
| RF04 | Fechamento com valor esperado, valor contado, diferença e justificativa obrigatória | ✅ |
| RF05 | Cancelamento com motivo, sem exclusão do histórico | ✅ |
| RF06 | Painel completo da proprietária | Próximo incremento |
| RF07 | Registro offline com sincronização (a API já evita duplicidade pelo UUID) | Parcial |

## Arquitetura

Monolito em camadas, modelo cliente-servidor:

```
frontend/ (Angular, PWA)  →  backend/ (Python + FastAPI)  →  PostgreSQL
                               ├── routers/       rotas da API (entrada e validação)
                               ├── services.py    regras de negócio do caixa
                               ├── repositories.py acesso aos dados (SQLAlchemy)
                               └── models.py      entidades: usuario, caixa, movimentacao
```

## Segurança (resumo)

- Senhas armazenadas apenas como hash **Argon2id** (nunca em texto, MD5 ou SHA-1).
- Sessão com **JWT** em cookie HttpOnly/SameSite e revogação ao sair.
- Bloqueio após 5 tentativas de login incorretas em 15 minutos e mensagem de erro genérica.
- Autorização por perfil verificada **no servidor** em toda operação.
- Validação de entradas com Pydantic e consultas parametrizadas (SQLAlchemy).
- Cabeçalho Content-Security-Policy e erros sem detalhes técnicos.
- Segredos apenas em variáveis de ambiente (ver `.env.example`).

## Como executar

### Back-end

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env                              # ajuste os valores
SENHA_INICIAL=defina-uma-senha python -m scripts.seed
uvicorn app.main:app --reload                        # http://localhost:8000/docs
```

Sem `DATABASE_URL`, a API usa SQLite local (`caixa_seguro.db`) para desenvolvimento.

### Front-end

```bash
cd frontend
npm install
npx ng serve                                         # http://localhost:4200
```

## Testes e integração contínua

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

- **Testes unitários** (`tests/test_unidade_servicos.py`): cálculo do saldo esperado, hash de senhas e regras do caixa.
- **Testes de integração** (`tests/test_integracao_api.py`): fluxo completo pela API, autenticação, autorização, validações e controles OWASP.
- **CI** (`.github/workflows/ci.yml`): a cada push e Pull Request, executa os testes com cobertura mínima de 80%, o build do front-end e a auditoria de dependências.

## Convenções

- Commits semânticos (`feat`, `fix`, `test`, `docs`, `ci`, `chore`, `refactor`).
- Toda funcionalidade entra na `main` por **Pull Request**, com auto-revisão e CI aprovado.

## Dados

Todos os nomes e valores usados em testes e demonstrações são **fictícios**. O sistema não coleta dados de clientes.
