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
const audioToggleButton = document.getElementById("audioToggleButton");
const restartButton = document.getElementById("restartButton");
const touchControls = document.querySelector(".touch-controls");
const AudioContextClass = window.AudioContext || window.webkitAudioContext;

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

const audioState = {
  enabled: false,
  context: null,
  masterGain: null,
  musicGain: null,
  effectGain: null,
  musicTimer: null,
  beatIndex: 0,
};

const MUSIC_SEQUENCE = [
  { bass: 130.81, melody: [261.63, 392.0] },
  { bass: 146.83, melody: [293.66, 440.0] },
  { bass: 164.81, melody: [329.63, 493.88] },
  { bass: 146.83, melody: [293.66, 440.0] },
  { bass: 130.81, melody: [261.63, 392.0] },
  { bass: 164.81, melody: [329.63, 523.25] },
  { bass: 196.0, melody: [392.0, 587.33] },
  { bass: 146.83, melody: [293.66, 440.0] },
];

function updateAudioButton() {
  const buttonText = audioState.enabled ? "声音：开" : "声音：关";
  audioToggleButton.textContent = buttonText;
  audioToggleButton.setAttribute("aria-pressed", String(audioState.enabled));
}

function initializeAudio() {
  if (!AudioContextClass || audioState.context) {
    return;
  }

  const contextInstance = new AudioContextClass();
  const masterGain = contextInstance.createGain();
  const musicGain = contextInstance.createGain();
  const effectGain = contextInstance.createGain();

  masterGain.gain.value = 0.24;
  musicGain.gain.value = 0.11;
  effectGain.gain.value = 0.18;

  musicGain.connect(masterGain);
  effectGain.connect(masterGain);
  masterGain.connect(contextInstance.destination);

  audioState.context = contextInstance;
  audioState.masterGain = masterGain;
  audioState.musicGain = musicGain;
  audioState.effectGain = effectGain;
}

async function ensureAudioReady() {
  if (!audioState.enabled) {
    return false;
  }

  initializeAudio();

  if (!audioState.context) {
    return false;
  }

  if (audioState.context.state === "suspended") {
    await audioState.context.resume();
  }

  updateAudioPlayback();
  return true;
}

function playTone(
  frequency,
  startTime,
  duration,
  {
    destination = audioState.effectGain,
    volume = 0.14,
    type = "sine",
    attack = 0.01,
    release = 0.08,
  } = {},
) {
  if (!audioState.enabled || !audioState.context || !destination) {
    return;
  }

  const oscillator = audioState.context.createOscillator();
  const gainNode = audioState.context.createGain();

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, startTime);

  gainNode.gain.setValueAtTime(0.0001, startTime);
  gainNode.gain.linearRampToValueAtTime(volume, startTime + attack);
  gainNode.gain.exponentialRampToValueAtTime(
    0.0001,
    startTime + duration + release,
  );

  oscillator.connect(gainNode);
  gainNode.connect(destination);
  oscillator.start(startTime);
  oscillator.stop(startTime + duration + release);
}

function shouldPlayMusic() {
  return (
    audioState.enabled &&
    audioState.context &&
    state.isRunning &&
    !state.isPaused &&
    !state.isGameOver
  );
}

function stopMusicLoop() {
  if (audioState.musicTimer) {
    window.clearTimeout(audioState.musicTimer);
    audioState.musicTimer = null;
  }
}

function queueMusicBeat() {
  if (!shouldPlayMusic()) {
    stopMusicLoop();
    return;
  }

  const step = MUSIC_SEQUENCE[audioState.beatIndex % MUSIC_SEQUENCE.length];
  const startTime = audioState.context.currentTime + 0.02;

  playTone(step.bass, startTime, 0.28, {
    destination: audioState.musicGain,
    volume: 0.08,
    type: "triangle",
    attack: 0.01,
    release: 0.12,
  });

  step.melody.forEach((note, index) => {
    playTone(note, startTime + index * 0.08, 0.18, {
      destination: audioState.musicGain,
      volume: 0.05,
      type: "sine",
      attack: 0.01,
      release: 0.12,
    });
  });

  audioState.beatIndex += 1;
  audioState.musicTimer = window.setTimeout(queueMusicBeat, 340);
}

function updateAudioPlayback() {
  stopMusicLoop();
  if (shouldPlayMusic()) {
    queueMusicBeat();
  }
}

function playEffect(name) {
  if (!audioState.enabled || !audioState.context) {
    return;
  }

  const now = audioState.context.currentTime + 0.01;

  switch (name) {
    case "move":
      playTone(392.0, now, 0.04, { type: "square", volume: 0.08, release: 0.04 });
      break;
    case "rotate":
      playTone(523.25, now, 0.05, { type: "triangle", volume: 0.1, release: 0.05 });
      playTone(659.25, now + 0.05, 0.05, { type: "triangle", volume: 0.07, release: 0.05 });
      break;
    case "softDrop":
      playTone(246.94, now, 0.03, { type: "sawtooth", volume: 0.05, release: 0.03 });
      break;
    case "lock":
      playTone(196.0, now, 0.08, { type: "square", volume: 0.08, release: 0.06 });
      break;
    case "hardDrop":
      playTone(329.63, now, 0.05, { type: "square", volume: 0.1, release: 0.04 });
      playTone(164.81, now + 0.06, 0.09, { type: "square", volume: 0.12, release: 0.08 });
      break;
    case "lineClear":
      playTone(523.25, now, 0.07, { type: "triangle", volume: 0.11, release: 0.05 });
      playTone(659.25, now + 0.08, 0.07, { type: "triangle", volume: 0.11, release: 0.05 });
      playTone(783.99, now + 0.16, 0.12, { type: "triangle", volume: 0.12, release: 0.08 });
      break;
    case "pause":
      playTone(349.23, now, 0.06, { type: "sine", volume: 0.08, release: 0.05 });
      playTone(293.66, now + 0.08, 0.06, { type: "sine", volume: 0.08, release: 0.05 });
      break;
    case "resume":
    case "start":
      playTone(293.66, now, 0.06, { type: "sine", volume: 0.08, release: 0.05 });
      playTone(392.0, now + 0.08, 0.08, { type: "sine", volume: 0.1, release: 0.06 });
      break;
    case "gameOver":
      playTone(329.63, now, 0.12, { type: "sawtooth", volume: 0.12, release: 0.1 });
      playTone(246.94, now + 0.14, 0.12, { type: "sawtooth", volume: 0.1, release: 0.1 });
      playTone(196.0, now + 0.28, 0.18, { type: "sawtooth", volume: 0.1, release: 0.12 });
      break;
    default:
      break;
  }
}

async function setAudioEnabled(enabled) {
  audioState.enabled = enabled;
  updateAudioButton();

  if (!enabled) {
    stopMusicLoop();
    if (audioState.masterGain && audioState.context) {
      audioState.masterGain.gain.cancelScheduledValues(audioState.context.currentTime);
      audioState.masterGain.gain.setValueAtTime(0, audioState.context.currentTime);
    }
    return;
  }

  const audioReady = await ensureAudioReady();
  if (!audioReady) {
    return;
  }

  audioState.masterGain.gain.cancelScheduledValues(audioState.context.currentTime);
  audioState.masterGain.gain.setValueAtTime(0, audioState.context.currentTime);
  audioState.masterGain.gain.linearRampToValueAtTime(0.24, audioState.context.currentTime + 0.18);
  playEffect(state.isRunning && !state.isPaused ? "resume" : "start");
}

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
  updateAudioPlayback();
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
    updateAudioPlayback();
    playEffect("gameOver");
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

  return cleared;
}

function playerDrop(triggeredByPlayer = false) {
  if (!state.isRunning || state.isPaused) {
    return false;
  }

  state.player.pos.y += 1;
  if (collide(state.board, state.player)) {
    state.player.pos.y -= 1;
    merge(state.board, state.player);
    const cleared = clearLines();
    playEffect(cleared > 0 ? "lineClear" : "lock");
    spawnPlayer();
    if (!state.isGameOver) {
      updateStats();
    }
  } else if (triggeredByPlayer) {
    playEffect("softDrop");
  }
  state.dropCounter = 0;
  return true;
}

function hardDrop() {
  if (!state.isRunning || state.isPaused) {
    return false;
  }

  while (!collide(state.board, state.player)) {
    state.player.pos.y += 1;
  }
  state.player.pos.y -= 1;
  merge(state.board, state.player);
  playEffect("hardDrop");
  if (clearLines() > 0) {
    playEffect("lineClear");
  }
  spawnPlayer();
  state.dropCounter = 0;
  return true;
}

function playerMove(offset) {
  if (!state.isRunning || state.isPaused) {
    return false;
  }

  state.player.pos.x += offset;
  if (collide(state.board, state.player)) {
    state.player.pos.x -= offset;
    return false;
  }

  playEffect("move");
  return true;
}

function rotateMatrix(matrix) {
  return matrix[0].map((_, columnIndex) =>
    matrix.map((row) => row[columnIndex]).reverse(),
  );
}

function playerRotate() {
  if (!state.isRunning || state.isPaused) {
    return false;
  }

  const originalMatrix = state.player.matrix.map((row) => [...row]);
  const originalX = state.player.pos.x;
  let kickIndex = 0;
  state.player.matrix = rotateMatrix(state.player.matrix);

  while (collide(state.board, state.player)) {
    if (kickIndex >= ROTATION_KICK_OFFSETS.length) {
      state.player.matrix = originalMatrix;
      state.player.pos.x = originalX;
      return false;
    }

    state.player.pos.x = originalX + ROTATION_KICK_OFFSETS[kickIndex];
    kickIndex += 1;
  }

  playEffect("rotate");
  return true;
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
    updateAudioPlayback();
    playEffect("start");
    return;
  }

  if (state.isGameOver) {
    return;
  }

  state.isPaused = !state.isPaused;
  setOverlay(state.isPaused ? "已暂停\n按 P 继续游戏" : "", state.isPaused);
  updateAudioPlayback();
  playEffect(state.isPaused ? "pause" : "resume");
}

async function handleAction(action) {
  if (action !== "audio") {
    await ensureAudioReady();
  }

  if (!state.isRunning && !state.isGameOver && !["pause", "audio"].includes(action)) {
    state.isRunning = true;
    setOverlay("");
    updateAudioPlayback();
  }

  switch (action) {
    case "left":
      playerMove(-1);
      break;
    case "right":
      playerMove(1);
      break;
    case "down":
      playerDrop(true);
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
      playEffect("start");
      break;
    case "audio":
      await setAudioEnabled(!audioState.enabled);
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
audioToggleButton.addEventListener("click", () => handleAction("audio"));

touchControls.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  handleAction(button.dataset.action);
});

resetBoard();
updateAudioButton();
setOverlay("按方向键、空格或下方按钮开始", true);
state.isRunning = false;
drawNextPiece();
update();
