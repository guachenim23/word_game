from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import random
import string
from typing import List, Dict

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estruturas para o modo multiplayer
class Player(BaseModel):
    name: str
    score: int = 0
    attempts: int = 0
    is_owner: bool = False
    completed: bool = False

class Room(BaseModel):
    code: str
    word: str
    players: Dict[str, Player]
    started: bool = False
    finished: bool = False

# Armazenamento das salas
ROOMS: Dict[str, Room] = {}

# Lista de palavras (vamos expandir isso)
WORDS = [
    'TERMO', 'PAPEL', 'FESTA', 'PRAIA', 'LIVRO', 'SONHO', 'MUNDO', 'FELIZ', 'CAMPO', 'TERRA',
    'MAÇÃ', 'FORÇA', 'GRAÇA', 'PREÇO', 'PRAÇA', 'HOUVE', 'PARIS', 'PEDRO', 'MARIA', 'PAULO',
    'JULHO', 'NATAL', 'PIZZA', 'GARÇA', 'MASSA', 'POÇÃO', 'SORTE', 'CORES', 'PORTO', 'PATOS',
    'LUCAS', 'BRUNO', 'CLARA', 'CHUVA', 'FOLHA', 'MANGA', 'PALHA', 'PEIXE', 'VINHO', 'SENHA',
    'CASAL', 'PILHA', 'BOLSA', 'TELHA', 'MALHA', 'CALÇA', 'PLACA', 'CLUBE', 'CORPO', 'FILHO',
    'PORTA', 'CARTA', 'GENTE', 'MOEDA', 'PEDRA', 'PLANO', 'LINHA', 'FILME', 'MAGIA', 'PASTA',
    'POLVO', 'PONTE', 'ROUPA', 'SOFIA', 'VIDRO', 'LIMÃO', 'LARVA', 'FLORA', 'MANTO', 'NOME',
    # Novas palavras adicionadas:
    'HERÓI', 'NOITE', 'IRMÃO', 'DANÇA', 'FOGÃO', 'ÁTOMO', 'AREIA', 'POETA', 'FLORA', 'SUAVE',
    'VERDE', 'DOIDO', 'PEIXE', 'BEIJO', 'NUVEM', 'CAFÉ', 'ADVÉM', 'FOSSO', 'FONTE', 'BRIGA',
    'VELOZ', 'NOBRE', 'RITMO', 'IDADE', 'HIATO', 'ZEBRA', 'ÍNDIO', 'MOTOR', 'FAVOR', 'ETAPA'
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

# Endpoints para multiplayer
def generate_room_code():
    """Gera um código único para a sala"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in ROOMS:
            return code

@app.post("/room/create")
async def create_room(player_name: str):
    """Cria uma nova sala e retorna o código"""
    code = generate_room_code()
    word = random.choice(WORDS)
    
    room = Room(
        code=code,
        word=word,
        players={
            player_name: Player(name=player_name, is_owner=True)
        }
    )
    ROOMS[code] = room
    return {"code": code}

@app.post("/room/join/{code}")
async def join_room(code: str, player_name: str):
    """Permite um jogador entrar em uma sala existente"""
    if code not in ROOMS:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    room = ROOMS[code]
    if room.started:
        raise HTTPException(status_code=400, detail="Jogo já começou")
    if player_name in room.players:
        raise HTTPException(status_code=400, detail="Nome já está em uso")
    
    room.players[player_name] = Player(name=player_name)
    return {"code": code, "players": list(room.players.keys())}

@app.post("/room/start/{code}")
async def start_room(code: str, player_name: str):
    """Inicia o jogo em uma sala"""
    if code not in ROOMS:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    room = ROOMS[code]
    if not room.players[player_name].is_owner:
        raise HTTPException(status_code=403, detail="Apenas o dono pode iniciar o jogo")
    
    room.started = True
    return {"word": room.word}

@app.get("/room/{code}")
async def get_room_status(code: str):
    """Retorna o status atual da sala"""
    if code not in ROOMS:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    room = ROOMS[code]
    return {
        "started": room.started,
        "finished": room.finished,
        "players": [
            {
                "name": name,
                "score": player.score,
                "attempts": player.attempts,
                "completed": player.completed
            }
            for name, player in room.players.items()
        ]
    }

@app.post("/room/{code}/attempt")
async def submit_attempt(code: str, player_name: str, attempt: str):
    """Registra uma tentativa de um jogador"""
    if code not in ROOMS:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    room = ROOMS[code]
    if not room.started:
        raise HTTPException(status_code=400, detail="Jogo ainda não começou")
    
    player = room.players[player_name]
    player.attempts += 1
    
    if attempt == room.word:
        player.completed = True
        player.score = max(100 - (player.attempts - 1) * 10, 10)
        
        # Verificar se todos terminaram
        if all(p.completed for p in room.players.values()):
            room.finished = True
    
    return {
        "correct": attempt == room.word,
        "finished": room.finished,
        "score": player.score if player.completed else None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)