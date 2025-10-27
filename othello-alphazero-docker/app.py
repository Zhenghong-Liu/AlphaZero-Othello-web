import numpy as np
import torch
import json
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import time

# 导入你的游戏和 AI 模块
from game import OthelloGame #
from alphazero import NNetWrapper, MCTS, dotdict #

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
# 启用 CORS，允许前端（通常在不同端口）访问
CORS(app)

# --- 全局状态和 AI 初始化 ---

# 默认参数 (与 alphazero.py 中的 args 保持一致)
args = dotdict({
    'lr': 0.001,
    'dropout': 0.1,
    'epochs': 10,
    'batch_size': 64,
    'cuda': torch.cuda.is_available(),
    'num_channels': 512,
    'numIters': 200,
    'numEps': 100,
    'tempThreshold': 15,
    'updateThreshold': 0.6,
    'maxlenOfQueue': 200000,
    'numItersForTrainExamplesHistory': 20,
    'numMCTSSims': 25,  # 训练时的 MCTS 模拟次数
    'arenaCompare': 40,
    'cpuct': 1,
    'checkpoint': './temp/',
    'load_model': True,
    'load_folder_file': ('./temp/','best.pth.tar'),
    'board_size': 8 # 默认 8x8
})

# 游戏和 AI 实例
game = None
nnet = None
mcts = None

# 游戏状态
current_board = None
current_player = 1 # 1: Human (White), -1: AI (Black)
last_move_coords = None
board_size = 8

history_stack = []
first_player_game = 1

# 【新增】辅助函数：保存当前状态到历史栈
def save_state():
    """保存当前棋盘的副本和当前轮到的玩家到历史栈。"""
    global current_board, current_player, history_stack
    # 保存当前棋盘的副本和当前轮到的玩家
    # 注意：这里保存的是未翻转的内部游戏状态
    history_stack.append((np.copy(current_board), current_player))

def init_game_and_ai(n):
    """根据板子大小初始化游戏和 AI 模块"""
    global game, nnet, mcts, board_size, history_stack, current_board
    board_size = n
    log.info(f"Initializing game and AI for {n}x{n} board.")
    game = OthelloGame(n) #

    # 重新配置 MCTS 参数用于 Play 模式
    play_args = dotdict({
        'numMCTSSims': 200,  # 对战时使用更多的模拟次数
        'cpuct': 1.0,
        'cuda': args.cuda # 继承 CUDA 设置
    })
    
    nnet = NNetWrapper(game, args) #
    # 假设你的模型文件已保存到 './checkpoint/best.pth.tar'
    try:
        load_folder = args.load_folder_file[0]
        load_file = args.load_folder_file[1]
        nnet.load_checkpoint(folder=load_folder, filename=load_file)
        log.info(f"Successfully loaded model from {load_folder}{load_file}")
    except ValueError as e:
        log.error(f"Failed to load model: {e}. AI will likely perform poorly.")
        
    mcts = MCTS(game, nnet, play_args) #

    # 【新增】清空历史栈并保存初始状态
    history_stack = []
    
    # 获取初始棋盘并保存
    current_board = game.getInitBoard()
    save_state()


def get_api_moves(board, player):
    """将 getValidMoves 结果从向量转换为 {x, y} 列表"""
    if game is None: return []
    
    valids = game.getValidMoves(board, player) #
    moves_list = []
    # 排除最后一个动作（Pass动作）
    for i in range(len(valids) - 1): #
        if valids[i] == 1:
            x = i // game.n
            y = i % game.n
            moves_list.append({'x': int(x), 'y': int(y)})
    return moves_list

def check_game_end(board, player):
    """检查游戏是否结束，并返回状态信息，基于绝对的棋子数量差异。"""
    
    result = game.getGameEnded(board, player) #
    
    status = 'Ongoing'
    score_diff = 0
    
    if result is not None:
        white_count = np.sum(board == 1)
        black_count = np.sum(board == -1)
        score_diff = int(white_count - black_count)
        
        if result == 0 or score_diff == 0:
            status = f"Game Over: Draw. Score: {white_count} vs {black_count}"
        elif score_diff > 0:
            status = f"Game Over: Human (O) Wins! Score: {white_count} vs {black_count}"
        elif score_diff < 0:
            status = f"Game Over: AI (X) Wins! Score: {white_count} vs {black_count}"
        else:
            status = f"Game Over: Draw. Score: {white_count} vs {black_count}"
    
    return status

@app.route('/api/game/new', methods=['POST'])
def new_game():
    global current_board, current_player, last_move_coords, board_size, history_stack, first_player_game
    data = request.json
    size = data.get('size', 8)
    
    first_player = data.get('first_player', 1) 
    first_player_game = first_player
    
    # 1. 初始化游戏和 AI
    # 只有在尺寸变化时才重新初始化 AI，否则只重置游戏
    if game is None or size != board_size:
        init_game_and_ai(size)

    # 如果尺寸不变，只重置历史栈和棋盘
    history_stack = []
    current_board = game.getInitBoard()
    save_state() # 保存初始状态 (栈长度 = 1)

    current_player = first_player 
    last_move_coords = None
    
    # 2. 处理 AI 先手逻辑
    if current_player == -1:
        # 【修复】删除 history_stack.pop()，因为初始状态 S_init 必须保留。
        # S_init 已经是 current_player = 1 的状态，我们只需要立即触发 AI 移动。
        # AI 移动逻辑 (ai_move_logic) 会执行 AI 动作并保存 S_AI_1 状态。
        history_stack = []
        
        # 立即触发 AI 移动
        current_board = np.flip(current_board, 0)
        status = check_game_end(current_board, current_player)
        if status == 'Ongoing':
             # is_init_move=True 确保 AI 逻辑中不再重复 save_state()
             # 因为 S_init 已经被保存，AI 下完后保存 S_AI_1
             return ai_move_logic(is_init_move=False) # 【修正】这里应该是 False，让 ai_move_logic 保存 S_AI_1
    
    # 3. 如果是 Human 先手或 AI 先手但游戏结束，则返回当前状态 (S_init)
    status = check_game_end(current_board, current_player)

    current_board = np.flip(current_board, 0)
    
    # 确保返回给前端的棋盘是垂直翻转的，以匹配前端的坐标系
    return jsonify({
        'board': current_board.tolist(),
        'legal_moves': get_api_moves(current_board, current_player),
        'current_player': current_player,
        'last_move': last_move_coords,
        'status': status,
        'history_length': len(history_stack) # 返回历史记录长度
    })


@app.route('/api/game/human_move', methods=['POST'])
def human_move():
    """处理人类玩家移动，并保存状态，返回给 AI 的中间状态"""
    global current_board, current_player, last_move_coords
    
    if current_player != 1 or check_game_end(current_board, current_player) != 'Ongoing':
        return jsonify({'error': 'Not your turn or game is over', 'history_length': len(history_stack)}), 400

    data = request.json
    x = data.get('x')
    y = data.get('y')

    if x is None or y is None:
        # 检查是否是 Pass 动作
        if data.get('action') == 'pass':
             action = game.n * game.n # Pass action is the last index
        else:
             return jsonify({'error': 'Invalid move coordinates', 'history_length': len(history_stack)}), 400
    else:
        action = game.n * x + y

    valids = game.getValidMoves(current_board, 1)
    if valids[action] == 0:
        return jsonify({'error': 'Illegal move', 'history_length': len(history_stack)}), 400
    
    # 1. 执行人类移动
    current_board, current_player = game.getNextState(current_board, 1, action)
    
    # 2. 【核心修改】保存人类移动后的状态 (State S_H: 轮到 AI 移动)
    save_state()
    
    if action != game.n * game.n:
        last_move_coords = {'x': x, 'y': y}
    else:
        last_move_coords = None # Human Pass
    
    status = check_game_end(current_board, current_player)

    # current_board = np.flip(current_board, 0)
    
    # 确保返回给前端的棋盘是垂直翻转的，以匹配前端的坐标系
    return jsonify({
        'board': current_board.tolist(), 
        'legal_moves': get_api_moves(current_board, current_player),
        'current_player': current_player,
        'last_move': last_move_coords,
        'status': status,
        'history_length': len(history_stack) # 【新增】返回历史记录长度
    })


def ai_move_logic(is_init_move=False):
    """AI 移动的逻辑封装，在 new_game 中调用"""
    global current_board, current_player, last_move_coords
    
    canonical_board = game.getCanonicalForm(current_board, -1) #
    
    # 获取 AI 的最佳动作 (temp=0)
    ai_action = np.argmax(mcts.getActionProb(canonical_board, temp=0)) #
    
    # 更新游戏状态
    current_board, next_player = game.getNextState(current_board, -1, ai_action) #
    current_player = next_player
    
    # 记录 AI 的移动坐标
    if ai_action != game.n * game.n: # 如果不是 Pass 动作
        ai_x = ai_action // game.n
        ai_y = ai_action % game.n
        last_move_coords = {'x': int(ai_x), 'y': int(ai_y)}
    else:
        last_move_coords = None # AI Pass
    
    status = check_game_end(current_board, current_player)

    # 【核心修改】保存 AI 移动后的状态 (State S_A: 轮到 Human 移动)
    # is_init_move 标记不再用于控制 save_state，因为 new_game 中只需要 AI 正常执行并保存状态
    save_state()

    # 确保返回给前端的棋盘是垂直翻转的，以匹配前端的坐标系
    return jsonify({
        'board': current_board.tolist(),
        'legal_moves': get_api_moves(current_board, current_player),
        'current_player': current_player,
        'last_move': last_move_coords,
        'status': status,
        'history_length': len(history_stack) # 【新增】返回历史记录长度
    })

# B. 新增 `ai_move` 路由

@app.route('/api/game/ai_move', methods=['POST'])
def ai_move():
    start_time = time.time()
    """触发 AI 移动，并返回最终状态"""
    global current_board, current_player, last_move_coords
    
    if current_player != -1:
        return jsonify({'error': 'Not AI turn', 'history_length': len(history_stack)}), 400
        
    response = ai_move_logic(is_init_move=False)

    # 控制 AI 最少思考时间为 0.5 秒
    end_time = time.time()
    used_time = end_time - start_time
    if used_time < 0.5:
        time.sleep(0.5 - used_time)  # 确保至少等待0.5秒

    return response


# app.py (新增路由)

@app.route('/api/game/undo_move', methods=['POST'])
def undo_move():
    """执行悔棋操作：回退到历史栈中的前一个人类落子完成前的状态（即撤销 Human move + AI move）。"""
    global current_board, current_player, last_move_coords, history_stack
    
    # 栈长度至少需要为 3 才能安全地回退一个完整的 (Human + AI) 步骤
    # 3 = S_init + S_Human_move + S_AI_move
    if len(history_stack) < 2:
        # 【修正】如果只有 S_init (长度=1) 或 S_AI_1 (长度=2, 发生在AI先手的第一步)，则不能再悔棋了
        return jsonify({
            'error': 'Cannot undo further. Only initial state remains or insufficient moves made.',
            'history_length': len(history_stack)
        }), 400
    
    # 场景 1: S_init -> S_AI_1 (AI 先手的第一步，长度为 2)
    # 此时只需要 pop() 一次，回到 S_init
    if len(history_stack) == 2:
        # 弹出 S_AI_1 状态
        history_stack.pop()
    
    # 场景 2: S_init -> S_H1 -> S_AI_1 (长度 >= 3)
    # 此时需要 pop() 两次，回到 S_H1 之前，即 S_init 或 S_AI_last
    elif len(history_stack) >= 3:
        # 1. 弹出 S_AI 状态 (AI move done, Human turn)
        history_stack.pop()

        # 2. 弹出 S_Human 状态 (Human move done, AI turn)
        history_stack.pop()

    
    # 3. 恢复到栈顶状态
    current_board_restored, current_player_restored = history_stack[-1]

    if len(history_stack) == 1 and first_player_game == 1:
        current_board_restored = np.flip(current_board_restored, 0)
    
    # 恢复状态
    current_board = np.copy(current_board_restored)
    current_player = current_player_restored 
    
    # 重置 last_move
    last_move_coords = None
    
    status = check_game_end(current_board, current_player)
    
    # 确保返回给前端的棋盘是垂直翻转的，以匹配前端的坐标系
    return jsonify({
        'board': current_board.tolist(),
        'legal_moves': get_api_moves(current_board, current_player),
        'current_player': current_player,
        'last_move': last_move_coords,
        'status': status,
        'history_length': len(history_stack) # 【新增】返回新的历史记录长度
    })

if __name__ == '__main__':
    # 初始化一个默认的 8x8 游戏实例
    init_game_and_ai(8)
    log.info("Starting Flask server on port 7860...")

    port = int(os.environ.get('PORT', 7860)) 
    # ... (日志) ...
    app.run(host='0.0.0.0', port=port)
