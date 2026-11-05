import logging
import textwrap
import threading
from datetime import date
from io import BytesIO

import chromadb
from docx import Document
from google.genai.errors import APIError
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from IA.agente_config import agente
from rag.ingestao_dados import COLECAO, MODELO, PASTA_CHROMA


TAMANHO_MAXIMO_TEXTO = 200_000
MAXIMO_PAGINAS = 100
MAXIMO_ANALISES_POR_DIA = 50
TAMANHO_BLOCO = 1000
NORMAS_POR_BLOCO = 3
MAXIMO_NORMAS = 30

logger = logging.getLogger(__name__)
modelo = SentenceTransformer(MODELO)
cliente = chromadb.PersistentClient(path=str(PASTA_CHROMA))

# shortcut: contagem em memoria e global, zera ao reiniciar; com varios workers ou login, mover para banco
uso_diario = {"dia": None, "total": 0}
trava_uso = threading.Lock()


class ContratoInvalido(Exception):
    pass


class FalhaNaAnalise(Exception):
    pass


class LimiteDeUsoAtingido(Exception):
    pass


def extrair_texto_pdf(conteudo):
    paginas = PdfReader(BytesIO(conteudo)).pages
    if len(paginas) > MAXIMO_PAGINAS:
        raise ContratoInvalido(f"O PDF deve ter no maximo {MAXIMO_PAGINAS} paginas")
    return "\n".join(pagina.extract_text() or "" for pagina in paginas)


def extrair_texto_docx(conteudo):
    documento = Document(BytesIO(conteudo))
    paragrafos = [p.text for p in documento.paragraphs]
    celulas = [c.text for tabela in documento.tables for linha in tabela.rows for c in linha.cells]
    return "\n".join(paragrafos + celulas)


def extrair_texto(nome_arquivo, conteudo):
    extrator = extrair_texto_pdf if nome_arquivo.lower().endswith(".pdf") else extrair_texto_docx

    try:
        texto = extrator(conteudo).strip()
    except ContratoInvalido:
        raise
    except Exception as erro:  # as bibliotecas lancam tipos variados com arquivos corrompidos
        raise ContratoInvalido("Nao foi possivel ler o arquivo") from erro

    if not texto:
        raise ContratoInvalido("O arquivo nao tem texto legivel. PDFs escaneados nao sao aceitos")
    if len(texto) > TAMANHO_MAXIMO_TEXTO:
        raise ContratoInvalido("O contrato e longo demais para ser analisado")

    return texto


def buscar_normas(texto):
    blocos = textwrap.wrap(texto, TAMANHO_BLOCO)
    # o e5 exige o prefixo "query: " nas buscas
    vetores = modelo.encode([f"query: {bloco}" for bloco in blocos], normalize_embeddings=True)
    resultado = cliente.get_collection(COLECAO).query(query_embeddings=vetores.tolist(), n_results=NORMAS_POR_BLOCO)

    # o mesmo artigo pode voltar para varios blocos; fica a menor distancia
    normas = {}
    for ids, documentos, metadados, distancias in zip(
        resultado["ids"], resultado["documents"], resultado["metadatas"], resultado["distances"]
    ):
        for id_norma, documento, metadado, distancia in zip(ids, documentos, metadados, distancias):
            if id_norma not in normas or distancia < normas[id_norma][0]:
                normas[id_norma] = (distancia, documento, metadado)

    selecionadas = sorted(normas.values(), key=lambda norma: norma[0])[:MAXIMO_NORMAS]
    return "\n\n".join(f"[{m['norma']} - {m['estrutura']}]\n{d}" for _, d, m in selecionadas)


def registrar_uso():
    with trava_uso:
        hoje = date.today()
        if uso_diario["dia"] != hoje:
            uso_diario.update(dia=hoje, total=0)
        if uso_diario["total"] >= MAXIMO_ANALISES_POR_DIA:
            raise LimiteDeUsoAtingido("Limite diario de analises atingido. Tente novamente amanha")
        uso_diario["total"] += 1


def analisar_contrato(nome_arquivo, conteudo):
    texto = extrair_texto(nome_arquivo, conteudo)
    registrar_uso()

    try:
        analise = agente.invoke({"normas": buscar_normas(texto), "contrato": texto})
    except (ChatGoogleGenerativeAIError, APIError) as erro:
        logger.exception("Falha na chamada ao Gemini")
        raise FalhaNaAnalise("Nao foi possivel analisar o contrato agora. Tente novamente mais tarde") from erro

    if analise is None:
        raise FalhaNaAnalise("A analise veio em formato invalido. Tente novamente")

    return analise
