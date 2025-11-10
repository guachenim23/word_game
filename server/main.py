from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lista de palavras (vamos expandir isso)
WORDS = [
    'TERMO', 'PAPEL', 'FESTA', 'PRAIA', 'LIVRO', 'SONHO', 'MUNDO', 'FELIZ', 'CAMPO', 'TERRA',
    'MAÇÃ', 'FORÇA', 'GRAÇA', 'PREÇO', 'PRAÇA', 'HOUVE', 'PARIS', 'PEDRO', 'MARIA', 'PAULO',
    'JULHO', 'NATAL', 'PIZZA', 'GARÇA', 'MASSA', 'POÇÃO', 'SORTE', 'CORES', 'PORTO', 'PATOS',
    'LUCAS', 'BRUNO', 'CLARA', 'CHUVA', 'FOLHA', 'MANGA', 'PALHA', 'PEIXE', 'VINHO', 'SENHA',
    'CASAL', 'PILHA', 'BOLSA', 'TELHA', 'MALHA', 'CALÇA', 'PLACA', 'CLUBE', 'CORPO', 'FILHO',
    'PORTA', 'CARTA', 'GENTE', 'MOEDA', 'PEDRA', 'PLANO', 'LINHA', 'FILME', 'MAGIA', 'PASTA',
    'POLVO', 'PONTE', 'ROUPA', 'SOFIA', 'VIDRO', 'LIMÃO', 'LARVA', 'FLOR', 'MANTO', 'NOME'
]

VALID_WORDS = set(WORDS)

@app.get("/words")
async def get_words():
    """Retorna a lista de palavras possíveis para serem a palavra do dia"""
    return {"words": WORDS}

@app.get("/validate/{word}")
async def validate_word(word: str):
    """Verifica se uma palavra é válida para o jogo"""
    word = word.upper()
    if len(word) != 5:
        raise HTTPException(status_code=400, detail="A palavra deve ter 5 letras")
    return {"valid": word in VALID_WORDS}

@app.get("/random")
async def get_random_word():
    """Retorna uma palavra aleatória da lista"""
    from random import choice
    return {"word": choice(WORDS)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)