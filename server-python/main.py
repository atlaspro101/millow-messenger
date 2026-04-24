from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os
import uuid
import hashlib

app = FastAPI(title="Millow Messenger")

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Папки
for d in ["data", "uploads", "uploads/avatars"]:
    os.makedirs(d, exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ============ ДАННЫЕ ============
SECRET_KEY = "millow_secret_2024"
users_db = {}
chats_db = {}
messages_db = []
online_users = {}
tokens = {}

def hash_password(password):
    return hashlib.sha256((password + SECRET_KEY).encode()).hexdigest()

def create_token(user_id):
    token = str(uuid.uuid4())
    tokens[token] = {"user_id": user_id}
    return token

def verify_token(token):
    return tokens.get(token)

# Стартовые аккаунты
def create_startup_accounts():
    if len(users_db) == 0:
        users_db["startup_1"] = {
            "id": "startup_1", "name": "TARAN", "email": "taran@millow.com",
            "password": hash_password("fastyk26tyr"),
            "avatar": "https://ui-avatars.com/api/?name=TARAN&background=8B5CF6&color=fff&size=200&bold=true",
            "bio": "Hey there! I'm using Millow 💜", "phone": "", "online": False,
            "lastSeen": datetime.utcnow().isoformat(), "createdAt": datetime.utcnow().isoformat()
        }
        users_db["startup_2"] = {
            "id": "startup_2", "name": "Test", "email": "test@millow.com",
            "password": hash_password("test123"),
            "avatar": "https://ui-avatars.com/api/?name=TEST&background=EC4899&color=fff&size=200&bold=true",
            "bio": "Just testing Millow messenger", "phone": "", "online": False,
            "lastSeen": datetime.utcnow().isoformat(), "createdAt": datetime.utcnow().isoformat()
        }
        print("✅ Startup accounts: TARAN / Test")

create_startup_accounts()

# Модели
class UserRegister(BaseModel):
    name: str; email: str; password: str

class UserLogin(BaseModel):
    email: str; password: str

class ChatCreate(BaseModel):
    participantId: str

class UserUpdate(BaseModel):
    name: Optional[str] = None; email: Optional[str] = None; bio: Optional[str] = None
    phone: Optional[str] = None; avatar: Optional[str] = None

# ============ HTML ============
HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Millow Messenger</title>
    <style>
        :root {
            --bg: #0f0c29;
            --glass: rgba(31, 41, 55, 0.4);
            --glass2: rgba(55, 65, 81, 0.3);
            --border: rgba(255, 255, 255, 0.08);
            --accent: #8b5cf6;
            --accent2: #ec4899;
            --text: #fff;
            --text2: #9ca3af;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }

        /* Анимированный фон */
        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 20% 50%, rgba(139, 92, 246, 0.15), transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(236, 72, 153, 0.1), transparent 50%),
                radial-gradient(circle at 40% 20%, rgba(139, 92, 246, 0.1), transparent 50%);
            animation: bgMove 20s ease infinite;
            z-index: 0;
            pointer-events: none;
        }

        @keyframes bgMove {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }

        /* Стеклянные эффекты */
        .glass {
            background: rgba(31, 41, 55, 0.3);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .glass-strong {
            background: rgba(31, 41, 55, 0.5);
            backdrop-filter: blur(30px) saturate(180%);
            -webkit-backdrop-filter: blur(30px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
        }

        /* Общие стили */
        .app-container {
            position: relative;
            z-index: 1;
            min-height: 100vh;
        }

        input, textarea {
            width: 100%;
            padding: 14px 18px;
            margin: 6px 0;
            background: rgba(55, 65, 81, 0.4);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            color: #fff;
            font-size: 15px;
            outline: none;
            transition: all 0.3s;
        }

        input:focus, textarea:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2);
        }

        textarea { resize: none; }

        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, var(--accent), #7c3aed);
            border: none;
            border-radius: 50px;
            color: #fff;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
            position: relative;
            overflow: hidden;
        }

        button::before {
            content: '';
            position: absolute;
            top: 0; left: -100%;
            width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }

        button:hover::before { left: 100%; }
        button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4); }
        button:active { transform: scale(0.95); }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .btn-danger {
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }

        .btn-demo {
            background: rgba(139, 92, 246, 0.2);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(139, 92, 246, 0.3);
            font-size: 13px;
            padding: 10px 20px;
        }

        /* Аватарки с эффектом */
        .avatar {
            width: 48px; height: 48px;
            border-radius: 16px;
            object-fit: cover;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
        }

        .avatar-lg {
            width: 100px; height: 100px;
            border-radius: 28px;
            object-fit: cover;
            box-shadow: 0 8px 30px rgba(139, 92, 246, 0.4);
        }

        .status-dot {
            width: 10px; height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 4px;
        }
        .online { background: #10b981; box-shadow: 0 0 10px #10b981; }
        .offline { background: #6b7280; }

        /* Сообщения */
        .message {
            padding: 12px 18px;
            border-radius: 20px;
            max-width: 75%;
            word-wrap: break-word;
            animation: msgSlide 0.3s ease;
        }

        .message.own {
            background: linear-gradient(135deg, var(--accent), #7c3aed);
            align-self: flex-end;
            border-bottom-right-radius: 6px;
        }

        .message.other {
            background: rgba(55, 65, 81, 0.5);
            backdrop-filter: blur(10px);
            align-self: flex-start;
            border-bottom-left-radius: 6px;
        }

        @keyframes msgSlide {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .hidden { display: none !important; }

        /* ============ ДЕСКТОП (>= 769px) ============ */
        @media (min-width: 769px) {
            .desktop-layout {
                display: flex;
                min-height: 100vh;
                padding: 20px;
                gap: 20px;
            }

            .sidebar-pc {
                width: 350px;
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            .main-pc {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            .chat-list-pc {
                flex: 1;
                overflow-y: auto;
                border-radius: 24px;
                padding: 20px;
            }

            .chat-area-pc {
                flex: 1;
                overflow-y: auto;
                border-radius: 24px;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .user-item {
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 14px;
                margin: 4px 0;
                background: rgba(55,65,81,0.2);
                backdrop-filter: blur(10px);
                border-radius: 18px;
                cursor: pointer;
                transition: all 0.2s;
                border: 1px solid transparent;
            }

            .user-item:hover {
                background: rgba(139,92,246,0.2);
                border-color: rgba(139,92,246,0.3);
                transform: translateX(6px);
            }

            .user-item.active {
                background: rgba(139,92,246,0.3);
                border-color: rgba(139,92,246,0.5);
                box-shadow: 0 4px 20px rgba(139,92,246,0.2);
            }

            .auth-card {
                max-width: 450px;
                margin: 80px auto;
                padding: 40px;
                border-radius: 32px;
            }

            .header-title {
                font-size: 52px;
                background: linear-gradient(135deg, #a78bfa, #ec4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .mobile-only { display: none !important; }
        }

        /* ============ МОБИЛЬНЫЙ (< 768px) ============ */
        @media (max-width: 768px) {
            .desktop-layout {
                display: flex;
                flex-direction: column;
                min-height: 100vh;
                padding: 10px;
                gap: 8px;
            }

            .pc-only { display: none !important; }

            /* Мобильная навигация */
            .mobile-nav {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                display: flex;
                justify-content: space-around;
                padding: 10px;
                background: rgba(31, 41, 55, 0.6);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                z-index: 100;
            }

            .mobile-nav-btn {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
                padding: 8px 16px;
                background: transparent;
                border: none;
                color: #9ca3af;
                font-size: 11px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s;
            }

            .mobile-nav-btn .icon {
                font-size: 22px;
                transition: transform 0.3s;
            }

            .mobile-nav-btn.active {
                color: var(--accent);
            }

            .mobile-nav-btn.active .icon {
                transform: scale(1.2);
                text-shadow: 0 0 15px var(--accent);
            }

            /* Мобильный чат */
            .mobile-chat-list {
                flex: 1;
                overflow-y: auto;
                padding-bottom: 70px;
            }

            .mobile-chat-area {
                flex: 1;
                overflow-y: auto;
                padding-bottom: 70px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }

            .user-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 14px;
                margin: 6px 0;
                background: rgba(55,65,81,0.3);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.2s;
                border: 1px solid rgba(255,255,255,0.05);
            }

            .user-item:active {
                background: rgba(139,92,246,0.3);
                transform: scale(0.98);
            }

            .user-item.active {
                background: rgba(139,92,246,0.35);
                border-color: rgba(139,92,246,0.4);
            }

            /* Мобильное поле ввода */
            .mobile-input-bar {
                position: fixed;
                bottom: 65px;
                left: 10px;
                right: 10px;
                display: flex;
                gap: 8px;
                padding: 10px;
                background: rgba(31, 41, 55, 0.7);
                backdrop-filter: blur(20px);
                border-radius: 30px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                z-index: 99;
            }

            .mobile-input-bar input {
                padding: 12px 16px;
                font-size: 16px;
            }

            .mobile-input-bar button {
                padding: 10px 20px;
                font-size: 16px;
            }

            .auth-card {
                max-width: 100%;
                margin: 20px 10px;
                padding: 30px 20px;
                border-radius: 28px;
            }

            .header-title {
                font-size: 36px;
                background: linear-gradient(135deg, #a78bfa, #ec4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .message {
                max-width: 85%;
            }
        }

        /* Анимация появления */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .fade-in { animation: fadeIn 0.3s ease; }
    </style>
</head>
<body>
    <div class="app-container" id="appRoot">
        <!-- ============ АВТОРИЗАЦИЯ ============ -->
        <div id="authScreen">
            <div class="desktop-layout" style="align-items:center;justify-content:center;">
                <div class="auth-card glass-strong">
                    <div style="text-align:center;margin-bottom:30px;">
                        <h1 class="header-title">💬 Millow</h1>
                        <p style="color:#9ca3af;font-size:14px;margin-top:8px;" id="authSubtitle">Login to continue</p>
                    </div>

                    <div style="display:flex;gap:8px;justify-content:center;margin-bottom:20px;flex-wrap:wrap;">
                        <button class="btn-demo" onclick="quickLogin('taran@millow.com','fastyk26tyr')">
                            👤 TARAN
                        </button>
                        <button class="btn-demo" onclick="quickLogin('test@millow.com','test123')">
                            👤 Test
                        </button>
                    </div>

                    <div style="text-align:center;color:#6b7280;font-size:12px;margin-bottom:15px;">or manually</div>

                    <input type="text" id="regName" placeholder="Full Name" class="hidden">
                    <input type="email" id="email" placeholder="Email address" autocomplete="email">
                    <input type="password" id="password" placeholder="Password" autocomplete="current-password">

                    <div style="display:flex;gap:10px;margin-top:20px;">
                        <button onclick="handleAuth()" id="authBtn" style="flex:1;">Login</button>
                        <button onclick="toggleAuth()" id="toggleBtn" class="btn-secondary">Register</button>
                    </div>
                    <p id="authError" style="color:#ef4444;text-align:center;margin-top:12px;font-size:13px;"></p>
                </div>
            </div>
        </div>

        <!-- ============ ГЛАВНЫЙ ИНТЕРФЕЙС ============ -->
        <div id="appScreen" class="hidden">
            <!-- ДЕСКТОП -->
            <div class="desktop-layout pc-only">
                <div class="sidebar-pc">
                    <div class="glass-strong" style="padding:20px;border-radius:24px;text-align:center;">
                        <h1 style="font-size:28px;background:linear-gradient(135deg,#a78bfa,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">💬 Millow</h1>
                        <div style="display:flex;gap:8px;margin-top:15px;">
                            <button onclick="showTab('chats')" id="tabChatsPc" style="flex:1;font-size:12px;">Chats</button>
                            <button onclick="showTab('users')" id="tabUsersPc" class="btn-secondary" style="flex:1;font-size:12px;">Users</button>
                            <button onclick="showTab('profile')" id="tabProfilePc" class="btn-secondary" style="flex:1;font-size:12px;">Profile</button>
                        </div>
                    </div>
                    <div class="chat-list-pc glass" id="chatsListPc"></div>
                    <div style="padding:15px;display:flex;align-items:center;gap:12px;cursor:pointer;" onclick="showTab('profile')" class="glass-strong" id="userMini">
                        <img id="userMiniAvatar" class="avatar" src="">
                        <div style="flex:1;"><b id="userMiniName"></b><br><span style="color:#10b981;font-size:12px;">Online</span></div>
                        <button onclick="event.stopPropagation();logout();" class="btn-danger" style="padding:8px 14px;font-size:12px;">Logout</button>
                    </div>
                </div>

                <div class="main-pc">
                    <!-- Вкладка чатов -->
                    <div id="chatsTab">
                        <div class="glass-strong" style="padding:20px;border-radius:24px;display:flex;justify-content:space-between;align-items:center;">
                            <h2 id="chatTitlePc" style="font-size:20px;">Select a chat</h2>
                        </div>
                        <div class="chat-area-pc glass" id="chatAreaPc">
                            <p style="color:#9ca3af;text-align:center;margin-top:40px;">👋 Select a user from the list</p>
                        </div>
                        <div style="display:flex;gap:10px;margin-top:10px;" class="glass-strong" id="inputBarPc">
                            <input type="text" id="messageInputPc" placeholder="Type a message..." style="flex:1;" onkeypress="if(event.key==='Enter')sendMessage()">
                            <button onclick="sendMessage()">📤 Send</button>
                        </div>
                    </div>

                    <!-- Вкладка пользователей -->
                    <div id="usersTab" class="hidden">
                        <div class="glass-strong" style="padding:20px;border-radius:24px;">
                            <h2 style="font-size:20px;margin-bottom:15px;">All Users</h2>
                            <input type="text" placeholder="Search users..." onkeyup="filterUsers()" id="userSearchPc">
                            <div id="usersListPc" style="max-height:500px;overflow-y:auto;margin-top:10px;"></div>
                        </div>
                    </div>

                    <!-- Вкладка профиля -->
                    <div id="profileTab" class="hidden">
                        <div class="glass-strong" style="padding:30px;border-radius:24px;text-align:center;">
                            <h2 style="font-size:24px;margin-bottom:20px;">Edit Profile</h2>
                            <img id="profileAvatarPc" class="avatar-lg" src="">
                            <div style="margin:15px 0;">
                                <input type="file" id="avatarFilePc" accept="image/*" style="display:none;" onchange="uploadAvatar()">
                                <button onclick="document.getElementById('avatarFilePc').click()" class="btn-secondary">📷 Change Photo</button>
                            </div>
                            <input type="text" id="profileNamePc" placeholder="Name">
                            <input type="email" id="profileEmailPc" placeholder="Email">
                            <textarea id="profileBioPc" placeholder="Bio" rows="3"></textarea>
                            <input type="tel" id="profilePhonePc" placeholder="Phone">
                            <div style="display:flex;gap:10px;margin-top:20px;">
                                <button onclick="updateProfile()" style="flex:1;">💾 Save</button>
                                <button onclick="showTab('chats')" class="btn-secondary" style="flex:1;">Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- МОБИЛЬНЫЙ -->
            <div class="desktop-layout mobile-only">
                <div id="mobileContent" class="mobile-chat-list fade-in"></div>

                <!-- Мобильная навигация -->
                <div class="mobile-nav">
                    <button class="mobile-nav-btn active" onclick="showMobileTab('chats')" id="mobNavChats">
                        <span class="icon">💬</span> Chats
                    </button>
                    <button class="mobile-nav-btn" onclick="showMobileTab('users')" id="mobNavUsers">
                        <span class="icon">👥</span> Users
                    </button>
                    <button class="mobile-nav-btn" onclick="showMobileTab('profile')" id="mobNavProfile">
                        <span class="icon">👤</span> Profile
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API = location.origin;
        let token = localStorage.getItem('mtoken');
        let user = JSON.parse(localStorage.getItem('muser')||'null');
        let isLogin = true;
        let socket = null;
        let currentChat = null;
        let allUsers = [];
        let allChats = [];
        let isMobile = window.innerWidth <= 768;
        let currentMobileTab = 'chats';

        // Init
        if(token && user) { showApp(); connectWS(); }
        setInterval(() => { if(currentChat) loadMessages(); }, 2000);
        
        window.addEventListener('resize', () => {
            isMobile = window.innerWidth <= 768;
            if(token && user) renderAll();
        });

        function quickLogin(email, password) {
            document.getElementById('email').value = email;
            document.getElementById('password').value = password;
            handleAuth();
        }

        function toggleAuth() {
            isLogin = !isLogin;
            document.getElementById('regName').classList.toggle('hidden', isLogin);
            document.getElementById('authSubtitle').textContent = isLogin ? 'Login to continue' : 'Create account';
            document.getElementById('authBtn').textContent = isLogin ? 'Login' : 'Register';
            document.getElementById('toggleBtn').textContent = isLogin ? 'Create Account' : 'Back to Login';
            document.getElementById('authError').textContent = '';
        }

        async function handleAuth() {
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const name = document.getElementById('regName').value.trim();
            
            if(!email || !password) { document.getElementById('authError').textContent='Fill all fields'; return; }
            
            const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
            const body = isLogin ? {email,password} : {name,email,password};
            
            try {
                const r = await fetch(API+endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
                const d = await r.json();
                if(!r.ok) throw new Error(d.detail||'Error');
                token = d.token; user = d.user;
                localStorage.setItem('mtoken', token);
                localStorage.setItem('muser', JSON.stringify(user));
                showApp(); connectWS(); loadAll();
            } catch(e) { document.getElementById('authError').textContent = e.message; }
        }

        function showApp() {
            document.getElementById('authScreen').classList.add('hidden');
            document.getElementById('appScreen').classList.remove('hidden');
            updateUserMini();
            showTab('chats');
        }

        function updateUserMini() {
            try {
                document.getElementById('userMiniAvatar').src = user.avatar;
                document.getElementById('userMiniName').textContent = user.name;
            } catch(e) {}
        }

        function logout() {
            localStorage.clear();
            location.reload();
        }

        function showTab(tab) {
            ['chatsTab','usersTab','profileTab'].forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.add('hidden');
            });
            
            const tabEl = document.getElementById(tab+'Tab');
            if(tabEl) tabEl.classList.remove('hidden');
            
            if(tab==='users') loadUsers();
            if(tab==='profile') loadProfile();
            if(tab==='chats') loadChats();
        }

        function showMobileTab(tab) {
            currentMobileTab = tab;
            document.querySelectorAll('.mobile-nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('mobNav'+tab.charAt(0).toUpperCase()+tab.slice(1)).classList.add('active');
            renderMobile();
        }

        async function loadAll() { await loadUsers(); await loadChats(); }

        async function loadUsers() {
            try {
                const r = await fetch(API+'/api/users', {headers:{'Authorization':'Bearer '+token}});
                allUsers = await r.json();
                renderUsers();
            } catch(e) {}
        }

        function renderUsers() {
            const containerPc = document.getElementById('usersListPc');
            const html = allUsers.length ? allUsers.map(u => `
                <div class="user-item" onclick="startChat('${u.id}')">
                    <img src="${u.avatar}" class="avatar" onerror="this.src='https://ui-avatars.com/api/?name=${u.name}&background=8B5CF6&color=fff'">
                    <div style="flex:1;"><b>${u.name}</b><br><span style="color:#9ca3af;font-size:12px;"><span class="status-dot ${u.online?'online':'offline'}"></span>${u.online?'Online':'Offline'}</span></div>
                </div>
            `).join('') : '<p style="color:#9ca3af;text-align:center;">No users yet</p>';
            
            if(containerPc) containerPc.innerHTML = html;
        }

        function filterUsers() {
            const s = (document.getElementById('userSearchPc')?.value || '').toLowerCase();
            const container = document.getElementById('usersListPc');
            if(!container) return;
            
            const filtered = allUsers.filter(u => u.name.toLowerCase().includes(s));
            container.innerHTML = filtered.length ? filtered.map(u => `
                <div class="user-item" onclick="startChat('${u.id}')">
                    <img src="${u.avatar}" class="avatar">
                    <div style="flex:1;"><b>${u.name}</b><br><span style="color:#9ca3af;font-size:12px;">${u.email}</span></div>
                </div>
            `).join('') : '<p style="color:#9ca3af;text-align:center;">No users found</p>';
        }

        async function loadChats() {
            try {
                const r = await fetch(API+'/api/chats', {headers:{'Authorization':'Bearer '+token}});
                allChats = await r.json();
                renderChats();
            } catch(e) {}
        }

        function renderChats() {
            const containerPc = document.getElementById('chatsListPc');
            const html = allChats.length ? allChats.map(c => {
                if(!c.otherUser) return '';
                return `
                    <div class="user-item ${currentChat?.id===c.id?'active':''}" onclick="selectChat('${c.id}')">
                        <img src="${c.otherUser.avatar}" class="avatar">
                        <div style="flex:1;"><b>${c.otherUser.name}</b><br><span style="color:#9ca3af;font-size:12px;">${(c.lastMessage?.content||'No messages').substring(0,30)}</span></div>
                        <span class="status-dot ${c.otherUser.online?'online':'offline'}"></span>
                    </div>
                `;
            }).join('') : '<p style="color:#9ca3af;text-align:center;padding:20px;">No chats yet</p>';
            
            if(containerPc) containerPc.innerHTML = html;
            if(isMobile) renderMobile();
        }

        function renderMobile() {
            const content = document.getElementById('mobileContent');
            if(!content) return;
            
            if(currentMobileTab === 'chats') {
                content.innerHTML = allChats.length ? allChats.map(c => {
                    if(!c.otherUser) return '';
                    return `
                        <div class="user-item ${currentChat?.id===c.id?'active':''}" onclick="selectChat('${c.id}')">
                            <img src="${c.otherUser.avatar}" class="avatar">
                            <div style="flex:1;"><b>${c.otherUser.name}</b><br><span style="color:#9ca3af;font-size:12px;">${(c.lastMessage?.content||'No messages').substring(0,35)}</span></div>
                            <span class="status-dot ${c.otherUser.online?'online':'offline'}"></span>
                        </div>
                    `;
                }).join('') : '<p style="color:#9ca3af;text-align:center;padding:40px;">No chats yet</p>';
            } else if(currentMobileTab === 'users') {
                content.innerHTML = allUsers.length ? allUsers.map(u => `
                    <div class="user-item" onclick="startChat('${u.id}')">
                        <img src="${u.avatar}" class="avatar">
                        <div style="flex:1;"><b>${u.name}</b><br><span style="color:#9ca3af;font-size:12px;"><span class="status-dot ${u.online?'online':'offline'}"></span>${u.online?'Online':'Offline'}</span></div>
                    </div>
                `).join('') : '<p style="color:#9ca3af;text-align:center;padding:40px;">No users</p>';
            } else {
                content.innerHTML = `
                    <div class="glass-strong" style="padding:20px;text-align:center;margin-top:10px;">
                        <h2 style="margin-bottom:15px;">Profile</h2>
                        <img src="${user.avatar}" class="avatar-lg" onerror="this.src='https://ui-avatars.com/api/?name=U&background=8B5CF6&color=fff'">
                        <h3 style="margin:10px 0;">${user.name}</h3>
                        <p style="color:#9ca3af;">${user.email}</p>
                        <button onclick="logout()" class="btn-danger" style="margin-top:15px;width:100%;">Logout</button>
                    </div>
                `;
            }
        }

        async function startChat(uid) {
            try {
                const r = await fetch(API+'/api/chats', {method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify({participantId:uid})});
                currentChat = await r.json();
                selectChat(currentChat.id);
                if(!isMobile) showTab('chats');
            } catch(e) {}
        }

        function selectChat(chatId) {
            currentChat = allChats.find(c => c.id === chatId) || currentChat;
            if(!currentChat) return;
            
            const titlePc = document.getElementById('chatTitlePc');
            if(titlePc) titlePc.textContent = '💬 ' + (currentChat.otherUser?.name || 'Chat');
            
            loadMessages();
            renderChats();
        }

        async function loadMessages() {
            if(!currentChat) return;
            try {
                const r = await fetch(API+'/api/messages/'+currentChat.id, {headers:{'Authorization':'Bearer '+token}});
                const msgs = await r.json();
                
                const html = msgs.length ? msgs.map(m => {
                    const isOwn = m.senderId === user.id;
                    return `
                        <div class="message ${isOwn?'own':'other'}">
                            ${!isOwn ? `<div style="font-size:11px;color:rgba(255,255,255,0.5);margin-bottom:4px;">${m.sender?.name||''}</div>` : ''}
                            ${m.content}
                            <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:4px;text-align:right;">${new Date(m.timestamp).toLocaleTimeString()}</div>
                        </div>
                    `;
                }).join('') : '<p style="color:#9ca3af;text-align:center;">No messages yet 👋</p>';
                
                const areaPc = document.getElementById('chatAreaPc');
                if(areaPc) { areaPc.innerHTML = html; areaPc.scrollTop = areaPc.scrollHeight; }
                
                if(isMobile) {
                    const mobileContent = document.getElementById('mobileContent');
                    if(mobileContent && currentMobileTab==='chats') {
                        // Показываем область сообщений
                        const chatTitle = document.getElementById('chatTitlePc');
                        mobileContent.innerHTML = `
                            <div style="padding:10px;display:flex;justify-content:space-between;align-items:center;" class="glass-strong">
                                <b>${currentChat.otherUser?.name||'Chat'}</b>
                                <button onclick="showMobileTab('chats');currentChat=null;renderMobile();" class="btn-secondary" style="padding:6px 12px;font-size:12px;">← Back</button>
                            </div>
                            <div class="mobile-chat-area">${html}</div>
                            <div class="mobile-input-bar">
                                <input type="text" id="msgInputMob" placeholder="Message..." onkeypress="if(event.key==='Enter')sendMessageMobile()">
                                <button onclick="sendMessageMobile()">Send</button>
                            </div>
                        `;
                        setTimeout(() => {
                            const area = document.querySelector('.mobile-chat-area');
                            if(area) area.scrollTop = area.scrollHeight;
                        }, 100);
                    }
                }
            } catch(e) {}
        }

        function sendMessage() {
            const input = isMobile ? document.getElementById('msgInputMob') : document.getElementById('messageInputPc');
            if(!input) return;
            const content = input.value.trim();
            if(!content||!currentChat) return;
            input.value = '';
            
            if(socket && socket.readyState===WebSocket.OPEN) {
                socket.send(JSON.stringify({type:'private-message',chatId:currentChat.id,senderId:user.id,content}));
            }
            setTimeout(loadMessages, 500);
        }

        function sendMessageMobile() { sendMessage(); }

        function loadProfile() {
            const pc = {
                avatar: document.getElementById('profileAvatarPc'),
                name: document.getElementById('profileNamePc'),
                email: document.getElementById('profileEmailPc'),
                bio: document.getElementById('profileBioPc'),
                phone: document.getElementById('profilePhonePc')
            };
            
            if(pc.avatar) {
                pc.avatar.src = user.avatar;
                pc.name.value = user.name||'';
                pc.email.value = user.email||'';
                pc.bio.value = user.bio||'';
                pc.phone.value = user.phone||'';
            }
        }

        async function updateProfile() {
            const body = {
                name: document.getElementById('profileNamePc')?.value,
                email: document.getElementById('profileEmailPc')?.value,
                bio: document.getElementById('profileBioPc')?.value,
                phone: document.getElementById('profilePhonePc')?.value
            };
            
            try {
                const r = await fetch(API+'/api/users/profile', {method:'PUT',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify(body)});
                if(r.ok) {
                    user = await r.json();
                    localStorage.setItem('muser', JSON.stringify(user));
                    updateUserMini();
                    alert('✅ Profile saved!');
                    showTab('chats');
                }
            } catch(e) {}
        }

        async function uploadAvatar() {
            const file = document.getElementById('avatarFilePc')?.files[0];
            if(!file) return;
            const fd = new FormData(); fd.append('avatar', file);
            try {
                const r = await fetch(API+'/api/users/avatar', {method:'POST',headers:{'Authorization':'Bearer '+token},body:fd});
                if(r.ok) {
                    const d = await r.json();
                    user.avatar = API + d.url;
                    localStorage.setItem('muser', JSON.stringify(user));
                    updateUserMini();
                    document.getElementById('profileAvatarPc').src = user.avatar;
                    alert('✅ Avatar updated!');
                }
            } catch(e) {}
        }

        function renderAll() {
            loadAll();
            renderChats();
            renderUsers();
        }

        function connectWS() {
            if(!token||!user) return;
            try {
                const proto = location.protocol==='https:'?'wss':'ws';
                socket = new WebSocket(proto+'://'+location.host+'/ws');
                socket.onopen = () => socket.send(JSON.stringify({type:'login',userId:user.id}));
                socket.onmessage = (e) => {
                    const d = JSON.parse(e.data);
                    if(d.type==='private-message') { loadMessages(); loadChats(); }
                    if(d.type==='user-status') { loadUsers(); loadChats(); }
                };
                socket.onclose = () => setTimeout(connectWS, 3000);
            } catch(e) { setTimeout(connectWS, 3000); }
        }
    </script>
</body>
</html>"""

# ============ API (тот же что и раньше) ============
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.post("/api/auth/register")
async def register(data: UserRegister):
    for u in users_db.values():
        if u["email"] == data.email:
            raise HTTPException(400, "User already exists")
    uid = str(uuid.uuid4())
    users_db[uid] = {
        "id": uid, "name": data.name, "email": data.email,
        "password": hash_password(data.password),
        "avatar": f"https://ui-avatars.com/api/?name={data.name}&background=8B5CF6&color=fff&size=200&bold=true",
        "bio": "Hey there! I'm using Millow 💜", "phone": "",
        "online": False, "lastSeen": datetime.utcnow().isoformat(), "createdAt": datetime.utcnow().isoformat()
    }
    token = create_token(uid)
    return {"token": token, "user": {k:v for k,v in users_db[uid].items() if k!="password"}}

@app.post("/api/auth/login")
async def login(data: UserLogin):
    user = next((u for u in users_db.values() if u["email"] == data.email), None)
    if not user or user["password"] != hash_password(data.password):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user["id"])
    return {"token": token, "user": {k:v for k,v in user.items() if k!="password"}}

@app.get("/api/users")
async def get_users(authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    return [{k:v for k,v in u.items() if k!="password"} for u in users_db.values() if u["id"]!=payload["user_id"]]

@app.get("/api/chats")
async def get_chats(authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    result = []
    for c in chats_db.values():
        if payload["user_id"] in c["participants"]:
            other_id = next((p for p in c["participants"] if p!=payload["user_id"]), None)
            other = users_db.get(other_id, {})
            result.append({**c, "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None})
    return sorted(result, key=lambda x: x.get("updatedAt",""), reverse=True)

@app.post("/api/chats")
async def create_chat(data: ChatCreate, authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    for c in chats_db.values():
        if payload["user_id"] in c["participants"] and data.participantId in c["participants"]:
            other = users_db.get(data.participantId, {})
            return {**c, "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None}
    cid = str(uuid.uuid4())
    chats_db[cid] = {"id":cid,"participants":[payload["user_id"],data.participantId],"isGroup":False,"createdAt":datetime.utcnow().isoformat(),"updatedAt":datetime.utcnow().isoformat(),"lastMessage":None}
    other = users_db.get(data.participantId, {})
    return {**chats_db[cid], "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None}

@app.get("/api/messages/{chat_id}")
async def get_messages(chat_id: str, authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    result = []
    for m in messages_db:
        if m["chatId"]==chat_id:
            sender = users_db.get(m["senderId"], {})
            result.append({**m, "sender": {k:v for k,v in sender.items() if k!="password"} if sender else None})
    return sorted(result, key=lambda x: x["timestamp"])

@app.put("/api/users/profile")
async def update_profile(data: UserUpdate, authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    u = users_db.get(payload["user_id"])
    if not u: raise HTTPException(404)
    for f in ["name","email","bio","phone","avatar"]:
        v = getattr(data, f, None)
        if v is not None: u[f] = v
    return {k:v for k,v in u.items() if k!="password"}

@app.post("/api/users/avatar")
async def upload_avatar(avatar: UploadFile = File(...), authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    os.makedirs("uploads/avatars", exist_ok=True)
    ext = os.path.splitext(avatar.filename)[1] if avatar.filename else ".jpg"
    fname = f"{payload['user_id']}_{uuid.uuid4().hex[:8]}{ext}"
    with open(f"uploads/avatars/{fname}", "wb") as f:
        f.write(await avatar.read())
    url = f"/uploads/avatars/{fname}"
    if payload["user_id"] in users_db: users_db[payload["user_id"]]["avatar"] = url
    return {"url": url}

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    uid = None
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            if data.get("type")=="login":
                uid = data["userId"]
                online_users[uid] = websocket
                if uid in users_db: users_db[uid]["online"] = True
                for u_id, ws in online_users.items():
                    if u_id!=uid:
                        try: await ws.send_text(json.dumps({"type":"user-status","userId":uid,"online":True}))
                        except: pass
            elif data.get("type")=="private-message":
                msg = {"id":str(uuid.uuid4()),"chatId":data["chatId"],"senderId":data["senderId"],"content":data["content"],"type":"text","timestamp":datetime.utcnow().isoformat(),"read":False}
                messages_db.append(msg)
                if data["chatId"] in chats_db:
                    chats_db[data["chatId"]]["lastMessage"] = msg
                    chats_db[data["chatId"]]["updatedAt"] = datetime.utcnow().isoformat()
                sender = users_db.get(data["senderId"], {})
                msg_s = {**msg, "sender": {k:v for k,v in sender.items() if k!="password"} if sender else None}
                if data["chatId"] in chats_db:
                    for pid in chats_db[data["chatId"]]["participants"]:
                        if pid!=data["senderId"] and pid in online_users:
                            try: await online_users[pid].send_text(json.dumps({"type":"private-message",**msg_s}))
                            except: pass
                await websocket.send_text(json.dumps({"type":"private-message",**msg_s}))
    except: pass
    finally:
        if uid and uid in online_users:
            del online_users[uid]
            if uid in users_db: users_db[uid]["online"] = False
            for u_id, ws in online_users.items():
                try: await ws.send_text(json.dumps({"type":"user-status","userId":uid,"online":False}))
                except: pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    print(f"✅ Millow on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)