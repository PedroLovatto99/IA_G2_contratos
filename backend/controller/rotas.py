from fastapi import APIRouter, HTTPException, UploadFile

from service.contratoService import ContratoInvalido, FalhaNaAnalise, LimiteDeUsoAtingido, analisar_contrato


rota_contrato = APIRouter(tags=["contrato"])

EXTENSOES_ACEITAS = (".pdf", ".docx")
TAMANHO_MAXIMO_ARQUIVO = 10 * 1024 * 1024


@rota_contrato.get("/")
def main():
    return {"mensagem": "ContratosCheck no ar"}


@rota_contrato.post("/avaliar")
def avaliar_contrato(arquivo: UploadFile):
    if not (arquivo.filename or "").lower().endswith(EXTENSOES_ACEITAS):
        raise HTTPException(status_code=415, detail="Envie um arquivo PDF ou DOCX")

    if arquivo.size > TAMANHO_MAXIMO_ARQUIVO:
        raise HTTPException(status_code=413, detail="O arquivo deve ter no maximo 10 MB")

    try:
        return analisar_contrato(arquivo.filename, arquivo.file.read())
    except ContratoInvalido as erro:
        raise HTTPException(status_code=422, detail=str(erro))
    except LimiteDeUsoAtingido as erro:
        raise HTTPException(status_code=429, detail=str(erro))
    except FalhaNaAnalise as erro:
        raise HTTPException(status_code=503, detail=str(erro))
