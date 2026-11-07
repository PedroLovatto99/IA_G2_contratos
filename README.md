# ContratosCheck

## Sobre o Projeto
O **ContratosCheck** é um sistema web em que o usuário envia um contrato em PDF ou DOCX e recebe os pontos de atenção encontrados no documento, com a gravidade, a explicação do risco e o fundamento legal de cada um.

A análise usa **RAG** (geração aumentada por recuperação): o sistema busca, em uma base vetorial, os artigos de lei mais próximos do texto do contrato e envia esses artigos ao **Gemini**, que só pode fundamentar a resposta nas normas fornecidas. A base é montada a partir do repositório [ctresb/leis](https://github.com/ctresb/leis) e contém a Constituição Federal, o Código Civil, o Código de Defesa do Consumidor, a Lei do Inquilinato, a CLT, a LGPD, a Lei de Arbitragem e o Código de Processo Civil.

O resultado é um apoio para a leitura do contrato e não substitui a orientação de um advogado.

---

## Funcionalidades
- Envio de contratos em PDF ou DOCX pela interface web
- Busca automática dos artigos de lei relacionados ao contrato
- Lista de pontos de atenção com trecho da cláusula, explicação, gravidade e fundamento legal
- Ingestão automática das normas na primeira inicialização, ignorada quando a base já existe
- Limites de uso: arquivos de até 10 MB, PDFs de até 100 páginas, textos de até 200 mil caracteres e 50 análises por dia

---

## Tecnologias Utilizadas
* **Front-end:** React, TypeScript, Vite, Tailwind CSS
* **Back-end:** Python, FastAPI, Uvicorn, pypdf, python-docx
* **Banco de dados:** ChromaDB (base vetorial)
* **IA:** LangChain, Gemini API (`gemini-3.5-flash-lite`), Sentence Transformers (`intfloat/multilingual-e5-base`)
* **Conteinerização:** Docker, Docker Compose

---

## Instalação e Configuração

### 1. Pré-requisitos
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/), para rodar com Docker
- [Python 3.12 ou superior](https://www.python.org/) e [Node.js 24](https://nodejs.org/), para rodar sem Docker
- Uma chave da Gemini API, criada no [Google AI Studio](https://aistudio.google.com/)

### 2. Clonar o repositório
```bash
git clone https://github.com/PedroLovatto99/IA_G2_contratos.git
cd IA_G2_contratos
```

### 3. Configurar variáveis de ambiente (.env)
Copie o arquivo `.env.example` para `.env`, na raiz do projeto, e preencha a chave:

```env
# Chave da Gemini API, obrigatória para o back-end iniciar
GEMINI_API_KEY=sua_chave_aqui
```

**IMPORTANTE:** o texto dos contratos enviados é processado pela Gemini API. Não use contratos com dados pessoais reais em testes.

### 4. Rodar com Docker (Recomendado)
```bash
docker compose up --build
```

**IMPORTANTE:** a primeira inicialização é demorada, pois baixa o modelo de embedding (cerca de 1 GB) e vetoriza as normas na CPU, o que pode levar dezenas de minutos. A API só responde quando o log mostrar `Uvicorn running`. Nas próximas vezes, a base e o modelo são reaproveitados dos volumes do Docker.

O comando `docker compose down -v` apaga esses volumes e faz a ingestão rodar de novo.

### 5. Rodar sem Docker

**Back-end**, a partir da raiz do projeto:

```bash
cd backend
python -m venv env
```

Ative o ambiente virtual:

```bash
# Windows
env\Scripts\activate

# Linux e macOS
source env/bin/activate
```

Instale as dependências, gere a base de normas e inicie a API:

```bash
pip install -r requirements.txt
python -m rag.ingestao_dados
uvicorn app:app --port 8000
```

**Front-end**, em outro terminal, a partir da raiz do projeto:

```bash
cd frontend
npm install
npm run dev
```

**IMPORTANTE:** a base gerada sem Docker fica em `backend/rag/chromadb/` e é separada da base do volume do Docker, por isso a ingestão precisa ser feita uma vez em cada ambiente.

---

## Como Acessar
```bash
http://localhost:5173
```

Selecione um contrato em PDF ou DOCX e clique em **Analisar contrato**.

A documentação interativa da API fica em:

```bash
http://localhost:8000/docs
```

---

## Estrutura de Diretórios
```text
.
├── docker-compose.yml             # Orquestração: backend e frontend, com volumes da base e do modelo
├── .dockerignore                  # Arquivos fora da imagem do backend
├── .env.example                   # Variáveis de ambiente exigidas (copiar para .env)
├── backend/                       # Python + FastAPI
│   ├── app.py                     # Criação da aplicação e configuração de CORS
│   ├── Dockerfile                 # Imagem do backend com PyTorch para CPU
│   ├── requirements.txt           # Dependências Python
│   ├── controller/
│   │   └── rotas.py               # Endpoints da API e validação do upload
│   ├── service/
│   │   └── contratoService.py     # Leitura do arquivo, busca das normas e regras de uso
│   ├── rag/
│   │   └── ingestao_dados.py      # Download, divisão por artigo e vetorização das normas
│   └── IA/
│       └── agente_config.py       # Modelo Gemini, prompt e formato da resposta
└── frontend/                      # React + TypeScript + Vite
    ├── Dockerfile                 # Imagem do servidor de desenvolvimento do Vite
    ├── package.json               # Dependências e scripts
    ├── vite.config.ts             # Configuração do Vite e do Tailwind CSS
    └── src/
        ├── App.tsx                # Tela de envio do contrato e de resultado
        ├── index.css              # Importação do Tailwind CSS
        └── main.tsx               # Ponto de entrada do React
```
