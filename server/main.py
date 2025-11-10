from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import random
import string
from typing import List, Dict, Set, Optional
import json

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gerenciador de conexões WebSocket
class ConnectionManager:
    def __init__(self):
        # key: room_code, value: set of WebSocket connections
        self.room_connections: Dict[str, Set[WebSocket]] = {}
        # key: WebSocket, value: room_code
        self.connection_rooms: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, room_code: str):
        if room_code not in self.room_connections:
            self.room_connections[room_code] = set()
        self.room_connections[room_code].add(websocket)
        self.connection_rooms[websocket] = room_code
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.connection_rooms:
            room_code = self.connection_rooms[websocket]
            self.room_connections[room_code].remove(websocket)
            if not self.room_connections[room_code]:
                del self.room_connections[room_code]
            del self.connection_rooms[websocket]
    
    async def broadcast_to_room(self, room_code: str, message: dict):
        if room_code in self.room_connections:
            for connection in self.room_connections[room_code]:
                await connection.send_json(message)

manager = ConnectionManager()

# Estruturas para o modo multiplayer
class Player(BaseModel):
    name: str
    score: int = 0
    attempts: int = 0
    is_owner: bool = False
    completed: bool = False
    current_guess: Optional[str] = None

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

@app.websocket("/ws/game")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket principal para o jogo"""
    try:
        await websocket.accept()
        
        async for raw_data in websocket:
            try:
                data = json.loads(raw_data)
                message_type = data.get("type")
                player_name = data.get("playerName")
                
                if message_type == "CREATE_ROOM":
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
                    
                    await manager.connect(websocket, code)
                    await websocket.send_json({
                        "type": "ROOM_CREATED",
                        "roomCode": code
                    })
                
                elif message_type == "JOIN_ROOM":
                    code = data.get("roomCode")
                    if code not in ROOMS:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Sala não encontrada"
                        })
                        continue
                    
                    room = ROOMS[code]
                    if room.started:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Jogo já começou"
                        })
                        continue
                        
                    if player_name in room.players:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Nome já está em uso"
                        })
                        continue
                    
                    room.players[player_name] = Player(name=player_name)
                    await manager.connect(websocket, code)
                    
                    # Broadcast para todos na sala
                    await manager.broadcast_to_room(code, {
                        "type": "PLAYER_JOINED",
                        "players": list(room.players.keys())
                    })
                
                elif message_type == "START_GAME":
                    code = data.get("roomCode")
                    if code not in ROOMS:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Sala não encontrada"
                        })
                        continue
                    
                    room = ROOMS[code]
                    if not room.players[player_name].is_owner:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Apenas o dono pode iniciar o jogo"
                        })
                        continue
                    
                    room.started = True
                    await manager.broadcast_to_room(code, {
                        "type": "GAME_STARTED",
                        "word": room.word
                    })
                
                elif message_type == "GUESS":
                    code = data.get("roomCode")
                    guess = data.get("guess").upper()
                    
                    if code not in ROOMS:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Sala não encontrada"
                        })
                        continue
                    
                    room = ROOMS[code]
                    if not room.started:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Jogo ainda não começou"
                        })
                        continue
                    
                    player = room.players[player_name]
                    target_word = room.word
                    result = []
                    
                    # Verificar cada letra da tentativa
                    for i, letter in enumerate(guess):
                        if letter == target_word[i]:
                            result.append("green")
                        elif letter in target_word:
                            result.append("yellow")
                        else:
                            result.append("gray")
                    
                    player.attempts += 1
                    is_correct = guess == target_word
                    
                    if is_correct:
                        player.completed = True
                        player.score = max(100 - (player.attempts - 1) * 10, 10)
                        
                        # Verificar se todos terminaram
                        if all(p.completed for p in room.players.values()):
                            room.finished = True
                    
                    # Preparar leaderboard se o jogo terminou
                    leaderboard = None
                    if room.finished or player.attempts >= 6:
                        leaderboard = [
                            {
                                "playerName": p.name,
                                "attempts": p.attempts,
                                "score": p.score
                            }
                            for p in room.players.values()
                        ]
                        leaderboard.sort(key=lambda x: (-x["score"], x["attempts"]))
                    
                    await manager.broadcast_to_room(code, {
                        "type": "GUESS_RESULT",
                        "result": result,
                        "isCorrect": is_correct,
                        "playerName": player_name,
                        "leaderboard": leaderboard
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "ERROR",
                    "message": "Formato de mensagem inválido"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "ERROR",
                    "message": str(e)
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def start_game(code: str, player_name: str, websocket: WebSocket):
    """Função auxiliar para iniciar o jogo em uma sala"""
    if code not in ROOMS:
        await websocket.send_json({
            "type": "ERROR",
            "message": "Sala não encontrada"
        })
        return False
    
    room = ROOMS[code]
    if not room.players[player_name].is_owner:
        await websocket.send_json({
            "type": "ERROR",
            "message": "Apenas o dono pode iniciar o jogo"
        })
        return False
    
    room.started = True
    await manager.broadcast_to_room(code, {
        "type": "GAME_STARTED",
        "word": room.word
    })
    return True

# Mantenha apenas os endpoints utilitários HTTP que não dependem do estado do jogo
@app.get("/validate/{word}")
async def validate_word(word: str):
    """Verifica se uma palavra é válida para o jogo"""
    word = word.upper()
    if len(word) != 5:
        raise HTTPException(status_code=400, detail="A palavra deve ter 5 letras")
    return {"valid": word in VALID_WORDS}

@app.get("/words")
async def get_words():
    """Retorna a lista de palavras possíveis"""
    return {"words": WORDS}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)