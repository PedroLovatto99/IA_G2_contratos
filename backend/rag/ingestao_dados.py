import re
import textwrap
import urllib.request
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# commit fixo: o texto vetorizado nao muda quando o repositorio for atualizado
COMMIT = "c9f21b4ab11aa0d7ca6fe861d75028e94219c2d6"
URL_BASE = f"https://raw.githubusercontent.com/ctresb/leis/{COMMIT}/"

NORMAS = {
    "Constituição Federal de 1988": "constituicao.md",
    "Código Civil (Lei nº 10.406/2002)": "federal/leis-ordinarias/2002/lei-10406-2002-01-10.md",
    "Código de Defesa do Consumidor (Lei nº 8.078/1990)": "federal/leis-ordinarias/1990/lei-8078-1990-09-11.md",
    "Lei do Inquilinato (Lei nº 8.245/1991)": "federal/leis-ordinarias/1991/lei-8245-1991-10-18.md",
    "CLT (Decreto-Lei nº 5.452/1943)": "federal/decretos-lei/1943/del-5452-1943-05-01.md",
    "LGPD (Lei nº 13.709/2018)": "federal/leis-ordinarias/2018/lei-13709-2018-08-14.md",
    "Lei de Arbitragem (Lei nº 9.307/1996)": "federal/leis-ordinarias/1996/lei-9307-1996-09-23.md",
    "Código de Processo Civil (Lei nº 13.105/2015)": "federal/leis-ordinarias/2015/lei-13105-2015-03-16.md",
}

MODELO = "intfloat/multilingual-e5-base"
PASTA_CHROMA = Path(__file__).parent / "chromadb"
COLECAO = "normas"
COLECAO_TEMP = "normas_em_ingestao"
# o e5 corta o texto em 512 tokens sem avisar; 1100 caracteres ficam abaixo disso
LIMITE_CARACTERES = 1100
LOTE_CHROMA = 1000

ARTIGO = re.compile(r"Art\. ?(\d[\d.]*[º°]?(?:-[A-Z]+)?)")
TITULO = re.compile(r"(#+) (.+)")
ASSINATURA = re.compile(r"(Brasília|Rio de Janeiro), \d")
SO_REVOGADO = re.compile(r"Art\. \S+[\s.–-]*(e parágrafo único\.\s*)?\(?(revogad|vetad)", re.IGNORECASE)


def baixar(caminho):
    with urllib.request.urlopen(URL_BASE + caminho, timeout=60) as resposta:
        return resposta.read().decode("utf-8")


def separar_artigos(texto):
    # tudo antes do primeiro artigo (cabecalho YAML, ementa, preambulo) fica de fora
    artigos, niveis, atual = [], {}, None

    for linha in texto.splitlines():
        linha = re.sub(r"[*\\]", "", linha).strip()
        titulo = TITULO.match(linha)
        artigo = ARTIGO.match(linha)

        if titulo:
            nivel = len(titulo.group(1))
            niveis = {n: t for n, t in niveis.items() if n < nivel}
            niveis[nivel] = titulo.group(2)
            atual = None
        elif artigo:
            # a estrutura diferencia numeros repetidos: CF x ADCT, decreto x CLT
            atual = {
                "artigo": "Art. " + artigo.group(1).rstrip("."),
                "estrutura": " > ".join(niveis[n] for n in sorted(niveis)),
                "paragrafos": [linha],
            }
            artigos.append(atual)
        elif ASSINATURA.match(linha):
            atual = None
        elif atual and linha:
            atual["paragrafos"].append(linha)

    return [a for a in artigos if not (len(a["paragrafos"]) == 1 and SO_REVOGADO.match(a["paragrafos"][0]))]


def dividir_artigo(artigo):
    partes, atual = [], ""

    for paragrafo in artigo["paragrafos"]:
        for pedaco in textwrap.wrap(paragrafo, LIMITE_CARACTERES):
            if atual and len(atual) + len(pedaco) > LIMITE_CARACTERES:
                partes.append(atual.strip())
                atual = f"{artigo['artigo']} (continuação)\n"
            atual += pedaco + "\n"

    partes.append(atual.strip())
    return partes


def main():
    cliente = chromadb.PersistentClient(path=str(PASTA_CHROMA))
    colecoes = [c.name for c in cliente.list_collections()]

    if COLECAO in colecoes:
        print("Base de normas ja existe, ingestao ignorada")
        return

    # sobra de uma ingestao interrompida
    if COLECAO_TEMP in colecoes:
        cliente.delete_collection(COLECAO_TEMP)

    ids, documentos, metadados = [], [], []

    for norma, caminho in NORMAS.items():
        print(f"Baixando {norma}")
        for artigo in separar_artigos(baixar(caminho)):
            for parte in dividir_artigo(artigo):
                ids.append(f"{Path(caminho).stem}-{len(ids)}")
                documentos.append(parte)
                metadados.append({
                    "norma": norma,
                    "artigo": artigo["artigo"],
                    "estrutura": artigo["estrutura"],
                    "fonte": URL_BASE + caminho,
                })

    print(f"Vetorizando {len(ids)} trechos")
    modelo = SentenceTransformer(MODELO)
    # o e5 exige o prefixo "passage: " aqui e "query: " nas buscas
    textos = [f"passage: {m['norma']} - {m['estrutura']}\n{d}" for d, m in zip(documentos, metadados)]
    vetores = modelo.encode(textos, normalize_embeddings=True, show_progress_bar=True)

    colecao = cliente.create_collection(COLECAO_TEMP, configuration={"hnsw": {"space": "cosine"}})

    for i in range(0, len(ids), LOTE_CHROMA):
        fim = i + LOTE_CHROMA
        colecao.add(ids=ids[i:fim], documents=documentos[i:fim], metadatas=metadados[i:fim], embeddings=vetores[i:fim])

    # so recebe o nome final completa: uma ingestao interrompida nao conta como pronta
    colecao.modify(name=COLECAO)
    print(f"{colecao.count()} trechos salvos em {PASTA_CHROMA}")


if __name__ == "__main__":
    main()
