const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 30;
const PREVIEW_BLOCK_SIZE = 24;
// 按单次同时消除 0-4 行计算的基础分值。
const LINE_CLEAR_BASE_SCORES = [0, 100, 300, 500, 800];
const MAX_LINES_PER_CLEAR = 4;
const START_DROP_INTERVAL = 700;
const MIN_DROP_INTERVAL = 120;
const LEVEL_SPEED_STEP = 55;
const ROTATION_KICK_OFFSETS = [0, 1, -1, 2, -2];

const SHAPES = {
  I: [[1, 1, 1, 1]],
  J: [
    [1, 0, 0],
    [1, 1, 1],
  ],
  L: [
    [0, 0, 1],
    [1, 1, 1],
  ],
  O: [
    [1, 1],
    [1, 1],
  ],
  S: [
    [0, 1, 1],
    [1, 1, 0],
  ],
  T: [
    [0, 1, 0],
    [1, 1, 1],
  ],
  Z: [
    [1, 1, 0],
    [0, 1, 1],
  ],
};

const COLORS = {
  I: "#38bdf8",
  J: "#60a5fa",
  L: "#fb923c",
  O: "#facc15",
  S: "#4ade80",
  T: "#c084fc",
  Z: "#f87171",
};

const canvas = document.getElementById("game");
const context = canvas.getContext("2d");
const nextCanvas = document.getElementById("next");
const nextContext = nextCanvas.getContext("2d");
const overlay = document.getElementById("overlay");
const scoreElement = document.getElementById("score");
const linesElement = document.getElementById("lines");
const levelElement = document.getElementById("level");
const restartButton = document.getElementById("restartButton");
const touchControls = document.querySelector(".touch-controls");

// 统一按网格单位绘制，避免手动换算像素坐标。
context.scale(BLOCK_SIZE, BLOCK_SIZE);
nextContext.setTransform(PREVIEW_BLOCK_SIZE, 0, 0, PREVIEW_BLOCK_SIZE, 0, 0);

const state = {
  board: createMatrix(COLS, ROWS),
  player: null,
  nextPiece: null,
  bag: [],
  score: 0,
  lines: 0,
  level: 1,
  dropCounter: 0,
  lastTime: 0,
  dropInterval: START_DROP_INTERVAL,
  isRunning: false,
  isPaused: false,
  isGameOver: false,
};

function createMatrix(width, height) {
  return Array.from({ length: height }, () => Array(width).fill(0));
}

function createPiece(type) {
  return {
    type,
    matrix: SHAPES[type].map((row) => [...row]),
    pos: { x: 0, y: 0 },
  };
}

function refillBag() {
  const types = Object.keys(SHAPES);

  for (let currentIndex = types.length - 1; currentIndex > 0; currentIndex -= 1) {
    const randomIndex = Math.floor(Math.random() * (currentIndex + 1));
    [types[currentIndex], types[randomIndex]] = [types[randomIndex], types[currentIndex]];
  }

  state.bag = types.map((type) => createPiece(type));
}

function getNextPiece() {
  if (!state.bag.length) {
    refillBag();
  }

  return state.bag.pop();
}

function resetBoard() {
  state.board = createMatrix(COLS, ROWS);
  state.score = 0;
  state.lines = 0;
  state.level = 1;
  state.dropInterval = START_DROP_INTERVAL;
  state.dropCounter = 0;
  state.lastTime = 0;
  state.isRunning = true;
  state.isPaused = false;
  state.isGameOver = false;
  state.bag = [];
  state.nextPiece = getNextPiece();
  spawnPlayer();
  updateStats();
  setOverlay("");
}

function spawnPlayer() {
  state.player = state.nextPiece ?? getNextPiece();
  state.nextPiece = getNextPiece();
  state.player.pos.y = 0;
  state.player.pos.x = Math.floor((COLS - state.player.matrix[0].length) / 2);

  if (collide(state.board, state.player)) {
    state.isGameOver = true;
    state.isRunning = false;
    setOverlay("游戏结束\n按 R 或点击“重新开始”再来一局", true);
  }

  drawNextPiece();
}

function collide(board, piece) {
  return piece.matrix.some((row, y) =>
    row.some((value, x) => {
      if (!value) {
        return false;
      }

      const boardY = y + piece.pos.y;
      const boardX = x + piece.pos.x;
      return (
        boardX < 0 ||
        boardX >= COLS ||
        boardY >= ROWS ||
        (boardY >= 0 && board[boardY][boardX] !== 0)
      );
    }),
  );
}

function merge(board, piece) {
  piece.matrix.forEach((row, y) => {
    row.forEach((value, x) => {
      if (value) {
        board[y + piece.pos.y][x + piece.pos.x] = piece.type;
      }
    });
  });
}

function clearLines() {
  let cleared = 0;

  outer: for (let y = ROWS - 1; y >= 0; y -= 1) {
    for (let x = 0; x < COLS; x += 1) {
      if (state.board[y][x] === 0) {
        continue outer;
      }
    }

    const row = state.board.splice(y, 1)[0].fill(0);
    state.board.unshift(row);
    cleared += 1;
    y += 1;
  }

  if (cleared > 0) {
    state.lines += cleared;
    state.level = Math.floor(state.lines / 10) + 1;
    state.dropInterval = Math.max(
      MIN_DROP_INTERVAL,
      START_DROP_INTERVAL - (state.level - 1) * LEVEL_SPEED_STEP,
    );
    const scoringLines = Math.min(cleared, MAX_LINES_PER_CLEAR);
    state.score += LINE_CLEAR_BASE_SCORES[scoringLines] * state.level;
    updateStats();
  }
}

function playerDrop() {
  if (!state.isRunning || state.isPaused) {
    return;
  }

  state.player.pos.y += 1;
  if (collide(state.board, state.player)) {
    state.player.pos.y -= 1;
    merge(state.board, state.player);
    clearLines();
    spawnPlayer();
    if (!state.isGameOver) {
      updateStats();
    }
  }
  state.dropCounter = 0;
}

function hardDrop() {
  if (!state.isRunning || state.isPaused) {
    return;
  }

  while (!collide(state.board, state.player)) {
    state.player.pos.y += 1;
  }
  state.player.pos.y -= 1;
  merge(state.board, state.player);
  clearLines();
  spawnPlayer();
  state.dropCounter = 0;
}

function playerMove(offset) {
  if (!state.isRunning || state.isPaused) {
    return;
  }

  state.player.pos.x += offset;
  if (collide(state.board, state.player)) {
    state.player.pos.x -= offset;
  }
}

function rotateMatrix(matrix) {
  return matrix[0].map((_, columnIndex) =>
    matrix.map((row) => row[columnIndex]).reverse(),
  );
}

function playerRotate() {
  if (!state.isRunning || state.isPaused) {
    return;
  }

  const originalMatrix = state.player.matrix.map((row) => [...row]);
  const originalX = state.player.pos.x;
  let kickIndex = 0;
  state.player.matrix = rotateMatrix(state.player.matrix);

  while (collide(state.board, state.player)) {
    if (kickIndex >= ROTATION_KICK_OFFSETS.length) {
      state.player.matrix = originalMatrix;
      state.player.pos.x = originalX;
      return;
    }

    state.player.pos.x = originalX + ROTATION_KICK_OFFSETS[kickIndex];
    kickIndex += 1;
  }
}

function drawCell(ctx, x, y, color, size = 1) {
  ctx.fillStyle = color;
  ctx.fillRect(x, y, size, size);
  ctx.strokeStyle = "rgba(15, 23, 42, 0.45)";
  ctx.lineWidth = 0.08;
  ctx.strokeRect(x, y, size, size);
}

function drawMatrix(ctx, matrix, offset, type) {
  matrix.forEach((row, y) => {
    row.forEach((value, x) => {
      if (value) {
        drawCell(
          ctx,
          x + offset.x,
          y + offset.y,
          COLORS[type],
          1,
        );
      }
    });
  });
}

function drawBoardGrid() {
  context.strokeStyle = "rgba(148, 163, 184, 0.12)";
  context.lineWidth = 0.04;
  for (let x = 0; x <= COLS; x += 1) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, ROWS);
    context.stroke();
  }
  for (let y = 0; y <= ROWS; y += 1) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(COLS, y);
    context.stroke();
  }
}

function draw() {
  context.fillStyle = "#020617";
  context.fillRect(0, 0, COLS, ROWS);
  drawBoardGrid();

  state.board.forEach((row, y) => {
    row.forEach((type, x) => {
      if (type) {
        drawCell(context, x, y, COLORS[type]);
      }
    });
  });

  if (state.player) {
    drawMatrix(context, state.player.matrix, state.player.pos, state.player.type);
  }
}

function drawNextPiece() {
  nextContext.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
  nextContext.fillStyle = "#020617";
  nextContext.fillRect(0, 0, 5, 5);

  if (!state.nextPiece) {
    return;
  }

  const matrix = state.nextPiece.matrix;
  const offset = {
    x: (5 - matrix[0].length) / 2,
    y: (5 - matrix.length) / 2,
  };

  drawMatrix(nextContext, matrix, offset, state.nextPiece.type);
}

function updateStats() {
  scoreElement.textContent = String(state.score);
  linesElement.textContent = String(state.lines);
  levelElement.textContent = String(state.level);
}

function setOverlay(message, visible = false) {
  overlay.textContent = message;
  overlay.classList.toggle("show", visible || Boolean(message));
}

function togglePause() {
  if (!state.isRunning && !state.isGameOver) {
    state.isRunning = true;
    setOverlay("");
    return;
  }

  if (state.isGameOver) {
    return;
  }

  state.isPaused = !state.isPaused;
  setOverlay(state.isPaused ? "已暂停\n按 P 继续游戏" : "", state.isPaused);
}

function handleAction(action) {
  if (!state.isRunning && !state.isGameOver && action !== "pause") {
    state.isRunning = true;
    setOverlay("");
  }

  switch (action) {
    case "left":
      playerMove(-1);
      break;
    case "right":
      playerMove(1);
      break;
    case "down":
      playerDrop();
      break;
    case "rotate":
      playerRotate();
      break;
    case "drop":
      hardDrop();
      break;
    case "pause":
      togglePause();
      break;
    case "restart":
      resetBoard();
      break;
    default:
      break;
  }
}

function update(time = 0) {
  const delta = time - state.lastTime;
  state.lastTime = time;

  if (state.isRunning && !state.isPaused && !state.isGameOver) {
    state.dropCounter += delta;
    if (state.dropCounter > state.dropInterval) {
      playerDrop();
    }
  }

  draw();
  requestAnimationFrame(update);
}

document.addEventListener("keydown", (event) => {
  if (
    ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Space", "KeyP", "KeyR"].includes(event.code)
  ) {
    event.preventDefault();
  }

  const keyActions = {
    ArrowLeft: "left",
    ArrowRight: "right",
    ArrowUp: "rotate",
    ArrowDown: "down",
    Space: "drop",
    KeyP: "pause",
    KeyR: "restart",
  };

  const action = keyActions[event.code];
  if (action) {
    handleAction(action);
  }
});

restartButton.addEventListener("click", () => handleAction("restart"));

touchControls.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  handleAction(button.dataset.action);
});

resetBoard();
setOverlay("按方向键、空格或下方按钮开始", true);
state.isRunning = false;
drawNextPiece();
update();
