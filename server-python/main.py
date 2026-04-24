from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os
import uuid
import hashlib

app = FastAPI(title="Millow Messenger")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создание папок
for d in ["data", "uploads", "uploads/avatars"]:
    os.makedirs(d, exist_ok=True)

# Монтирование загрузок
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ============ ДАННЫЕ ============
SECRET_KEY = "millow_secret_2024"
users_db = {}
chats_db = {}
messages_db = []
online_users = {}
tokens = {}

# ============ ФУНКЦИИ ============
def hash_password(password):
    return hashlib.sha256((password + SECRET_KEY).encode()).hexdigest()

def create_token(user_id):
    token = str(uuid.uuid4())
    tokens[token] = {"user_id": user_id}
    return token

def verify_token(token):
    return tokens.get(token)

# ============ СТАРТОВЫЕ АККАУНТЫ ============
def create_startup_accounts():
    if len(users_db) == 0:
        # Аккаунт 1: TARAN
        uid1 = "startup_1"
        users_db[uid1] = {
            "id": uid1,
            "name": "TARAN",
            "email": "taran@millow.com",
            "password": hash_password("fastyk26tyr"),
            "avatar": "https://ui-avatars.com/api/?name=TARAN&background=8B5CF6&color=fff&size=200&bold=true",
            "bio": "Hey there! I'm using Millow 💜",
            "phone": "",
            "online": False,
            "lastSeen": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat()
        }
        
        # Аккаунт 2: Test
        uid2 = "startup_2"
        users_db[uid2] = {
            "id": uid2,
            "name": "Test",
            "email": "test@millow.com",
            "password": hash_password("test123"),
            "avatar": "https://ui-avatars.com/api/?name=TEST&background=EC4899&color=fff&size=200&bold=true",
            "bio": "Just testing Millow messenger",
            "phone": "",
            "online": False,
            "lastSeen": datetime.utcnow().isoformat(),
            "createdAt": datetime.utcnow().isoformat()
        }
        
        print("✅ Created startup accounts:")
        print("   1. TARAN - Email: taran@millow.com | Password: fastyk26tyr")
        print("   2. Test - Email: test@millow.com | Password: test123")

create_startup_accounts()

# ============ МОДЕЛИ ============
class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ChatCreate(BaseModel):
    participantId: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None

# ============ HTML ============
HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no">
    <title>Millow Messenger ✨</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: radial-gradient(circle at top left, #0f0c29, #1a183f, #0b0a1a);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 12px;
            margin: 0;
        }

        /* Стеклянный контейнер */
        .glass-container {
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
        }

        /* общие карточки с блюром */
        .glass-card {
            background: rgba(20, 24, 40, 0.55);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border-radius: 32px;
            border: 1px solid rgba(139, 92, 246, 0.2);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3), 0 0 0 0.5px rgba(255, 255, 255, 0.05) inset;
            transition: all 0.2s ease;
        }

        /* шапка */
        .neon-header {
            text-align: center;
            margin-bottom: 20px;
        }

        .neon-header h1 {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #c084fc, #f472b6, #a855f7);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: -0.5px;
            text-shadow: 0 2px 10px rgba(139, 92, 246, 0.2);
        }

        .stats-line {
            font-size: 0.75rem;
            color: #a78bfa;
            background: rgba(0, 0, 0, 0.3);
            display: inline-block;
            padding: 4px 16px;
            border-radius: 60px;
            backdrop-filter: blur(4px);
        }

        /* общие инпуты */
        input, textarea {
            width: 100%;
            padding: 14px 18px;
            margin: 8px 0;
            background: rgba(15, 18, 30, 0.7);
            border: 1.5px solid rgba(139, 92, 246, 0.4);
            border-radius: 28px;
            color: #f0f0ff;
            font-size: 15px;
            outline: none;
            transition: all 0.2s;
            font-weight: 500;
        }

        input:focus, textarea:focus {
            border-color: #c084fc;
            box-shadow: 0 0 0 3px rgba(192, 132, 252, 0.25);
            background: rgba(20, 24, 45, 0.9);
        }

        button {
            padding: 10px 22px;
            background: linear-gradient(110deg, #8b5cf6, #7c3aed);
            border: none;
            border-radius: 44px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
            font-size: 14px;
            letter-spacing: 0.3px;
            backdrop-filter: blur(4px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        button:active { transform: scale(0.96); }
        button:hover { filter: brightness(1.05); transform: translateY(-1px); }

        button.secondary {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(139, 92, 246, 0.5);
        }

        button.danger {
            background: linear-gradient(110deg, #ef4444, #b91c1c);
        }

        button.demo {
            background: rgba(139, 92, 246, 0.25);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 8px 18px;
            font-size: 13px;
        }

        .hidden { display: none !important; }
        .flex { display: flex; gap: 12px; flex-wrap: wrap; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; }
        .items-center { align-items: center; }
        .mt-2 { margin-top: 8px; }
        .mt-4 { margin-top: 20px; }
        .mb-2 { margin-bottom: 8px; }
        .mb-4 { margin-bottom: 20px; }
        .text-center { text-align: center; }
        .text-gray { color: #a0a3c0; }
        .text-green { color: #4ade80; }
        .text-red { color: #f87171; }

        /* аватарки */
        .avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid rgba(139, 92, 246, 0.6);
            background: #1e1a3a;
        }
        .avatar-lg {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid #a855f7;
            box-shadow: 0 0 20px rgba(168, 85, 247, 0.5);
        }
        /* юзер-айтемы */
        .user-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 14px;
            background: rgba(25, 30, 50, 0.5);
            border-radius: 28px;
            cursor: pointer;
            margin: 8px 0;
            transition: all 0.2s;
            backdrop-filter: blur(4px);
            border: 1px solid transparent;
        }
        .user-item:hover, .user-item.active {
            background: rgba(139, 92, 246, 0.35);
            border-color: rgba(168, 85, 247, 0.5);
            transform: translateX(6px);
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        .online { background: #10b981; box-shadow: 0 0 6px #10b981; }
        .offline { background: #6b7280; }

        /* сетка для десктоп/мобайл */
        .messenger-grid {
            display: flex;
            gap: 18px;
            flex-wrap: wrap;
        }
        .chats-sidebar {
            flex: 1.2;
            min-width: 260px;
        }
        .chat-main {
            flex: 2.5;
            min-width: 280px;
        }
        .chat-area {
            height: 380px;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 28px;
            margin-bottom: 12px;
        }
        .message {
            padding: 10px 16px;
            border-radius: 26px;
            max-width: 80%;
            word-wrap: break-word;
            animation: fadeSlide 0.25s ease;
            backdrop-filter: blur(2px);
        }
        .message.own {
            background: linear-gradient(120deg, #8b5cf6, #6d28d9);
            align-self: flex-end;
            border-bottom-right-radius: 8px;
            color: white;
        }
        .message.other {
            background: rgba(45, 50, 80, 0.8);
            align-self: flex-start;
            border-bottom-left-radius: 8px;
            border-left: 2px solid #a78bfa;
        }
        .message-sender {
            font-size: 11px;
            opacity: 0.7;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .message-time {
            font-size: 9px;
            opacity: 0.6;
            margin-top: 5px;
            text-align: right;
        }
        @keyframes fadeSlide {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* вкладки мобильные красивые */
        .mobile-tabs {
            display: flex;
            gap: 8px;
            background: rgba(0, 0, 0, 0.3);
            padding: 6px;
            border-radius: 60px;
            margin-bottom: 20px;
            backdrop-filter: blur(12px);
        }
        .tab-mob {
            flex: 1;
            text-align: center;
            padding: 8px;
            border-radius: 40px;
            font-weight: 600;
            background: transparent;
            box-shadow: none;
        }
        .tab-mob.active {
            background: linear-gradient(110deg, #8b5cf6, #7c3aed);
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        /* адаптив */
        @media (max-width: 760px) {
            body { padding: 8px; }
            .messenger-grid { flex-direction: column; }
            .chats-sidebar { order: 2; }
            .chat-main { order: 1; }
            .glass-card { border-radius: 24px; padding: 16px; }
            .chat-area { height: 460px; }
            .message { max-width: 90%; }
            button { padding: 8px 16px; }
        }

        @media (min-width: 1024px) {
            .messenger-grid { flex-wrap: nowrap; }
            .chats-sidebar { max-width: 340px; }
        }

        /* скролл стильный */
        ::-webkit-scrollbar {
            width: 5px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb {
            background: #a855f7;
            border-radius: 10px;
        }
    </style>
</head>
<body>
<div class="glass-container">
    <div class="neon-header">
        <h1>✨ Millow</h1>
        <span class="stats-line" id="stats">🔄 загрузка...</span>
    </div>

    <!-- АВТОРИЗАЦИЯ -->
    <div id="authScreen" class="glass-card" style="padding: 28px 20px; max-width: 480px; margin: 0 auto;">
        <h2 class="mb-4 text-center" id="authTitle">🔐 Вход</h2>
        <div class="flex" style="justify-content: center; gap: 12px; margin-bottom: 20px;">
            <button class="demo" onclick="quickLogin('taran@millow.com','fastyk26tyr')">⚡ TARAN</button>
            <button class="demo" onclick="quickLogin('test@millow.com','test123')">🧪 Test</button>
        </div>
        <div class="text-center text-gray mb-2" style="font-size:12px">или вручную</div>
        <input type="text" id="regName" placeholder="Имя (при регистрации)" class="hidden">
        <input type="email" id="email" placeholder="Email" autocomplete="email">
        <input type="password" id="password" placeholder="Пароль">
        <div class="flex mt-4">
            <button id="authBtn" style="flex:1">Войти</button>
            <button id="toggleBtn" class="secondary" style="flex:1">Создать аккаунт</button>
        </div>
        <p id="authError" class="text-red text-center mt-2"></p>
    </div>

    <!-- ОСНОВНОЙ ИНТЕРФЕЙС -->
    <div id="appScreen" class="hidden">
        <!-- мобильные табы (адаптивные) -->
        <div class="mobile-tabs" id="tabBar">
            <button class="tab-mob active" data-tab="chats">💬 Чаты</button>
            <button class="tab-mob" data-tab="users">👥 Люди</button>
            <button class="tab-mob" data-tab="profile">👤 Профиль</button>
            <button class="tab-mob danger" id="logoutBtnMobile">🚪</button>
        </div>

        <!-- панель Чатов (десктоп + мобила) -->
        <div id="chatsTab" class="tab-pane">
            <div class="messenger-grid">
                <div class="chats-sidebar glass-card" style="padding: 16px;">
                    <h3 class="mb-2">📋 Диалоги</h3>
                    <div id="chatsList" style="max-height: 480px; overflow-y: auto;"></div>
                </div>
                <div class="chat-main glass-card" style="padding: 16px;">
                    <div class="flex-between mb-2">
                        <h3 id="chatTitle">💭 Выберите чат</h3>
                    </div>
                    <div class="chat-area" id="chatArea">
                        <div class="text-gray text-center mt-4">✨ Нажмите на диалог или пользователя</div>
                    </div>
                    <div class="flex" style="margin-top: 12px;">
                        <input type="text" id="messageInput" placeholder="Сообщение..." style="flex:1" onkeypress="if(event.key==='Enter') sendMessage()">
                        <button onclick="sendMessage()">📤</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Люди -->
        <div id="usersTab" class="tab-pane hidden glass-card" style="padding: 20px;">
            <h3>👥 Все участники</h3>
            <input type="text" id="userSearch" placeholder="🔍 Поиск по имени..." onkeyup="filterUsers()" style="margin: 12px 0;">
            <div id="usersList" style="max-height: 500px; overflow-y: auto;"></div>
        </div>

        <!-- Профиль -->
        <div id="profileTab" class="tab-pane hidden glass-card" style="padding: 24px;">
            <h2 class="mb-4">🎨 Редактировать</h2>
            <div class="text-center mb-4">
                <img id="profileAvatar" class="avatar-lg" src="" alt="avatar">
                <div class="mt-2">
                    <input type="file" id="avatarFile" accept="image/*" style="display:none" onchange="uploadAvatar()">
                    <button onclick="document.getElementById('avatarFile').click()" class="secondary">📷 Загрузить фото</button>
                </div>
            </div>
            <label class="text-gray">Имя</label>
            <input type="text" id="profileName">
            <label class="text-gray">Email</label>
            <input type="email" id="profileEmail">
            <label class="text-gray">О себе</label>
            <textarea id="profileBio" rows="2"></textarea>
            <label class="text-gray">Телефон</label>
            <input type="tel" id="profilePhone">
            <div class="flex mt-4">
                <button onclick="updateProfile()">💾 Сохранить</button>
                <button onclick="showTab('chats')" class="secondary">Отмена</button>
            </div>
        </div>
    </div>
</div>

<script>
    // ----- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ -----
    const API = location.origin;
    let token = localStorage.getItem('mtoken');
    let user = JSON.parse(localStorage.getItem('muser') || 'null');
    let isLogin = true;
    let socket = null;
    let currentChat = null;
    let allUsers = [];
    let allChats = [];
    let reconnectAttempt = 0;
    let messagePollTimer = null;

    // ---- ИНИЦИАЛИЗАЦИЯ ----
    function init() {
        updateStats();
        if(token && user) {
            showApp();
            connectWebSocket();
            loadAllData();
            startSoftPolling();
        }
        setInterval(() => updateStats(), 15000);
    }

    async function updateStats() {
        try {
            const r = await fetch(API+'/api/health');
            const d = await r.json();
            document.getElementById('stats').innerHTML = `🟢 ${d.users} участников | ${d.chats} чатов`;
        } catch(e) { document.getElementById('stats').innerHTML = `⚠️ слабый сигнал`; }
    }

    // незаметное фоновое обновление (только если вебсокет не активен но все равно обновляем сообщения)
    function startSoftPolling() {
        if(messagePollTimer) clearInterval(messagePollTimer);
        messagePollTimer = setInterval(() => {
            if(currentChat && document.getElementById('chatsTab') && !document.getElementById('chatsTab').classList.contains('hidden')) {
                loadMessages(true); // silent refresh
            }
            loadChats(true); // фоном обновляем статусы и чаты
            loadUsersSilent();
        }, 2800);
    }

    async function loadUsersSilent() {
        if(!token) return;
        try {
            const r = await fetch(API+'/api/users', {headers:{'Authorization':'Bearer '+token}});
            if(r.ok) {
                allUsers = await r.json();
                if(document.getElementById('usersTab') && !document.getElementById('usersTab').classList.contains('hidden')) renderUsers();
            }
        } catch(e) {}
    }

    async function loadAllData() {
        await loadUsers();
        await loadChats();
    }

    // ----- АВТОРИЗАЦИЯ -----
    function quickLogin(email, password) {
        document.getElementById('email').value = email;
        document.getElementById('password').value = password;
        handleAuth();
    }

    function toggleAuth() {
        isLogin = !isLogin;
        document.getElementById('regName').classList.toggle('hidden', isLogin);
        document.getElementById('authTitle').innerText = isLogin ? '🔐 Вход' : '📝 Регистрация';
        document.getElementById('authBtn').innerText = isLogin ? 'Войти' : 'Зарегистрироваться';
        document.getElementById('toggleBtn').innerText = isLogin ? 'Создать аккаунт' : 'Назад ко входу';
        document.getElementById('authError').innerText = '';
    }

    async function handleAuth() {
        const email = document.getElementById('email').value.trim();
        const pwd = document.getElementById('password').value;
        const name = document.getElementById('regName').value.trim();
        if(!email || !pwd) { document.getElementById('authError').innerText = 'Заполните поля'; return; }
        if(!isLogin && !name) { document.getElementById('authError').innerText = 'Укажите имя'; return; }
        const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
        const body = isLogin ? {email, password: pwd} : {name, email, password: pwd};
        try {
            const r = await fetch(API+endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
            const d = await r.json();
            if(!r.ok) throw new Error(d.detail || 'Ошибка');
            token = d.token;
            user = d.user;
            localStorage.setItem('mtoken', token);
            localStorage.setItem('muser', JSON.stringify(user));
            showApp();
            connectWebSocket();
            loadAllData();
            startSoftPolling();
        } catch(e) { document.getElementById('authError').innerText = e.message; }
    }

    function showApp() {
        document.getElementById('authScreen').classList.add('hidden');
        document.getElementById('appScreen').classList.remove('hidden');
        showTab('chats');
    }

    // управление вкладками (мобильные и десктоп)
    function showTab(tabId) {
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
        document.getElementById(`${tabId}Tab`).classList.remove('hidden');
        document.querySelectorAll('.tab-mob').forEach(btn => {
            if(btn.getAttribute('data-tab') === tabId) btn.classList.add('active');
            else if(btn.getAttribute('data-tab')) btn.classList.remove('active');
        });
        if(tabId === 'users') { loadUsers(); renderUsers(); }
        if(tabId === 'profile') loadProfile();
        if(tabId === 'chats') loadChats();
    }

    function logout() {
        localStorage.clear();
        if(socket) socket.close();
        location.reload();
    }

    // чаты и загрузка
    async function loadChats(silent = false) {
        if(!token) return;
        try {
            const r = await fetch(API+'/api/chats', {headers:{'Authorization':'Bearer '+token}});
            if(r.ok) {
                allChats = await r.json();
                if(!silent) renderChats();
                else {
                    if(document.getElementById('chatsTab') && !document.getElementById('chatsTab').classList.contains('hidden')) renderChats();
                }
            }
        } catch(e) {}
    }

    function renderChats() {
        const container = document.getElementById('chatsList');
        if(!allChats.length) { container.innerHTML = '<div class="text-gray text-center">💬 Нет чатов, начните диалог</div>'; return; }
        container.innerHTML = '';
        allChats.forEach(chat => {
            if(!chat.otherUser) return;
            const div = document.createElement('div');
            div.className = 'user-item';
            if(currentChat && currentChat.id === chat.id) div.classList.add('active');
            div.innerHTML = `
                <img src="${chat.otherUser.avatar || 'https://ui-avatars.com/api/?name=User'}" class="avatar" onerror="this.src='https://ui-avatars.com/api/?background=8B5CF6&color=fff'">
                <div style="flex:1"><b>${escapeHtml(chat.otherUser.name)}</b><br><span class="text-sm text-gray">${chat.lastMessage?.content ? truncate(chat.lastMessage.content,35) : 'Нет сообщений'}</span></div>
                <span class="status-dot ${chat.otherUser.online ? 'online' : 'offline'}"></span>
            `;
            div.onclick = () => selectChat(chat);
            container.appendChild(div);
        });
    }

    async function loadUsers() {
        if(!token) return;
        try {
            const r = await fetch(API+'/api/users', {headers:{'Authorization':'Bearer '+token}});
            if(r.ok) {
                allUsers = await r.json();
                renderUsers();
            }
        } catch(e) {}
    }

    function renderUsers() {
        const listDiv = document.getElementById('usersList');
        if(!allUsers.length) { listDiv.innerHTML = '<div class="text-gray text-center">👀 Других пользователей нет</div>'; return; }
        listDiv.innerHTML = '';
        allUsers.forEach(u => {
            const item = document.createElement('div');
            item.className = 'user-item';
            item.innerHTML = `
                <img src="${u.avatar || 'https://ui-avatars.com/api/?name='+u.name}" class="avatar">
                <div style="flex:1"><b>${escapeHtml(u.name)}</b><br><span class="text-sm">${u.online ? '🟢 онлайн' : '⚫ офлайн'}</span></div>
                <button class="secondary" style="padding:6px 16px;" onclick="event.stopPropagation(); startChat('${u.id}')">💬</button>
            `;
            item.onclick = () => startChat(u.id);
            listDiv.appendChild(item);
        });
    }

    function filterUsers() {
        const query = document.getElementById('userSearch').value.toLowerCase();
        const filtered = allUsers.filter(u => u.name.toLowerCase().includes(query) || u.email.toLowerCase().includes(query));
        const listDiv = document.getElementById('usersList');
        listDiv.innerHTML = '';
        filtered.forEach(u => {
            const div = document.createElement('div');
            div.className = 'user-item';
            div.innerHTML = `<img src="${u.avatar}" class="avatar"><div><b>${escapeHtml(u.name)}</b><br><span class="text-sm">${u.email}</span></div>`;
            div.onclick = () => startChat(u.id);
            listDiv.appendChild(div);
        });
    }

    async function startChat(otherUserId) {
        try {
            const r = await fetch(API+'/api/chats', {
                method:'POST',
                headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
                body:JSON.stringify({participantId: otherUserId})
            });
            const chat = await r.json();
            selectChat(chat);
            showTab('chats');
        } catch(e) { console.warn(e); }
    }

    function selectChat(chat) {
        currentChat = chat;
        document.getElementById('chatTitle').innerHTML = `💬 ${chat.otherUser?.name || 'Диалог'}`;
        document.getElementById('chatArea').innerHTML = '<div class="text-gray text-center">⏳ загрузка...</div>';
        loadMessages();
        renderChats();
    }

    async function loadMessages(silent = false) {
        if(!currentChat) return;
        try {
            const r = await fetch(API+'/api/messages/'+currentChat.id, {headers:{'Authorization':'Bearer '+token}});
            const msgs = await r.json();
            const area = document.getElementById('chatArea');
            if(!msgs.length) { area.innerHTML = '<div class="text-gray text-center mt-4">💭 Напишите первое сообщение ✨</div>'; return; }
            area.innerHTML = '';
            msgs.forEach(m => {
                const isOwn = m.senderId === user.id;
                const div = document.createElement('div');
                div.className = `message ${isOwn ? 'own' : 'other'}`;
                div.innerHTML = `
                    ${!isOwn ? `<div class="message-sender">${escapeHtml(m.sender?.name || 'Unknown')}</div>` : ''}
                    ${escapeHtml(m.content)}
                    <div class="message-time">${new Date(m.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>
                `;
                area.appendChild(div);
            });
            area.scrollTop = area.scrollHeight;
        } catch(e) {}
    }

    async function sendMessage() {
        const input = document.getElementById('messageInput');
        const content = input.value.trim();
        if(!content || !currentChat) return;
        input.value = '';
        // оптимистичное добавление локально (мгновенно)
        const tempMsg = {
            id: 'temp'+Date.now(),
            chatId: currentChat.id,
            senderId: user.id,
            content: content,
            sender: { name: user.name, avatar: user.avatar },
            timestamp: new Date().toISOString()
        };
        // визуально добавим временно
        const area = document.getElementById('chatArea');
        const tempDiv = document.createElement('div');
        tempDiv.className = 'message own';
        tempDiv.innerHTML = `${escapeHtml(content)}<div class="message-time">⌛️ отправка...</div>`;
        area.appendChild(tempDiv);
        area.scrollTop = area.scrollHeight;

        if(socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type:'private-message', chatId:currentChat.id, senderId:user.id, content }));
        } else {
            // резерв HTTP
            try {
                await fetch(API+'/api/messages/reserve', {method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify({chatId:currentChat.id, content})});
            } catch(e) {}
        }
        setTimeout(() => { loadMessages(); loadChats(true); }, 400);
    }

    // профиль
    function loadProfile() {
        document.getElementById('profileAvatar').src = user.avatar || `https://ui-avatars.com/api/?name=${user.name}&background=8B5CF6&color=fff`;
        document.getElementById('profileName').value = user.name || '';
        document.getElementById('profileEmail').value = user.email || '';
        document.getElementById('profileBio').value = user.bio || '';
        document.getElementById('profilePhone').value = user.phone || '';
    }
    async function updateProfile() {
        const body = {
            name: document.getElementById('profileName').value,
            email: document.getElementById('profileEmail').value,
            bio: document.getElementById('profileBio').value,
            phone: document.getElementById('profilePhone').value
        };
        try {
            const r = await fetch(API+'/api/users/profile', {method:'PUT',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify(body)});
            if(r.ok) {
                user = await r.json();
                localStorage.setItem('muser', JSON.stringify(user));
                alert('✅ Профиль обновлён');
                showTab('chats');
            }
        } catch(e) { alert('Ошибка'); }
    }
    async function uploadAvatar() {
        const file = document.getElementById('avatarFile').files[0];
        if(!file) return;
        const fd = new FormData();
        fd.append('avatar', file);
        try {
            const r = await fetch(API+'/api/users/avatar', {method:'POST',headers:{'Authorization':'Bearer '+token}, body:fd});
            if(r.ok) {
                const d = await r.json();
                user.avatar = API + d.url;
                localStorage.setItem('muser', JSON.stringify(user));
                document.getElementById('profileAvatar').src = user.avatar;
                alert('✨ Аватар обновлён');
            }
        } catch(e) { alert('Не удалось загрузить'); }
    }

    // WEBSOCKET с автореконнектом (незаметно)
    function connectWebSocket() {
        if(!token || !user) return;
        try {
            const proto = location.protocol === 'https:' ? 'wss' : 'ws';
            socket = new WebSocket(`${proto}://${location.host}/ws`);
            socket.onopen = () => { 
                console.log('ws ready');
                socket.send(JSON.stringify({type:'login', userId: user.id}));
                reconnectAttempt = 0;
            };
            socket.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if(data.type === 'private-message') {
                    if(currentChat && data.chatId === currentChat.id) loadMessages();
                    loadChats(true);
                }
                if(data.type === 'user-status') {
                    loadUsersSilent();
                    loadChats(true);
                }
            };
            socket.onclose = () => {
                console.log('ws closed, silent reconnect');
                setTimeout(() => connectWebSocket(), 2000);
            };
            socket.onerror = () => { socket?.close(); };
        } catch(e) { setTimeout(() => connectWebSocket(), 3000); }
    }

    // функция для безопасного escape
    function escapeHtml(str) { if(!str) return ''; return str.replace(/[&<>]/g, function(m){if(m==='&') return '&amp;'; if(m==='<') return '&lt;'; if(m==='>') return '&gt;'; return m;}); }
    function truncate(txt, len) { if(!txt) return ''; return txt.length>len ? txt.slice(0,len)+'…' : txt; }

    // биндинги кнопок
    document.getElementById('toggleBtn')?.addEventListener('click', toggleAuth);
    document.getElementById('authBtn')?.addEventListener('click', handleAuth);
    document.querySelectorAll('.tab-mob').forEach(btn => {
        const tab = btn.getAttribute('data-tab');
        if(tab) btn.addEventListener('click', () => showTab(tab));
    });
    document.getElementById('logoutBtnMobile')?.addEventListener('click', logout);
    window.showTab = showTab;
    window.sendMessage = sendMessage;
    window.startChat = startChat;
    window.filterUsers = filterUsers;
    window.updateProfile = updateProfile;
    window.uploadAvatar = uploadAvatar;
    window.quickLogin = quickLogin;
    window.logout = logout;
    window.toggleAuth = toggleAuth;
    window.handleAuth = handleAuth;

    init();
</script>
</body>
</html>"""

# ============ API ============

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "users": len(users_db),
        "chats": len(chats_db),
        "messages": len(messages_db),
        "online": len(online_users)
    }

@app.post("/api/auth/register")
async def register(data: UserRegister):
    for u in users_db.values():
        if u["email"] == data.email:
            raise HTTPException(400, "User already exists")
    
    uid = str(uuid.uuid4())
    users_db[uid] = {
        "id": uid,
        "name": data.name,
        "email": data.email,
        "password": hash_password(data.password),
        "avatar": f"https://ui-avatars.com/api/?name={data.name}&background=8B5CF6&color=fff&size=200&bold=true",
        "bio": "Hey there! I'm using Millow 💜",
        "phone": "",
        "online": False,
        "lastSeen": datetime.utcnow().isoformat(),
        "createdAt": datetime.utcnow().isoformat()
    }
    
    token = create_token(uid)
    return {"token": token, "user": {k:v for k,v in users_db[uid].items() if k != "password"}}

@app.post("/api/auth/login")
async def login(data: UserLogin):
    user = next((u for u in users_db.values() if u["email"] == data.email), None)
    hashed = hash_password(data.password)
    
    if not user or user["password"] != hashed:
        raise HTTPException(401, "Invalid email or password")
    
    token = create_token(user["id"])
    return {"token": token, "user": {k:v for k,v in user.items() if k != "password"}}

@app.get("/api/users")
async def get_users(authorization: str = Header(None)):
    if not authorization: raise HTTPException(401)
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401)
    
    return [{k:v for k,v in u.items() if k!="password"} 
            for u in users_db.values() if u["id"] != payload["user_id"]]

@app.get("/api/chats")
async def get_chats(authorization: str = Header(None)):
    if not authorization: raise HTTPException(401)
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401)
    
    result = []
    for c in chats_db.values():
        if payload["user_id"] in c["participants"]:
            other_id = next((p for p in c["participants"] if p != payload["user_id"]), None)
            other_user = users_db.get(other_id, {})
            result.append({
                **c,
                "otherUser": {k:v for k,v in other_user.items() if k!="password"} if other_user else None
            })
    
    return sorted(result, key=lambda x: x.get("updatedAt", ""), reverse=True)

@app.post("/api/chats")
async def create_chat(data: ChatCreate, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401)
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401)
    
    # Ищем существующий чат
    for c in chats_db.values():
        if (payload["user_id"] in c["participants"] and 
            data.participantId in c["participants"]):
            other = users_db.get(data.participantId, {})
            return {**c, "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None}
    
    # Создаем новый чат
    cid = str(uuid.uuid4())
    chats_db[cid] = {
        "id": cid,
        "participants": [payload["user_id"], data.participantId],
        "isGroup": False,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
        "lastMessage": None
    }
    
    other = users_db.get(data.participantId, {})
    return {
        **chats_db[cid],
        "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None
    }

@app.get("/api/messages/{chat_id}")
async def get_messages(chat_id: str, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401)
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401)
    
    result = []
    for m in messages_db:
        if m["chatId"] == chat_id:
            sender = users_db.get(m["senderId"], {})
            result.append({
                **m,
                "sender": {k:v for k,v in sender.items() if k!="password"} if sender else None
            })
    
    return sorted(result, key=lambda x: x["timestamp"])

@app.put("/api/users/profile")
async def update_profile(data: UserUpdate, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401)
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401)
    
    u = users_db.get(payload["user_id"])
    if not u: raise HTTPException(404)
    
    for field in ["name", "email", "bio", "phone", "avatar"]:
        val = getattr(data, field, None)
        if val is not None:
            u[field] = val
    
    return {k:v for k,v in u.items() if k!="password"}

@app.post("/api/users/avatar")
async def upload_avatar(avatar: UploadFile = File(...), authorization: str = Header(None)):
    if not authorization: raise HTTPException(401)
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401)
    
    os.makedirs("uploads/avatars", exist_ok=True)
    
    ext = os.path.splitext(avatar.filename)[1] if avatar.filename else ".jpg"
    fname = f"{payload['user_id']}_{uuid.uuid4().hex[:8]}{ext}"
    fpath = f"uploads/avatars/{fname}"
    
    with open(fpath, "wb") as f:
        f.write(await avatar.read())
    
    url = f"/uploads/avatars/{fname}"
    if payload["user_id"] in users_db:
        users_db[payload["user_id"]]["avatar"] = url
    
    return {"url": url}

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    uid = None
    
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            
            if data.get("type") == "login":
                uid = data["userId"]
                online_users[uid] = websocket
                
                if uid in users_db:
                    users_db[uid]["online"] = True
                    users_db[uid]["lastSeen"] = datetime.utcnow().isoformat()
                
                for u_id, ws in online_users.items():
                    if u_id != uid:
                        try:
                            await ws.send_text(json.dumps({
                                "type": "user-status",
                                "userId": uid,
                                "online": True
                            }))
                        except:
                            pass
            
            elif data.get("type") == "private-message":
                msg = {
                    "id": str(uuid.uuid4()),
                    "chatId": data["chatId"],
                    "senderId": data["senderId"],
                    "content": data["content"],
                    "type": "text",
                    "timestamp": datetime.utcnow().isoformat(),
                    "read": False
                }
                
                messages_db.append(msg)
                
                if data["chatId"] in chats_db:
                    chats_db[data["chatId"]]["lastMessage"] = msg
                    chats_db[data["chatId"]]["updatedAt"] = datetime.utcnow().isoformat()
                
                sender = users_db.get(data["senderId"], {})
                msg_with_sender = {
                    **msg,
                    "sender": {k:v for k,v in sender.items() if k!="password"} if sender else None
                }
                
                # Отправляем получателю
                if data["chatId"] in chats_db:
                    for pid in chats_db[data["chatId"]]["participants"]:
                        if pid != data["senderId"] and pid in online_users:
                            try:
                                await online_users[pid].send_text(
                                    json.dumps({"type": "private-message", **msg_with_sender})
                                )
                            except:
                                pass
                
                # Отправляем отправителю подтверждение
                await websocket.send_text(
                    json.dumps({"type": "private-message", **msg_with_sender})
                )
    
    except Exception:
        pass
    finally:
        if uid and uid in online_users:
            del online_users[uid]
            if uid in users_db:
                users_db[uid]["online"] = False
                users_db[uid]["lastSeen"] = datetime.utcnow().isoformat()
            
            for u_id, ws in online_users.items():
                try:
                    await ws.send_text(json.dumps({
                        "type": "user-status",
                        "userId": uid,
                        "online": False
                    }))
                except:
                    pass

# ============ ЗАПУСК ============
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    print(f"""
╔══════════════════════════════════════════╗
║         💬 Millow Messenger             ║
║         Server Starting...              ║
║         Port: {port}                       ║
║         Users: {len(users_db)}                         ║
╚══════════════════════════════════════════╝
    """)
    print("📧 Demo accounts:")
    print("   1. TARAN - taran@millow.com / fastyk26tyr")
    print("   2. Test - test@millow.com / test123")
    uvicorn.run(app, host="0.0.0.0", port=port)