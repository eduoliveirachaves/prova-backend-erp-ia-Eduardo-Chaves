# Prova Backend ERP + IA

Implementei uma API FastAPI para produtos e estoque com PostgreSQL, Redis, autenticação JWT, processamento em background e um agente determinístico. A solução prática é um monólito modular; as decisões sobre microsserviços, concorrência, Go e evolução para LLM/MCP estão nas respostas teóricas.

## Pré-requisitos

- Docker com o plugin Docker Compose;
- porta `8000` disponível para a API. Caso ela já esteja ocupada, use `APP_PORT` conforme o exemplo abaixo.

Não é necessário instalar Python, PostgreSQL ou Redis no host.

## Subindo a aplicação

Crie o arquivo de ambiente a partir do exemplo e inicie todos os serviços:

```bash
cp .env.example .env
docker compose up --build --wait
```

O Compose inicia PostgreSQL, Redis, API e worker. O entrypoint da API executa as migrações do Alembic e cria o usuário de demonstração de forma idempotente antes de iniciar o Uvicorn.

Se a porta `8000` já estiver em uso:

```bash
APP_PORT=18000 docker compose up --build --wait
```

Nesse caso, substitua `8000` por `18000` nas URLs acessadas pelo host.

## Verificando o ambiente

```bash
curl --fail http://localhost:8000/health/live
curl --fail http://localhost:8000/health/ready
docker compose ps
```

A documentação interativa fica em <http://localhost:8000/docs>. Para experimentar a API sem depender de ferramentas adicionais, recomendo usar o Swagger:

1. clique em **Authorize**;
2. informe o `username` e o `password` definidos no `.env`;
3. confirme a autorização; o Swagger solicita o token automaticamente;
4. use as rotas de produtos, dashboard e agente.

Os valores iniciais de desenvolvimento estão em `.env.example`. A porta da API é vinculada apenas a `127.0.0.1`, e o `JWT_SECRET` de exemplo não deve ser reutilizado fora de um ambiente local.

## Fluxos para avaliação

### Produtos e estoque

As rotas em `/api/v1/products` oferecem criação, consulta, atualização e exclusão. A listagem aceita:

- `page` e `page_size`;
- `name`;
- `min_price` e `max_price`;
- `low_stock=true`.

Crie um produto com `stock_quantity` abaixo de `LOW_STOCK_THRESHOLD` para enfileirar um alerta. O worker revalida o estado no PostgreSQL e grava um registro idempotente em `stock_alerts`.

Para acompanhar o processamento:

```bash
docker compose logs --follow worker
```

### Concorrência e degradação parcial

O dashboard consulta três fontes simuladas concorrentemente:

```text
GET /api/v1/dashboard/{product_id}?scenario=success
GET /api/v1/dashboard/{product_id}?scenario=degraded
```

No cenário degradado, uma fonte expira, outra se recupera após retry e a resposta preserva os resultados disponíveis.

### Agente determinístico

Envie para `POST /api/v1/agent/query`:

```json
{
  "question": "Quais produtos estão com estoque abaixo de 10 unidades?"
}
```

A pergunta é convertida em uma chamada estruturada para a ferramenta permitida e então executada pela camada de serviço:

```json
{
  "tool_call": {
    "name": "find_low_stock",
    "arguments": {
      "max_quantity": 10
    }
  },
  "result": []
}
```

Não há chamada a LLM ou serviço externo nesse fluxo.

## Testes e qualidade

Com a aplicação em execução, rode todos os testes e verificações em um container próprio:

```bash
docker compose --profile test run --rm --build test
```

Esse comando executa:

- testes unitários;
- um fluxo de integração contra API, PostgreSQL, Redis e worker reais;
- Ruff;
- mypy.

As dependências de desenvolvimento ficam apenas no estágio de teste da imagem, não no runtime da aplicação.

## Parando os serviços

Para parar e preservar os dados locais:

```bash
docker compose down
```

Para remover também os volumes de PostgreSQL e Redis:

```bash
docker compose down -v
```

## Organização

```text
src/app/
├── api/routes       # contrato HTTP, status codes e dependências
├── core             # configuração, segurança, cache e infraestrutura da aplicação
├── db               # engine e sessões SQLAlchemy
├── models           # modelos persistidos
├── repositories     # consultas e operações de persistência
├── schemas          # contratos Pydantic
├── services         # regras e orquestração
├── seed.py          # criação idempotente do usuário de demonstração
└── worker.py        # job e configuração do ARQ
```

Escolhi essa separação porque ela mantém HTTP, regras e persistência em fronteiras reconhecíveis sem criar uma estrutura maior que o problema. O PostgreSQL é a fonte de verdade. O Redis é usado como cache-aside e backend da fila, mas não participa de decisões transacionais de estoque.

## Respostas da prova

- [Parte 1 — arquitetura e organização](partes/1.md)
- [Parte 2 — asyncio e concorrência](partes/2.md)
- [Parte 3 — API RESTful](partes/3.md)
- [Parte 4 — Docker e entrega](partes/4.md)
- [Parte 5 — agente, LLM e MCP](partes/5.md)
- [Parte 6 — Go e perfil](partes/6.md)
- [Parte 7 — portfólio](partes/7.md)

## Uso de IA

Usei IA como ferramenta de apoio para organizar os requisitos, explorar alternativas e criar e revisar código, testes e documentação. Eu analisei as sugestões, adaptei o que fazia sentido para o contexto da prova e revisei as decisões finais da implementação. A aplicação não depende de OpenAI, Anthropic, Gemini ou outro provedor externo.
