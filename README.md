# AlphaZero-Othello-web

&gt; 🌟 基于 AlphaZero 的网络版黑白棋（Othello/Reversi）对战平台  
&gt; 前端：Vue.js | 后端：Flask + PyTorch + MCTS | 部署：GitHub Pages × Hugging Face Spaces

---

## 1. 项目简介
- 采用 **前后端分离** 架构，提供 **在线 AI 对战** 体验  
- AI 核心：AlphaZero 算法（PyTorch 神经网络 + 蒙特卡洛树搜索）  
- 目标：展示如何将复杂 ML 模型部署为 **可扩展 Web API**

---

## 2. 在线体验
| 组件 | 地址 |
|---|---|
| 🌐 **前端**（GitHub Pages） | [https://zhenghong-liu.github.io/AlphaZero-Othello-web/](https://zhenghong-liu.github.io/AlphaZero-Othello-web/) |
| 🧠 **后端 API**（Hugging Face Spaces） | [https://huggingface.co/spaces/sodastar/othello-alphazero-docker](https://huggingface.co/spaces/sodastar/othello-alphazero-docker) |

---

## 3. 技术栈
| 组件 | 技术 | 说明 |
|---|---|---|
| 前端 | Vue 2.x + Axios | 棋盘渲染、用户交互、动画、API 通信 |
| 后端 | Python 3.x + Flask | RESTful API，接收棋盘 → 返回 AI 落子 |
| AI 核心 | PyTorch + AlphaZero + MCTS | 神经网络评估 + 树搜索决策 |

---

## 4. 项目结构（Monorepo）

```
AlphaZero-Othello-web/
├── othello-backend/         # Python Flask 后端
│   ├── app.py               # Flask 入口
│   ├── alphazero.py         # AlphaZero / MCTS / NN
│   ├── game.py              # 黑白棋规则
│   ├── requirements.txt
│   ├── Dockerfile           # HF Spaces 镜像
│   └── temp/best.pth.tar    # 预训练权重（Git LFS）
└── othello-frontend/        # Vue 前端
├── src/
├── public/
└── vue.config.js        # GitHub Pages 路径配置
```


---

## 5. 部署细节
### 5.1 前端（GitHub Pages）
- **构建**：`npm run build`  
- **发布**：`npx gh-pages -d dist` → `gh-pages` 分支  
- **路径**：`vue.config.js` 中 `publicPath: '/AlphaZero-Othello-web/'`

### 5.2 后端（Hugging Face Spaces）
- **平台**：Docker SDK  
- **端口**：Flask 监听 `0.0.0.0:7860`  
- **模型**：`best.pth.tar` 通过 Git LFS 存于 `./temp/`，由 `app.py` 加载

### 5.3 关键联通点
- 前端 `src/App.vue` 中的 `API_BASE_URL` 已指向 Hugging Face 地址，支持 CORS

---

## 6. 本地开发
### 6.1 后端
```bash
cd othello-backend
pip install -r requirements.txt
python app.py          # 默认 http://localhost:5001
```

### 6.2 前端
```bash
cd othello-frontend
npm install
npm run serve         # 默认 http://localhost:8080
```

联调时，将 src/App.vue 里的 API_BASE_URL 临时改为 http://localhost:5001/api/game

部署是，将 src/App.vue 里的 API_BASE_URL 改为 Hugging Face 地址：'https://sodastar-othello-alphazero-docker.hf.space/api/game';

---

## 7. 参考

https://github.com/schinger/AlphaZero/tree/main