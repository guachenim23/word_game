const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(cors());
app.use(express.static(path.join(__dirname, '../client')));

const rooms = new Map();
const words = ['TERMO', 'PAPEL', 'FESTA', 'PRAIA', 'LIVRO']; // Add more words as needed
const leaderboard = new Map();

function generateRoomCode() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let code = '';
    for (let i = 0; i < 5; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return code;
}

wss.on('connection', (ws) => {
    ws.on('message', (message) => {
        const data = JSON.parse(message);
        
        switch (data.type) {
            case 'CREATE_ROOM':
                const roomCode = generateRoomCode();
                const word = words[Math.floor(Math.random() * words.length)];
                rooms.set(roomCode, {
                    word,
                    players: new Map([[data.playerName, ws]]),
                    startTime: Date.now()
                });
                ws.send(JSON.stringify({ type: 'ROOM_CREATED', roomCode }));
                break;

            case 'JOIN_ROOM':
                const room = rooms.get(data.roomCode);
                if (room) {
                    room.players.set(data.playerName, ws);
                    ws.send(JSON.stringify({ type: 'JOINED_ROOM', roomCode: data.roomCode }));
                    // Notify other players
                    room.players.forEach((playerWs, playerName) => {
                        if (playerWs !== ws) {
                            playerWs.send(JSON.stringify({
                                type: 'PLAYER_JOINED',
                                playerName: data.playerName
                            }));
                        }
                    });
                } else {
                    ws.send(JSON.stringify({ type: 'ERROR', message: 'Room not found' }));
                }
                break;

            case 'GUESS':
                const gameRoom = rooms.get(data.roomCode);
                if (gameRoom) {
                    const isCorrect = data.guess === gameRoom.word;
                    const result = data.guess.split('').map((letter, index) => {
                        if (letter === gameRoom.word[index]) return 'green';
                        if (gameRoom.word.includes(letter)) return 'yellow';
                        return 'gray';
                    });

                    if (isCorrect) {
                        const endTime = Date.now();
                        const timeElapsed = (endTime - gameRoom.startTime) / 1000;
                        const score = {
                            playerName: data.playerName,
                            attempts: data.attemptNumber,
                            time: timeElapsed
                        };
                        
                        if (!leaderboard.has(data.roomCode)) {
                            leaderboard.set(data.roomCode, []);
                        }
                        leaderboard.get(data.roomCode).push(score);
                        leaderboard.get(data.roomCode).sort((a, b) => {
                            if (a.attempts !== b.attempts) return a.attempts - b.attempts;
                            return a.time - b.time;
                        });
                    }

                    gameRoom.players.forEach((playerWs) => {
                        playerWs.send(JSON.stringify({
                            type: 'GUESS_RESULT',
                            playerName: data.playerName,
                            guess: data.guess,
                            result,
                            isCorrect,
                            leaderboard: isCorrect ? leaderboard.get(data.roomCode) : null
                        }));
                    });
                }
                break;
        }
    });

    ws.on('close', () => {
        // Handle player disconnection
        rooms.forEach((room, roomCode) => {
            room.players.forEach((playerWs, playerName) => {
                if (playerWs === ws) {
                    room.players.delete(playerName);
                    if (room.players.size === 0) {
                        rooms.delete(roomCode);
                        leaderboard.delete(roomCode);
                    }
                }
            });
        });
    });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});