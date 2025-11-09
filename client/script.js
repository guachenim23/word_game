class WordGame {
    constructor() {
        this.currentAttempt = 0;
        this.currentPosition = 0;
        this.gameActive = false;
        this.startTime = null;
        this.ws = new WebSocket('ws://localhost:3000');
        this.playerName = '';
        this.roomCode = '';
        this.setupWebSocket();
        this.setupEventListeners();
        this.createGameGrid();
        this.createKeyboard();
    }

    setupWebSocket() {
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            switch (data.type) {
                case 'ROOM_CREATED':
                    this.roomCode = data.roomCode;
                    this.startGame();
                    break;
                case 'JOINED_ROOM':
                    this.roomCode = data.roomCode;
                    this.startGame();
                    break;
                case 'GUESS_RESULT':
                    this.handleGuessResult(data);
                    break;
                case 'ERROR':
                    alert(data.message);
                    break;
            }
        };
    }

    setupEventListeners() {
        document.getElementById('create-room').addEventListener('click', () => this.createRoom());
        document.getElementById('join-room-btn').addEventListener('click', () => {
            document.getElementById('join-room-form').classList.remove('hidden');
        });
        document.getElementById('join-room-submit').addEventListener('click', () => this.joinRoom());
        document.getElementById('play-again').addEventListener('click', () => this.resetGame());
        
        document.addEventListener('keydown', (e) => {
            if (!this.gameActive) return;
            
            if (e.key === 'Enter') {
                this.submitGuess();
            } else if (e.key === 'Backspace') {
                this.deleteLetter();
            } else if (/^[A-Za-z]$/.test(e.key)) {
                this.addLetter(e.key.toUpperCase());
            }
        });
    }

    createGameGrid() {
        const gameGrid = document.getElementById('game-grid');
        gameGrid.innerHTML = '';
        
        for (let i = 0; i < 6; i++) {
            const row = document.createElement('div');
            row.className = 'grid-row';
            
            for (let j = 0; j < 5; j++) {
                const cell = document.createElement('div');
                cell.className = 'grid-cell';
                cell.dataset.row = i;
                cell.dataset.col = j;
                row.appendChild(cell);
            }
            
            gameGrid.appendChild(row);
        }
    }

    createKeyboard() {
        const keyboard = document.getElementById('keyboard');
        const layout = [
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['ENTER', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '⌫']
        ];

        keyboard.innerHTML = '';
        layout.forEach(row => {
            const keyboardRow = document.createElement('div');
            keyboardRow.className = 'keyboard-row';
            
            row.forEach(key => {
                const button = document.createElement('button');
                button.className = 'key';
                button.textContent = key;
                button.addEventListener('click', () => {
                    if (key === 'ENTER') {
                        this.submitGuess();
                    } else if (key === '⌫') {
                        this.deleteLetter();
                    } else {
                        this.addLetter(key);
                    }
                });
                keyboardRow.appendChild(button);
            });
            
            keyboard.appendChild(keyboardRow);
        });
    }

    createRoom() {
        this.playerName = document.getElementById('player-name').value.trim();
        if (!this.playerName) {
            alert('Por favor, insira seu nome');
            return;
        }
        this.ws.send(JSON.stringify({
            type: 'CREATE_ROOM',
            playerName: this.playerName
        }));
    }

    joinRoom() {
        this.playerName = document.getElementById('player-name').value.trim();
        const roomCode = document.getElementById('room-code').value.trim();
        
        if (!this.playerName || !roomCode) {
            alert('Por favor, preencha todos os campos');
            return;
        }

        this.ws.send(JSON.stringify({
            type: 'JOIN_ROOM',
            playerName: this.playerName,
            roomCode: roomCode
        }));
    }

    startGame() {
        document.getElementById('initial-screen').classList.add('hidden');
        document.getElementById('game-screen').classList.remove('hidden');
        document.getElementById('room-code-display').textContent = this.roomCode;
        this.gameActive = true;
        this.startTime = Date.now();
        this.updateTimer();
    }

    updateTimer() {
        if (!this.gameActive) return;
        
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        document.getElementById('timer').textContent = 
            `Tempo: ${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        requestAnimationFrame(() => this.updateTimer());
    }

    addLetter(letter) {
        if (!this.gameActive || this.currentPosition >= 5) return;

        const cell = document.querySelector(
            `.grid-cell[data-row="${this.currentAttempt}"][data-col="${this.currentPosition}"]`
        );
        cell.textContent = letter;
        cell.classList.add('filled');
        this.currentPosition++;
    }

    deleteLetter() {
        if (!this.gameActive || this.currentPosition === 0) return;

        this.currentPosition--;
        const cell = document.querySelector(
            `.grid-cell[data-row="${this.currentAttempt}"][data-col="${this.currentPosition}"]`
        );
        cell.textContent = '';
        cell.classList.remove('filled');
    }

    submitGuess() {
        if (!this.gameActive || this.currentPosition !== 5) return;

        const guess = Array.from(document.querySelectorAll(
            `.grid-cell[data-row="${this.currentAttempt}"]`
        )).map(cell => cell.textContent).join('');

        this.ws.send(JSON.stringify({
            type: 'GUESS',
            playerName: this.playerName,
            roomCode: this.roomCode,
            guess: guess,
            attemptNumber: this.currentAttempt + 1
        }));
    }

    handleGuessResult(data) {
        const { result, isCorrect, leaderboard } = data;
        
        // Colorir as células
        result.forEach((color, index) => {
            const cell = document.querySelector(
                `.grid-cell[data-row="${this.currentAttempt}"][data-col="${index}"]`
            );
            cell.classList.add(color);
            
            // Atualizar o teclado
            const letter = cell.textContent;
            const key = document.querySelector(`.key[data-key="${letter}"]`);
            if (key) {
                if (color === 'green') {
                    key.classList.add('green');
                } else if (color === 'yellow' && !key.classList.contains('green')) {
                    key.classList.add('yellow');
                } else if (color === 'gray' && !key.classList.contains('green') && !key.classList.contains('yellow')) {
                    key.classList.add('disabled');
                }
            }
        });

        if (isCorrect || this.currentAttempt === 5) {
            this.endGame(isCorrect, leaderboard);
        } else {
            this.currentAttempt++;
            this.currentPosition = 0;
        }
    }

    endGame(isWinner, leaderboard) {
        this.gameActive = false;
        const endScreen = document.getElementById('end-screen');
        const endMessage = document.getElementById('end-message');
        const attemptsCount = document.getElementById('attempts-count');
        const timeElapsed = document.getElementById('time-elapsed');
        const leaderboardTable = document.querySelector('#leaderboard-table tbody');

        endMessage.textContent = isWinner ? 
            'Parabéns! Você acertou!' : 
            'Fim de jogo! Tente novamente!';
        
        attemptsCount.textContent = this.currentAttempt + 1;
        const totalTime = Math.floor((Date.now() - this.startTime) / 1000);
        timeElapsed.textContent = `${Math.floor(totalTime / 60)}:${(totalTime % 60).toString().padStart(2, '0')}`;

        // Preencher o placar
        leaderboardTable.innerHTML = '';
        if (leaderboard) {
            leaderboard.forEach((score, index) => {
                const row = leaderboardTable.insertRow();
                row.insertCell(0).textContent = index + 1;
                row.insertCell(1).textContent = score.playerName;
                row.insertCell(2).textContent = score.attempts;
                row.insertCell(3).textContent = 
                    `${Math.floor(score.time / 60)}:${(Math.floor(score.time) % 60).toString().padStart(2, '0')}`;
            });
        }

        document.getElementById('game-screen').classList.add('hidden');
        endScreen.classList.remove('hidden');
    }

    resetGame() {
        document.getElementById('end-screen').classList.add('hidden');
        document.getElementById('initial-screen').classList.remove('hidden');
        this.currentAttempt = 0;
        this.currentPosition = 0;
        this.gameActive = false;
        this.startTime = null;
        this.roomCode = '';
        this.createGameGrid();
        this.createKeyboard();
    }
}

// Iniciar o jogo quando a página carregar
window.addEventListener('load', () => {
    new WordGame();
});