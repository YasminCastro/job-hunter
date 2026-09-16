# job-hunter

API em Python com Flask.

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

### Executando o container

```bash
docker run -d -p 5000:5000 --name job-hunter job-hunter
```

O servidor sobe em `http://127.0.0.1:5000`.

### Parando o container

```bash
docker stop job-hunter
docker rm job-hunter
```

### Usando Docker Compose

```bash
docker compose up -d
```

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
