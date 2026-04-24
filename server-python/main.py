from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import json
import os
import uuid
import sys
import traceback

# Настройка логирования
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Millow Messenger")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация
SECRET_KEY = os.getenv("JWT_SECRET", "millow_secret_key_2024")
ALGORITHM = "HS256"

# Проверка bcrypt
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Тест хеширования
    test_hash = pwd_context.hash("test")
    logger.info("✅ Bcrypt working")
except Exception as e:
    logger.error(f"❌ Bcrypt error: {e}")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Создание папок
for directory in ["data", "uploads", "uploads/avatars", "static"]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"📁 Directory ready: {directory}")

# Загрузка или создание файлов данных
def load_json(filename, default={}):
    filepath = f"data/{filename}.json"
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
    
    # Создаем файл если не существует
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(default, f, indent=2)
    return default

def save_json(filename, data):
    try:
        filepath = f"data/{filename}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False

# Инициализация данных
users_db = load_json("users", {})
chats_db = load_json("chats", {})
messages_db = load_json("messages", [])
online_users = {}

logger.info(f"📊 Loaded: {len(users_db)} users, {len(chats_db)} chats, {len(messages_db)} messages")

# Монтирование статических файлов
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.error(f"Error mounting static files: {e}")

# ============ Функции для работы с файлами ============

def load_data(filename):
    """Загрузка данных из JSON файла"""
    try:
        filepath = f"data/{filename}.json"
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {} if filename in ["users", "chats"] else []
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        return {} if filename in ["users", "chats"] else []

def save_data(filename, data):
    """Сохранение данных в JSON файл"""
    try:
        filepath = f"data/{filename}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False

# Текущие данные в памяти
users_db = load_data("users")
chats_db = load_data("chats")
messages_db = load_data("messages")
online_users = {}

# ============ Модели данных ============

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None

class ChatCreate(BaseModel):
    participantId: str

# ============ JWT функции ============

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    payload = verify_token(authorization.split(" ")[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

# ============ HTML СТРАНИЦА ============

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Millow Messenger</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
            background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);
            min-height:100vh;display:flex;align-items:center;justify-content:center;
            color:#fff;padding:20px
        }
        .container{max-width:1000px;width:100%}
        .header{text-align:center;margin-bottom:30px}
        .header h1{font-size:48px;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
        .status{color:#10b981;font-size:14px;margin-top:10px}
        .card{
            background:rgba(31,41,55,0.7);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
            border-radius:20px;padding:30px;margin-bottom:20px;border:1px solid rgba(255,255,255,0.1);
            box-shadow:0 20px 40px rgba(0,0,0,0.3)
        }
        input,textarea,select{
            width:100%;padding:14px 18px;margin:8px 0;
            background:rgba(55,65,81,0.6);border:2px solid rgba(255,255,255,0.1);
            border-radius:14px;color:#fff;font-size:15px;outline:none;
            transition:all 0.3s
        }
        input:focus,textarea:focus{
            border-color:#8b5cf6;box-shadow:0 0 0 3px rgba(139,92,246,0.2)
        }
        button{
            padding:12px 24px;background:linear-gradient(135deg,#8b5cf6,#7c3aed);
            border:none;border-radius:50px;color:#fff;font-weight:600;cursor:pointer;
            margin:4px;transition:all 0.3s;font-size:14px
        }
        button:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(139,92,246,0.4)}
        button.secondary{background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2)}
        button.danger{background:linear-gradient(135deg,#ef4444,#dc2626)}
        .flex{display:flex}.gap-2{gap:10px}.flex-wrap{flex-wrap:wrap}
        .justify-between{justify-content:space-between}
        .items-center{align-items:center}
        .hidden{display:none!important}
        .mt-2{margin-top:10px}.mt-4{margin-top:20px}.mb-2{margin-bottom:10px}
        .text-center{text-align:center}.text-sm{font-size:14px}
        .text-gray{color:#9ca3af}.text-green{color:#10b981}.text-red{color:#ef4444}
        .avatar{width:48px;height:48px;border-radius:50%;object-fit:cover;border:2px solid rgba(139,92,246,0.5)}
        .avatar-lg{width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid #8b5cf6}
        .user-item{
            display:flex;align-items:center;gap:12px;padding:12px;
            background:rgba(55,65,81,0.3);border-radius:14px;cursor:pointer;
            margin:6px 0;transition:all 0.2s
        }
        .user-item:hover{background:rgba(139,92,246,0.3);transform:translateX(4px)}
        .user-item.active{background:rgba(139,92,246,0.4);border:1px solid rgba(139,92,246,0.5)}
        .status-dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:4px}
        .online{background:#10b981;box-shadow:0 0 10px #10b981}
        .offline{background:#6b7280}
        .chat-area{
            height:350px;overflow-y:auto;padding:15px;
            background:rgba(0,0,0,0.2);border-radius:14px;
            display:flex;flex-direction:column;gap:10px
        }
        .message{
            padding:10px 16px;border-radius:18px;max-width:75%;
            animation:slideIn 0.3s;word-wrap:break-word
        }
        .message.own{
            background:linear-gradient(135deg,#8b5cf6,#7c3aed);
            align-self:flex-end;border-bottom-right-radius:4px
        }
        .message.other{
            background:rgba(55,65,81,0.8);
            align-self:flex-start;border-bottom-left-radius:4px
        }
        .message-sender{font-size:11px;color:rgba(255,255,255,0.6);margin-bottom:4px}
        .message-time{font-size:10px;color:rgba(255,255,255,0.4);margin-top:4px;text-align:right}
        @keyframes slideIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        .tabs{display:flex;gap:8px;margin-bottom:15px}
        .tab-btn{padding:10px 20px;border-radius:50px;font-size:13px}
        .tab-btn.active{background:linear-gradient(135deg,#8b5cf6,#7c3aed)!important}
        .grid-2{display:grid;grid-template-columns:300px 1fr;gap:15px}
        @media(max-width:768px){
            .grid-2{grid-template-columns:1fr}
            .header h1{font-size:32px}
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 Millow Messenger</h1>
            <p class="status">🟢 Server Active | <span id="stats">Loading...</span></p>
        </div>

        <!-- Auth Screen -->
        <div class="card" id="authScreen">
            <h2 id="authTitle" class="mb-2">Login to Millow</h2>
            <input type="text" id="regName" placeholder="Full Name" class="hidden">
            <input type="email" id="email" placeholder="Email address">
            <input type="password" id="password" placeholder="Password">
            <div class="flex gap-2 mt-4">
                <button onclick="handleAuth()" id="authBtn" style="flex:1">Login</button>
                <button onclick="toggleAuth()" id="toggleBtn" class="secondary">Create Account</button>
            </div>
            <p id="authError" class="text-red text-center mt-2"></p>
        </div>

        <!-- Main App -->
        <div id="appScreen" class="hidden">
            <div class="flex justify-between items-center mb-2">
                <div class="tabs">
                    <button onclick="showTab('chats')" id="tabChats" class="tab-btn active">💬 Chats</button>
                    <button onclick="showTab('users')" id="tabUsers" class="tab-btn secondary">👥 Users</button>
                    <button onclick="showTab('profile')" id="tabProfile" class="tab-btn secondary">👤 Profile</button>
                </div>
                <button onclick="logout()" class="danger">🚪 Logout</button>
            </div>

            <!-- Chats Tab -->
            <div id="tabContentChats">
                <div class="grid-2">
                    <div>
                        <div class="card" style="max-height:500px;overflow-y:auto">
                            <h3 class="mb-2">Your Chats</h3>
                            <div id="chatsList"></div>
                        </div>
                    </div>
                    <div>
                        <div class="card">
                            <div class="flex justify-between items-center mb-2">
                                <h3 id="chatTitle">Select a chat</h3>
                                <button onclick="deleteChat()" class="danger secondary" style="padding:6px 12px;font-size:12px">🗑️</button>
                            </div>
                            <div class="chat-area" id="chatArea">
                                <p class="text-gray text-center mt-4">👋 Select a user to start chatting</p>
                            </div>
                            <div class="flex gap-2 mt-4">
                                <input type="text" id="messageInput" placeholder="Type a message..." style="flex:1" 
                                       onkeypress="if(event.key==='Enter')sendMessage()">
                                <button onclick="sendMessage()">📤 Send</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Users Tab -->
            <div id="tabContentUsers" class="hidden">
                <div class="card">
                    <h3 class="mb-2">All Users</h3>
                    <input type="text" id="userSearch" placeholder="🔍 Search users..." onkeyup="filterUsers()">
                    <div id="usersList" style="max-height:400px;overflow-y:auto;margin-top:10px"></div>
                </div>
            </div>

            <!-- Profile Tab -->
            <div id="tabContentProfile" class="hidden">
                <div class="card">
                    <h2 class="mb-2">Edit Profile</h2>
                    <div class="text-center mt-4">
                        <img id="profileAvatar" class="avatar-lg" src="" alt="Avatar">
                        <div class="mt-2">
                            <input type="file" id="avatarFile" accept="image/*" style="display:none" onchange="uploadAvatar()">
                            <button onclick="document.getElementById('avatarFile').click()" class="secondary">📷 Change Photo</button>
                        </div>
                    </div>
                    <div class="mt-4"><label class="text-sm text-gray">Name</label>
                    <input type="text" id="profileName"></div>
                    <div><label class="text-sm text-gray">Email</label>
                    <input type="email" id="profileEmail"></div>
                    <div><label class="text-sm text-gray">Bio</label>
                    <textarea id="profileBio" rows="3"></textarea></div>
                    <div><label class="text-sm text-gray">Phone</label>
                    <input type="tel" id="profilePhone"></div>
                    <div class="flex gap-2 mt-4">
                        <button onclick="updateProfile()" style="flex:1">💾 Save Changes</button>
                        <button onclick="showTab('chats')" class="secondary" style="flex:1">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API = window.location.origin;
        let token = localStorage.getItem('millow_token');
        let user = JSON.parse(localStorage.getItem('millow_user')||'null');
        let isLogin = true;
        let socket = null;
        let currentChat = null;
        let allUsers = [];
        let allChats = [];

        // Init
        checkServer();
        if(token && user) { showApp(); connectWS(); }
        setInterval(() => { if(currentChat) loadMessages(); }, 1500);

        async function checkServer() {
            try {
                const r = await fetch(API+'/api/health');
                const d = await r.json();
                document.getElementById('stats').textContent = d.users+' users, '+d.chats+' chats, '+d.messages+' messages';
            } catch(e) {
                document.getElementById('stats').textContent = 'Connecting...';
            }
        }

        function toggleAuth() {
            isLogin = !isLogin;
            document.getElementById('regName').classList.toggle('hidden', isLogin);
            document.getElementById('authTitle').textContent = isLogin ? 'Login to Millow' : 'Create Account';
            document.getElementById('authBtn').textContent = isLogin ? 'Login' : 'Register';
            document.getElementById('toggleBtn').textContent = isLogin ? 'Create Account' : 'Back to Login';
            document.getElementById('authError').textContent = '';
        }

        async function handleAuth() {
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const name = document.getElementById('regName').value.trim();
            
            if(!email||!password) {
                document.getElementById('authError').textContent = 'Please fill all fields';
                return;
            }
            
            const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
            const body = isLogin ? {email,password} : {name,email,password};
            
            try {
                const r = await fetch(API+endpoint, {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify(body)
                });
                const d = await r.json();
                if(!r.ok) throw new Error(d.detail||'Error');
                
                token = d.token; user = d.user;
                localStorage.setItem('millow_token', token);
                localStorage.setItem('millow_user', JSON.stringify(user));
                showApp(); connectWS(); loadAll();
            } catch(e) {
                document.getElementById('authError').textContent = e.message;
            }
        }

        function showApp() {
            document.getElementById('authScreen').classList.add('hidden');
            document.getElementById('appScreen').classList.remove('hidden');
            showTab('chats');
        }

        function showTab(tab) {
            ['tabContentChats','tabContentUsers','tabContentProfile'].forEach(id => document.getElementById(id).classList.add('hidden'));
            document.getElementById('tabContent'+tab.charAt(0).toUpperCase()+tab.slice(1)).classList.remove('hidden');
            
            ['tabChats','tabUsers','tabProfile'].forEach(id => {
                document.getElementById(id).className = 'tab-btn secondary';
            });
            document.getElementById('tab'+tab.charAt(0).toUpperCase()+tab.slice(1)).className = 'tab-btn active';
            
            if(tab==='users') loadUsers();
            if(tab==='profile') loadProfile();
            if(tab==='chats') loadChats();
        }

        function logout() {
            localStorage.clear();
            token=null; user=null; currentChat=null;
            if(socket) socket.close();
            document.getElementById('authScreen').classList.remove('hidden');
            document.getElementById('appScreen').classList.add('hidden');
        }

        async function loadAll() { await loadUsers(); await loadChats(); checkServer(); }

        async function loadUsers() {
            try {
                const r = await fetch(API+'/api/users', {headers:{'Authorization':'Bearer '+token}});
                allUsers = await r.json();
                renderUsers();
            } catch(e) {}
        }

        function renderUsers() {
            const list = document.getElementById('usersList');
            list.innerHTML = allUsers.length ? '' : '<p class="text-gray text-center">No users yet</p>';
            allUsers.forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                div.innerHTML = `
                    <img src="${u.avatar||'https://ui-avatars.com/api/?name=U&background=8B5CF6&color=fff'}" class="avatar">
                    <div style="flex:1">
                        <b>${u.name}</b><br>
                        <span class="status-dot ${u.online?'online':'offline'}"></span>
                        <span class="text-sm text-gray">${u.online?'Online':'Offline'}</span>
                    </div>
                `;
                div.onclick = () => startChat(u.id);
                list.appendChild(div);
            });
        }

        function filterUsers() {
            const s = document.getElementById('userSearch').value.toLowerCase();
            const list = document.getElementById('usersList');
            list.innerHTML = '';
            allUsers.filter(u => u.name.toLowerCase().includes(s)||u.email.toLowerCase().includes(s)).forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                div.innerHTML = `<img src="${u.avatar}" class="avatar"><div style="flex:1"><b>${u.name}</b></div>`;
                div.onclick = () => startChat(u.id);
                list.appendChild(div);
            });
        }

        async function loadChats() {
            try {
                const r = await fetch(API+'/api/chats', {headers:{'Authorization':'Bearer '+token}});
                allChats = await r.json();
                renderChats();
            } catch(e) {}
        }

        function renderChats() {
            const list = document.getElementById('chatsList');
            list.innerHTML = allChats.length ? '' : '<p class="text-gray text-center">No chats yet</p>';
            allChats.forEach(c => {
                if(!c.otherUser) return;
                const div = document.createElement('div');
                div.className = 'user-item';
                if(currentChat?.id === c.id) div.classList.add('active');
                div.innerHTML = `
                    <img src="${c.otherUser.avatar}" class="avatar">
                    <div style="flex:1">
                        <b>${c.otherUser.name}</b><br>
                        <span class="text-sm text-gray">${c.lastMessage?.content?.substring(0,25)||'No messages'}</span>
                    </div>
                    <span class="status-dot ${c.otherUser.online?'online':'offline'}"></span>
                `;
                div.onclick = () => selectChat(c);
                list.appendChild(div);
            });
        }

        async function startChat(uid) {
            try {
                const r = await fetch(API+'/api/chats', {
                    method:'POST',
                    headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
                    body:JSON.stringify({participantId:uid})
                });
                currentChat = await r.json();
                selectChat(currentChat);
                showTab('chats');
            } catch(e) {}
        }

        function selectChat(c) {
            currentChat = c;
            document.getElementById('chatTitle').textContent = c.otherUser ? '💬 '+c.otherUser.name : 'Chat';
            document.getElementById('chatArea').innerHTML = '';
            loadMessages(); renderChats();
        }

        async function loadMessages() {
            if(!currentChat) return;
            try {
                const r = await fetch(API+'/api/messages/'+currentChat.id, {headers:{'Authorization':'Bearer '+token}});
                const msgs = await r.json();
                const area = document.getElementById('chatArea');
                area.innerHTML = msgs.length ? '' : '<p class="text-gray text-center mt-4">No messages yet. Say hello! 👋</p>';
                msgs.forEach(m => {
                    const div = document.createElement('div');
                    div.className = 'message '+(m.senderId===user.id?'own':'other');
                    div.innerHTML = `
                        ${m.senderId!==user.id ? `<div class="message-sender">${m.sender?.name||'Unknown'}</div>` : ''}
                        ${m.content}
                        <div class="message-time">${new Date(m.timestamp).toLocaleTimeString()}</div>
                    `;
                    area.appendChild(div);
                });
                area.scrollTop = area.scrollHeight;
            } catch(e) {}
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const content = input.value.trim();
            if(!content||!currentChat) return;
            input.value = '';
            
            if(socket && socket.readyState===WebSocket.OPEN) {
                socket.send(JSON.stringify({type:'private-message',chatId:currentChat.id,senderId:user.id,content}));
            }
            setTimeout(loadMessages, 300);
        }

        function deleteChat() {
            if(currentChat && confirm('Close this chat?')) {
                currentChat = null;
                document.getElementById('chatArea').innerHTML = '<p class="text-gray text-center mt-4">Select a user to chat</p>';
                document.getElementById('chatTitle').textContent = 'Select a chat';
                renderChats();
            }
        }

        function loadProfile() {
            document.getElementById('profileAvatar').src = user.avatar||'https://ui-avatars.com/api/?name=U&background=8B5CF6&color=fff';
            document.getElementById('profileName').value = user.name||'';
            document.getElementById('profileEmail').value = user.email||'';
            document.getElementById('profileBio').value = user.bio||'';
            document.getElementById('profilePhone').value = user.phone||'';
        }

        async function updateProfile() {
            const body = {
                name: document.getElementById('profileName').value,
                email: document.getElementById('profileEmail').value,
                bio: document.getElementById('profileBio').value,
                phone: document.getElementById('profilePhone').value
            };
            try {
                const r = await fetch(API+'/api/users/profile', {
                    method:'PUT',
                    headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
                    body:JSON.stringify(body)
                });
                user = await r.json();
                localStorage.setItem('millow_user', JSON.stringify(user));
                alert('✅ Profile updated!');
                showTab('chats');
            } catch(e) {
                alert('❌ Error: '+e.message);
            }
        }

        async function uploadAvatar() {
            const file = document.getElementById('avatarFile').files[0];
            if(!file) return;
            const fd = new FormData();
            fd.append('avatar', file);
            try {
                const r = await fetch(API+'/api/users/avatar', {
                    method:'POST',
                    headers:{'Authorization':'Bearer '+token},
                    body:fd
                });
                const d = await r.json();
                user.avatar = API + d.url;
                localStorage.setItem('millow_user', JSON.stringify(user));
                document.getElementById('profileAvatar').src = user.avatar;
                alert('✅ Avatar updated!');
            } catch(e) {
                alert('❌ Upload failed');
            }
        }

        function connectWS() {
            if(!token||!user) return;
            try {
                const proto = API.startsWith('https') ? 'wss' : 'ws';
                const host = API.replace('https://','').replace('http://','');
                socket = new WebSocket(proto+'://'+host+'/ws');
                
                socket.onopen = () => {
                    console.log('WebSocket connected');
                    socket.send(JSON.stringify({type:'login',userId:user.id}));
                };
                
                socket.onmessage = (e) => {
                    const d = JSON.parse(e.data);
                    if(d.type==='private-message' && currentChat && d.chatId===currentChat.id) loadMessages();
                    if(d.type==='user-status') { loadUsers(); loadChats(); checkServer(); }
                };
                
                socket.onclose = () => setTimeout(connectWS, 3000);
                socket.onerror = () => setTimeout(connectWS, 3000);
            } catch(e) {
                setTimeout(connectWS, 3000);
            }
        }
    </script>
</body>
</html>"""

# ============ API ROUTES ============

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
    logger.info(f"📝 Register: {data.email}")
    
    for u in users_db.values():
        if u["email"] == data.email:
            raise HTTPException(400, "User already exists")
    
    uid = str(uuid.uuid4())
    users_db[uid] = {
        "id": uid,
        "name": data.name,
        "email": data.email,
        "password": pwd_context.hash(data.password),
        "avatar": f"https://ui-avatars.com/api/?name={data.name}&background=8B5CF6&color=fff&size=200",
        "bio": "Hey there! I'm using Millow 💜",
        "phone": "",
        "online": False,
        "lastSeen": datetime.utcnow().isoformat(),
        "createdAt": datetime.utcnow().isoformat()
    }
    
    save_data("users", users_db)
    token = create_token({"id": uid, "email": data.email})
    user_data = {k: v for k, v in users_db[uid].items() if k != "password"}
    
    logger.info(f"✅ Registered: {data.email}")
    return {"token": token, "user": user_data}

@app.post("/api/auth/login")
async def login(data: UserLogin):
    logger.info(f"🔑 Login: {data.email}")
    
    user = next((u for u in users_db.values() if u["email"] == data.email), None)
    if not user or not pwd_context.verify(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"id": user["id"], "email": user["email"]})
    user_data = {k: v for k, v in user.items() if k != "password"}
    
    logger.info(f"✅ Logged in: {data.email}")
    return {"token": token, "user": user_data}

@app.get("/api/users")
async def get_users(payload=Depends(get_current_user)):
    return [{k: v for k, v in u.items() if k != "password"} 
            for u in users_db.values() if u["id"] != payload["id"]]

@app.get("/api/chats")
async def get_chats(payload=Depends(get_current_user)):
    result = []
    for c in chats_db.values():
        if payload["id"] in c["participants"]:
            other_id = next((p for p in c["participants"] if p != payload["id"]), None)
            other = users_db.get(other_id, {})
            result.append({
                **c,
                "otherUser": {k: v for k, v in other.items() if k != "password"} if other else None
            })
    return sorted(result, key=lambda x: x.get("updatedAt", ""), reverse=True)

@app.post("/api/chats")
async def create_chat(data: ChatCreate, payload=Depends(get_current_user)):
    existing = next((c for c in chats_db.values() 
                    if payload["id"] in c["participants"] 
                    and data.participantId in c["participants"]), None)
    
    if existing:
        other = users_db.get(data.participantId, {})
        return {**existing, "otherUser": {k: v for k, v in other.items() if k != "password"} if other else None}
    
    cid = str(uuid.uuid4())
    chats_db[cid] = {
        "id": cid,
        "participants": [payload["id"], data.participantId],
        "isGroup": False,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
        "lastMessage": None
    }
    
    save_data("chats", chats_db)
    other = users_db.get(data.participantId, {})
    return {**chats_db[cid], "otherUser": {k: v for k, v in other.items() if k != "password"} if other else None}

@app.get("/api/messages/{chat_id}")
async def get_messages(chat_id: str, payload=Depends(get_current_user)):
    result = []
    for m in messages_db:
        if m["chatId"] == chat_id:
            sender = users_db.get(m["senderId"], {})
            result.append({**m, "sender": {k: v for k, v in sender.items() if k != "password"} if sender else None})
    return sorted(result, key=lambda x: x["timestamp"])

@app.put("/api/users/profile")
async def update_profile(data: UserUpdate, payload=Depends(get_current_user)):
    user = users_db.get(payload["id"])
    if not user:
        raise HTTPException(404, "User not found")
    
    for field in ["name", "email", "bio", "phone", "avatar"]:
        val = getattr(data, field, None)
        if val is not None:
            user[field] = val
    
    save_data("users", users_db)
    return {k: v for k, v in user.items() if k != "password"}

@app.post("/api/users/avatar")
async def upload_avatar(avatar: UploadFile = File(...), payload=Depends(get_current_user)):
    try:
        ext = os.path.splitext(avatar.filename)[1] if avatar.filename else ".jpg"
        fname = f"{payload['id']}_{uuid.uuid4().hex[:8]}{ext}"
        fpath = f"uploads/avatars/{fname}"
        
        content = await avatar.read()
        with open(fpath, "wb") as f:
            f.write(content)
        
        url = f"/uploads/avatars/{fname}"
        if payload["id"] in users_db:
            users_db[payload["id"]]["avatar"] = url
            save_data("users", users_db)
        
        logger.info(f"📸 Avatar uploaded: {url}")
        return {"url": url}
    except Exception as e:
        logger.error(f"Avatar upload error: {e}")
        raise HTTPException(500, str(e))

# WebSocket
@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
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
                    save_data("users", users_db)
                
                for u, ws in online_users.items():
                    if u != uid:
                        try:
                            await ws.send_text(json.dumps({"type": "user-status", "userId": uid, "online": True}))
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
                save_data("messages", messages_db)
                
                if data["chatId"] in chats_db:
                    chats_db[data["chatId"]]["lastMessage"] = msg
                    chats_db[data["chatId"]]["updatedAt"] = datetime.utcnow().isoformat()
                    save_data("chats", chats_db)
                
                sender = users_db.get(data["senderId"], {})
                msg_sender = {
                    **msg,
                    "sender": {k: v for k, v in sender.items() if k != "password"} if sender else None
                }
                
                if data["chatId"] in chats_db:
                    for pid in chats_db[data["chatId"]]["participants"]:
                        if pid != data["senderId"] and pid in online_users:
                            try:
                                await online_users[pid].send_text(json.dumps({"type": "private-message", **msg_sender}))
                            except:
                                pass
                
                await websocket.send_text(json.dumps({"type": "private-message", **msg_sender}))
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if uid:
            if uid in online_users:
                del online_users[uid]
            if uid in users_db:
                users_db[uid]["online"] = False
                users_db[uid]["lastSeen"] = datetime.utcnow().isoformat()
                save_data("users", users_db)
            
            for u, ws in online_users.items():
                try:
                    await ws.send_text(json.dumps({"type": "user-status", "userId": uid, "online": False}))
                except:
                    pass

# Запуск
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    print(f"""
╔══════════════════════════════════════════╗
║         🚀 Millow Messenger            ║
║         Server Starting...             ║
║         Port: {port}                      ║
║         Data: data/                    ║
║         Uploads: uploads/avatars/      ║
╚══════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")