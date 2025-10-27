<template>
	<div id="app">
		<h1>Othello AlphaZero</h1>

		<GameControls :current-player="currentPlayer" :board-size="boardSize" :game-status="gameStatus"
			:pass-action="hasPassAction" :piece-counts="pieceCounts" :is-processing="isProcessing"
			@new-game="startNewGame" @pass-turn="handleHumanMove({action: 'pass'})" />

		<OthelloBoard :board="boardState" :board-size="boardSize" :legal-moves="legalMoves" :last-move="lastMove"
			@move-made="handleHumanMove" />

<!-- 		<div v-if="gameStatus !== 'Ongoing'" class="game-over-message">
			<h2>{{ gameStatus }}</h2>
			<button @click="startNewGame({ size: boardSize, firstPlayer: 1 })">Play Again (Human First)</button>
		</div> -->

		<div class="game-info">
			<!-- 【悔棋按钮】只有当 historyLength > 1 时才可悔棋 -->
			<button @click="handleUndoMove" :disabled="isProcessing || historyLength <= 1" class="undo-button">
				🔙 悔棋 (Undo)
			</button>
		</div>
	</div>
</template>

<script>
	import axios from 'axios';
	import OthelloBoard from './components/OthelloBoard.vue';
	import GameControls from './components/GameControls.vue';

	// 后端 API 地址，请替换为你的 Hugging Face URL
	// 请注意，我使用了你的 Hugging Face URL，如果本地调试请改回 localhost
	const API_BASE_URL = 'https://sodastar-othello-alphazero-docker.hf.space/api/game';
	// const API_BASE_URL = 'http://localhost:7860/api/game';

	const FLIP_ANIMATION_DURATION = 0.4;

	function waitForDelay(durationInSeconds) {
		return new Promise(resolve => setTimeout(resolve, durationInSeconds * 1000));
	}

	export default {
		name: 'App',
		components: {
			OthelloBoard,
			GameControls
		},
		data() {
			return {
				boardSize: 8, // Current board size
				boardState: [], // 2D array of the board
				currentPlayer: 1, // 1: Human (O), -1: AI (X)
				legalMoves: [], // List of legal moves [{x, y}, ...]
				lastMove: null, // Last move made {x, y}
				gameStatus: 'Initializing',
				isProcessing: false, // Prevents duplicated clicks and controls AI turn
				historyLength: 1, // 【NEW】Tracks the number of historical states for undo logic
			};
		},
		computed: {
			hasPassAction() {
				// Allow Pass only if ongoing, human's turn, and no legal moves
				return this.legalMoves.length === 0 && this.gameStatus === 'Ongoing' && this.currentPlayer === 1;
			},
			pieceCounts() {
				let white = 0;
				let black = 0;

				if (this.boardState && this.boardState.length > 0) {
					this.boardState.forEach(row => {
						row.forEach(piece => {
							if (piece === 1) { // 1 is Human (White)
								white++;
							} else if (piece === -1) { // -1 is AI (Black)
								black++;
							}
						});
					});
				}

				const totalSquares = this.boardSize * this.boardSize;
				const empty = totalSquares - white - black;

				return {
					white,
					black,
					empty
				};
			}
		},
		mounted() {
			// Start default 8x8 game, Human first
			this.startNewGame({
				size: this.boardSize,
				firstPlayer: 1
			});
		},
		methods: {
			// 【NEW】Handles the undo move request
			async handleUndoMove() {
				// Prevent undo if processing or at the initial state
				if (this.isProcessing || this.historyLength <= 1) return;

				this.isProcessing = true;
				this.gameStatus = 'Undoing Move...';

				try {
					// Call the new backend undo API
					const response = await axios.post(`${API_BASE_URL}/undo_move`);

					// Step 1: Update state based on backend response (includes new historyLength)
					this.updateGameState(response.data);

					// Step 2: Check if AI should automatically move (occurs if AI was the starting player
					// and we reverted to the initial state, or if the game requires a pass)
					if (this.gameStatus === 'Ongoing' && this.currentPlayer === -1) {
						// Auto-trigger AI move
						this.handleAIMove();
					} else {
						// Release lock, waiting for human move
						this.isProcessing = false;
					}

				} catch (error) {
					console.error('Error undoing move:', error.response ? error.response.data : error);
					this.gameStatus = 'Error during Undo';
					// Ensure lock is released on error
					this.isProcessing = false;
				}
			},

			async startNewGame(config) {
				if (this.isProcessing) return;
				this.isProcessing = true;

				const {
					size,
					firstPlayer
				} = config;

				this.gameStatus = `Starting ${size}x${size} game...`;
				this.boardSize = size;

				try {
					const response = await axios.post(`${API_BASE_URL}/new`, {
						size: size,
						first_player: firstPlayer
					});

					this.updateGameState(response.data);
					// 【FIX】Ensure historyLength is correctly initialized
					this.historyLength = response.data.history_length || 1;

				} catch (error) {
					console.error('Error starting new game:', error.response ? error.response.data : error);
					this.gameStatus = 'Error: Cannot connect to Python Backend (check terminal)';
				} finally {
					// Only release lock if it's human's turn
					if (this.currentPlayer === 1) {
						this.isProcessing = false;
					}
				}
			},

			async handleAIMove() {
				if (this.gameStatus !== 'Ongoing' || this.currentPlayer !== -1) return;

				this.isProcessing = true;
				this.gameStatus = 'AI is thinking...';

				try {
					const response = await axios.post(`${API_BASE_URL}/ai_move`);

					// Step 1: Update state (includes historyLength update from backend)
					this.updateGameState(response.data);

					// Step 2: Wait for flip animation
					await waitForDelay(FLIP_ANIMATION_DURATION);

				} catch (error) {
					console.error('Error handling AI move:', error.response ? error.response.data : error);
					this.gameStatus = 'Error during AI move';
				} finally {
					this.isProcessing = false;

					// Check if AI needs to Pass or play again
					if (this.gameStatus === 'Ongoing' && this.currentPlayer === -1) {
						this.handleAIMove();
					}
				}
			},

			async handleHumanMove(coords) {
				if (this.gameStatus !== 'Ongoing' || this.currentPlayer !== 1 || this.isProcessing) return;

				const {
					x,
					y,
					action
				} = coords;

				this.isProcessing = true;
				this.gameStatus = 'Processing Move...';

				try {
					// Step 1: Send human move request
					const response = await axios.post(`${API_BASE_URL}/human_move`, {
						x,
						y,
						action
					});

					// Step 2: Update board state (now it's AI's turn)
					this.updateGameState(response.data);

					// Step 3: Wait for human flip animation
					await waitForDelay(FLIP_ANIMATION_DURATION);

					// Step 4: Check state; if it's AI's turn, trigger AI move
					if (this.gameStatus === 'Ongoing' && this.currentPlayer === -1) {
						// handleAIMove takes over processing lock
						this.handleAIMove();
					} else {
						// Game ended or human passed back to human
						this.isProcessing = false;
					}

				} catch (error) {
					console.error('Error handling human move:', error.response ? error.response.data : error);
					this.gameStatus = 'Error during human move';
					this.isProcessing = false;
				}
			},

			updateGameState(data) {
				this.boardState = data.board;
				this.legalMoves = data.legal_moves;
				this.currentPlayer = data.current_player;
				this.lastMove = data.last_move;
				this.gameStatus = data.status;

				// 【CORE FIX】Always use the history_length provided by the backend
				if (data.history_length !== undefined) {
					this.historyLength = data.history_length;
				}

				if (this.gameStatus === 'Ongoing' && this.currentPlayer === -1 && !this.isProcessing) {
					this.gameStatus = 'AI is thinking...';
				}
			}
		}
	};
</script>

<style>
	#app {
		font-family: Avenir, Helvetica, Arial, sans-serif;
		text-align: center;
		color: #2c3e50;
		margin-top: 20px;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.game-over-message {
		margin-top: 20px;
		padding: 15px;
		border: 2px solid red;
		background-color: #ffe0e0;
	}

	/* Optional: Basic styling for the undo button */
	.undo-button {
		padding: 10px 20px;
		background-color: #fca5a5;
		color: #333;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		font-weight: bold;
		transition: background-color 0.2s;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.undo-button:hover:not(:disabled) {
		background-color: #f87171;
	}

	.undo-button:disabled {
		background-color: #ccc;
		color: #666;
		cursor: not-allowed;
	}
	
	.game-info {
		margin-top: 20px;
	}
</style>
