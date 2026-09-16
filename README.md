# job-hunter

API em Python (Flask) que busca vagas no LinkedIn via [python-jobspy](https://github.com/speedyapply/JobSpy), filtra por título e usa um modelo local no Ollama para analisar a aderência de cada vaga ao perfil do candidato. Um workflow do n8n (`n8n-workflows/`) orquestra as chamadas para essa API.

## Endpoints

### `GET /`

Health check.

```json
{ "message": "service online" }
```

### `POST /jobspy`

Busca vagas novas no LinkedIn (ainda não vistas em execuções anteriores), aplica um filtro por título e salva o resultado em `output/vagas_<timestamp>.csv`.

Body:

```json
{
  "site_name": ["linkedin"],
  "search_term": "desenvolvedor python",
  "location": "Brasil",
  "focus_titles": ["desenvolvedor", "developer"],
  "discard_terms": ["estágio", "júnior"]
}
```

- `site_name`, `search_term`, `location` e `focus_titles` são obrigatórios (`focus_titles` não pode ser vazio, senão toda vaga é descartada pelo filtro).
- `discard_terms` é opcional; se omitido, usa os padrões de `services/filters.py`.
- Retorna `429` se chamado antes do cooldown de 60s entre execuções (proteção contra bloqueio do LinkedIn por excesso de requisições).

Resposta:

```json
{ "jobs": [...], "total": 10 }
```

### `POST /analyze`

Envia uma vaga e o perfil do candidato para o modelo rodando no Ollama e retorna um score de aderência.

Body:

```json
{
  "job": { "id": "...", "title": "...", "company": "...", "job_url": "..." },
  "candidate_profile": "texto livre descrevendo experiência, skills, etc."
}
```

Resposta:

```json
{
  "jobId": "...",
  "title": "...",
  "company": "...",
  "location": "...",
  "url": "...",
  "score": 8,
  "pontos_fortes": ["..."],
  "requisitos_faltantes": ["..."],
  "resumo_vaga": "..."
}
```

Variáveis de ambiente usadas: `OLLAMA_URL` (padrão `http://localhost:11434`), `OLLAMA_MODEL` (padrão `llama3.1:8b`), `OLLAMA_TIMEOUT` (padrão `120`s).

## ⚠️ Sobre rodar o scraping

O scraping do LinkedIn (`/jobspy`) é sensível a bloqueios quando executado repetidamente a partir do mesmo IP, especialmente IPs de datacenter/CI. Por isso, **rode a API localmente** — não execute `app.py` a partir de ambientes automatizados/CI. Se necessário, use a variável `PROXIES` para rotacionar IP (veja `services/scrape_service.py`).

## Pré-requisitos

- Python 3.10+ instalado

## Instalação

1. Clone o repositório e entre na pasta do projeto:

   ```bash
   cd job-hunter
   ```

2. Crie o ambiente virtual:

   ```bash
   python -m venv venv
   ```

3. Ative o ambiente virtual:
   - Windows (PowerShell):

     ```powershell
     venv\Scripts\Activate.ps1
     ```

   - Windows (cmd):

     ```cmd
     venv\Scripts\activate.bat
     ```

   - Linux/macOS:

     ```bash
     source venv/bin/activate
     ```

4. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

## Executando o projeto

```bash
python app.py
```

O servidor sobe em `http://127.0.0.1:5000`.

## Testando

```bash
curl http://127.0.0.1:5000/
```

Resposta esperada:

```json
{
  "message": "service online"
}
```

## Rodando com Docker

### Pré-requisitos

- Docker instalado

### Build da imagem

```bash
docker build -t job-hunter .
```

### Usando Docker Compose (recomendado)

O `docker-compose.yml` sobe a stack completa: a API, o Ollama (com pull automático do modelo `llama3.1:8b`) e o n8n.

```bash
docker compose up -d
```

- API: `http://127.0.0.1:5000`
- n8n: `http://127.0.0.1:5678`
- Ollama: `http://127.0.0.1:11434`

Para parar:

```bash
docker compose down
```

### Workflows do n8n

Os workflows são versionados em `n8n-workflows/` (um arquivo `.json` por workflow) e são importados automaticamente toda vez que o container do n8n sobe.

Para salvar um workflow novo/alterado nesse diretório (com o container rodando):

```bash
docker exec job-hunter-n8n n8n export:workflow --all --separate --output=/workflows
```

Depois é só commitar os `.json` gerados em `n8n-workflows/`. Em outra máquina, basta rodar `docker compose up -d` que o n8n já sobe com os workflows importados.

## **Como criar o Bot no Telegram e pegar o Chat ID**

Para o Telegram, precisamos de duas informações: criar o robô para pegar o "Token" e descobrir o seu número de identificação "Chat ID" para o robô saber para quem enviar a vaga.

## **Criando o Robô (Token)**

1. Abra o aplicativo do Telegram e, na barra de pesquisa, digite **@BotFather** (escolha o que tem o selo azul de verificado).
2. Abra a conversa e clique em **Iniciar**.
3. Envie a mensagem `/newbot` para começar a criar seu robô.
4. Envie um nome para o robô (exemplo: "Meu Robô de Empregos").
5. Envie um "username" (nome de usuário) único, que **obrigatoriamente** precisa terminar com a palavra "bot" (exemplo: `vagas_rafa_bot`).
6. Quando o nome for aceito, o BotFather enviará uma mensagem de sucesso. Copie o código enorme que vem logo abaixo da frase "Use this token to access the HTTP API:". Esse é o seu **Token**.

## **Pegando o seu Chat ID**

1. O robô só pode te enviar mensagens se você falar com ele primeiro. Pesquise no Telegram pelo username do robô que você acabou de criar (exemplo: `@vagas_rafa_bot`), abra a conversa e clique em **Iniciar**.
2. Volte na pesquisa do Telegram e digite **@userinfobot**.
3. Abra a conversa com esse bot e clique em **Iniciar**.
4. Ele vai responder instantaneamente com algumas informações. Copie o número que aparece na linha **Id:** (esse é o seu **Chat ID**).
5. Cole esse número no campo "Chat ID" na configuração final da mensagem no n8n.
