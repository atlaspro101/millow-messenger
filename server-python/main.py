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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Millow Messenger</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;color:#fff;padding:20px}
        .container{max-width:900px;width:100%}
        .header{text-align:center;margin-bottom:30px}
        .header h1{font-size:52px;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}
        .status{color:#10b981;font-size:13px}
        .card{background:rgba(31,41,55,0.7);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-radius:20px;padding:25px;margin-bottom:15px;border:1px solid rgba(255,255,255,0.1);box-shadow:0 10px 40px rgba(0,0,0,0.3)}
        input,textarea{width:100%;padding:14px 18px;margin:8px 0;background:rgba(55,65,81,0.6);border:2px solid rgba(255,255,255,0.1);border-radius:14px;color:#fff;font-size:14px;outline:none;transition:all 0.3s}
        input:focus,textarea:focus{border-color:#8b5cf6;box-shadow:0 0 0 3px rgba(139,92,246,0.2)}
        button{padding:12px 28px;background:linear-gradient(135deg,#8b5cf6,#7c3aed);border:none;border-radius:50px;color:#fff;font-weight:600;cursor:pointer;margin:4px;transition:all 0.3s;font-size:14px}
        button:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(139,92,246,0.4)}
        button.secondary{background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2)}
        button.danger{background:linear-gradient(135deg,#ef4444,#dc2626)}
        button.demo{background:rgba(139,92,246,0.2);border:1px solid rgba(139,92,246,0.3);font-size:12px;padding:8px 16px}
        .hidden{display:none!important}
        .flex{display:flex;gap:10px;flex-wrap:wrap}
        .justify-between{justify-content:space-between}
        .items-center{align-items:center}
        .mt-2{margin-top:10px}.mt-4{margin-top:20px}.mb-2{margin-bottom:10px}.mb-4{margin-bottom:20px}
        .text-center{text-align:center}.text-sm{font-size:13px}.text-gray{color:#9ca3af}.text-green{color:#10b981}.text-red{color:#ef4444}
        .avatar{width:48px;height:48px;border-radius:50%;object-fit:cover;border:2px solid rgba(139,92,246,0.5)}
        .avatar-lg{width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid #8b5cf6;box-shadow:0 0 30px rgba(139,92,246,0.3)}
        .user-item{display:flex;align-items:center;gap:12px;padding:12px;background:rgba(55,65,81,0.3);border-radius:14px;cursor:pointer;margin:6px 0;transition:all 0.2s}
        .user-item:hover{background:rgba(139,92,246,0.3);transform:translateX(4px)}
        .user-item.active{background:rgba(139,92,246,0.4);border:1px solid rgba(139,92,246,0.5)}
        .status-dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:4px}
        .online{background:#10b981;box-shadow:0 0 10px #10b981}.offline{background:#6b7280}
        .chat-area{height:350px;overflow-y:auto;padding:15px;background:rgba(0,0,0,0.2);border-radius:14px;display:flex;flex-direction:column;gap:10px}
        .message{padding:10px 16px;border-radius:18px;max-width:75%;word-wrap:break-word;animation:slideIn 0.3s}
        .message.own{background:linear-gradient(135deg,#8b5cf6,#7c3aed);align-self:flex-end;border-bottom-right-radius:4px}
        .message.other{background:rgba(55,65,81,0.8);align-self:flex-start;border-bottom-left-radius:4px}
        .message-sender{font-size:11px;color:rgba(255,255,255,0.6);margin-bottom:4px}
        .message-time{font-size:10px;color:rgba(255,255,255,0.4);margin-top:4px;text-align:right}
        @keyframes slideIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        .grid-2{display:grid;grid-template-columns:280px 1fr;gap:15px}
        .tabs{display:flex;gap:8px;margin-bottom:15px}
        .tab-btn{padding:10px 20px;border-radius:50px;font-size:13px}
        .tab-btn.active{background:linear-gradient(135deg,#8b5cf6,#7c3aed)!important}
        @media(max-width:768px){.grid-2{grid-template-columns:1fr}.header h1{font-size:36px}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 Millow</h1>
            <p class="status">🟢 Online | <span id="stats">Loading...</span></p>
        </div>

        <div class="card" id="authScreen">
            <h2 class="mb-4" id="authTitle">Login to Millow</h2>
            
            <!-- Demo accounts -->
            <div class="flex mb-4" style="justify-content:center">
                <button class="demo" onclick="quickLogin('taran@millow.com','fastyk26tyr')">👤 TARAN</button>
                <button class="demo" onclick="quickLogin('test@millow.com','test123')">👤 Test</button>
            </div>
            
            <div style="text-align:center;margin-bottom:15px;color:#6b7280;font-size:12px">or login manually</div>
            
            <input type="text" id="regName" placeholder="Full Name (for register)" class="hidden">
            <input type="email" id="email" placeholder="Email address">
            <input type="password" id="password" placeholder="Password">
            
            <div class="flex mt-4">
                <button onclick="handleAuth()" id="authBtn" style="flex:1">Login</button>
                <button onclick="toggleAuth()" id="toggleBtn" class="secondary">Create Account</button>
            </div>
            <p id="authError" class="text-red text-center mt-2"></p>
        </div>

        <div id="appScreen" class="hidden">
            <div class="flex justify-between items-center mb-4">
                <div class="tabs">
                    <button onclick="showTab('chats')" id="tabChats" class="tab-btn active">💬 Chats</button>
                    <button onclick="showTab('users')" id="tabUsers" class="tab-btn secondary">👥 Users</button>
                    <button onclick="showTab('profile')" id="tabProfile" class="tab-btn secondary">👤 Profile</button>
                </div>
                <button onclick="logout()" class="danger">🚪 Logout</button>
            </div>

            <div id="chatsTab">
                <div class="grid-2">
                    <div class="card" style="max-height:500px;overflow-y:auto">
                        <h3 class="mb-2">Your Chats</h3>
                        <div id="chatsList"></div>
                    </div>
                    <div class="card">
                        <div class="flex justify-between items-center mb-2">
                            <h3 id="chatTitle">Select a chat</h3>
                        </div>
                        <div class="chat-area" id="chatArea">
                            <p class="text-gray text-center mt-4">👋 Select a user to start chatting</p>
                        </div>
                        <div class="flex mt-4">
                            <input type="text" id="messageInput" placeholder="Type a message..." style="flex:1" onkeypress="if(event.key==='Enter')sendMessage()">
                            <button onclick="sendMessage()">📤 Send</button>
                        </div>
                    </div>
                </div>
            </div>

            <div id="usersTab" class="hidden">
                <div class="card">
                    <h3 class="mb-2">All Users</h3>
                    <input type="text" id="userSearch" placeholder="🔍 Search users..." onkeyup="filterUsers()">
                    <div id="usersList" style="max-height:400px;overflow-y:auto;margin-top:10px"></div>
                </div>
            </div>

            <div id="profileTab" class="hidden">
                <div class="card">
                    <h2 class="mb-4">Edit Profile</h2>
                    <div class="text-center mb-4">
                        <img id="profileAvatar" class="avatar-lg" src="" alt="Avatar">
                        <div class="mt-2">
                            <input type="file" id="avatarFile" accept="image/*" style="display:none" onchange="uploadAvatar()">
                            <button onclick="document.getElementById('avatarFile').click()" class="secondary">📷 Change Photo</button>
                        </div>
                    </div>
                    <label class="text-sm text-gray">Name</label>
                    <input type="text" id="profileName">
                    <label class="text-sm text-gray">Email</label>
                    <input type="email" id="profileEmail">
                    <label class="text-sm text-gray">Bio</label>
                    <textarea id="profileBio" rows="3"></textarea>
                    <label class="text-sm text-gray">Phone</label>
                    <input type="tel" id="profilePhone">
                    <div class="flex mt-4">
                        <button onclick="updateProfile()" style="flex:1">💾 Save</button>
                        <button onclick="showTab('chats')" class="secondary" style="flex:1">Cancel</button>
                    </div>
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

        // Init
        checkStatus();
        if(token && user) { showApp(); connectWS(); }
        setInterval(() => { if(currentChat) loadMessages(); }, 1500);

        async function checkStatus() {
            try {
                const r = await fetch(API+'/');
                const d = await r.json();
                document.getElementById('stats').textContent = d.users+' users | '+d.chats+' chats';
            } catch(e) {
                document.getElementById('stats').textContent = 'Offline - trying to connect...';
            }
        }

        function quickLogin(email, password) {
            document.getElementById('email').value = email;
            document.getElementById('password').value = password;
            handleAuth();
        }

        function toggleAuth() {
            isLogin = !isLogin;
            document.getElementById('regName').classList.toggle('hidden', isLogin);
            document.getElementById('authTitle').textContent = isLogin ? 'Login to Millow' : 'Create Account';
            document.getElementById('authBtn').textContent = isLogin ? 'Login' : 'Register';
            document.getElementById('toggleBtn').textContent = isLogin ? 'Back to Login' : 'Create Account';
            document.getElementById('authError').textContent = '';
        }

        async function handleAuth() {
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const name = document.getElementById('regName').value.trim();
            
            if(!email || !password) {
                document.getElementById('authError').textContent = 'Please fill all fields';
                return;
            }
            
            const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
            const body = isLogin ? {email, password} : {name, email, password};
            
            try {
                const r = await fetch(API+endpoint, {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify(body)
                });
                const d = await r.json();
                
                if(!r.ok) throw new Error(d.detail || 'Error');
                
                token = d.token;
                user = d.user;
                localStorage.setItem('mtoken', token);
                localStorage.setItem('muser', JSON.stringify(user));
                
                showApp();
                connectWS();
                loadAll();
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
            ['chatsTab','usersTab','profileTab'].forEach(id => document.getElementById(id).classList.add('hidden'));
            document.getElementById(tab+'Tab').classList.remove('hidden');
            
            if(tab === 'users') loadUsers();
            if(tab === 'profile') loadProfile();
            if(tab === 'chats') loadChats();
        }

        function logout() {
            localStorage.clear();
            location.reload();
        }

        async function loadAll() {
            await loadUsers();
            await loadChats();
            checkStatus();
        }

        async function loadUsers() {
            try {
                const r = await fetch(API+'/api/users', {headers:{'Authorization':'Bearer '+token}});
                allUsers = await r.json();
                renderUsers();
            } catch(e) {}
        }

        function renderUsers() {
            const list = document.getElementById('usersList');
            list.innerHTML = allUsers.length ? '' : '<p class="text-gray text-center">No other users yet</p>';
            
            allUsers.forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                div.innerHTML = `
                    <img src="${u.avatar}" class="avatar" onerror="this.src='https://ui-avatars.com/api/?name=${u.name}&background=8B5CF6&color=fff'">
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
            
            allUsers
                .filter(u => u.name.toLowerCase().includes(s) || u.email.toLowerCase().includes(s))
                .forEach(u => {
                    const div = document.createElement('div');
                    div.className = 'user-item';
                    div.innerHTML = `<img src="${u.avatar}" class="avatar" onerror="this.src='https://ui-avatars.com/api/?name=U&background=8B5CF6&color=fff'"><div style="flex:1"><b>${u.name}</b><br><span class="text-sm text-gray">${u.email}</span></div>`;
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
                if(currentChat && currentChat.id === c.id) div.classList.add('active');
                div.innerHTML = `
                    <img src="${c.otherUser.avatar}" class="avatar">
                    <div style="flex:1">
                        <b>${c.otherUser.name}</b><br>
                        <span class="text-sm text-gray">${(c.lastMessage?.content || 'No messages').substring(0,30)}</span>
                    </div>
                    <span class="status-dot ${c.otherUser.online?'online':'offline'}"></span>
                `;
                div.onclick = () => selectChat(c);
                list.appendChild(div);
            });
        }

        async function startChat(otherUserId) {
            try {
                const r = await fetch(API+'/api/chats', {
                    method:'POST',
                    headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
                    body:JSON.stringify({participantId: otherUserId})
                });
                currentChat = await r.json();
                selectChat(currentChat);
                showTab('chats');
            } catch(e) {}
        }

        function selectChat(chat) {
            currentChat = chat;
            document.getElementById('chatTitle').textContent = '💬 ' + (chat.otherUser?.name || 'Chat');
            document.getElementById('chatArea').innerHTML = '';
            loadMessages();
            renderChats();
        }

        async function loadMessages() {
            if(!currentChat) return;
            try {
                const r = await fetch(API+'/api/messages/'+currentChat.id, {
                    headers:{'Authorization':'Bearer '+token}
                });
                const msgs = await r.json();
                const area = document.getElementById('chatArea');
                area.innerHTML = msgs.length ? '' : '<p class="text-gray text-center mt-4">No messages yet. Say hello! 👋</p>';
                
                msgs.forEach(m => {
                    const isOwn = m.senderId === user.id;
                    const div = document.createElement('div');
                    div.className = 'message ' + (isOwn ? 'own' : 'other');
                    div.innerHTML = `
                        ${!isOwn ? `<div class="message-sender">${m.sender?.name || 'Unknown'}</div>` : ''}
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
            if(!content || !currentChat) return;
            input.value = '';
            
            if(socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'private-message',
                    chatId: currentChat.id,
                    senderId: user.id,
                    content: content
                }));
            }
            
            setTimeout(loadMessages, 300);
        }

        function loadProfile() {
            document.getElementById('profileAvatar').src = user.avatar || 'https://ui-avatars.com/api/?name='+user.name+'&background=8B5CF6&color=fff';
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
                const r = await fetch(API+'/api/users/profile', {
                    method:'PUT',
                    headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
                    body:JSON.stringify(body)
                });
                
                if(r.ok) {
                    user = await r.json();
                    localStorage.setItem('muser', JSON.stringify(user));
                    alert('✅ Profile saved!');
                    showTab('chats');
                }
            } catch(e) {
                alert('Error: ' + e.message);
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
                    body: fd
                });
                
                if(r.ok) {
                    const d = await r.json();
                    user.avatar = API + d.url;
                    localStorage.setItem('muser', JSON.stringify(user));
                    document.getElementById('profileAvatar').src = user.avatar;
                    alert('✅ Avatar updated!');
                }
            } catch(e) {
                alert('Upload failed');
            }
        }

        function connectWS() {
            if(!token || !user) return;
            
            try {
                const proto = location.protocol === 'https:' ? 'wss' : 'ws';
                socket = new WebSocket(proto + '://' + location.host + '/ws');
                
                socket.onopen = () => {
                    console.log('✅ WebSocket connected');
                    socket.send(JSON.stringify({type:'login', userId: user.id}));
                };
                
                socket.onmessage = (e) => {
                    const d = JSON.parse(e.data);
                    
                    if(d.type === 'private-message') {
                        if(currentChat && d.chatId === currentChat.id) {
                            loadMessages();
                        }
                        loadChats();
                    }
                    
                    if(d.type === 'user-status') {
                        loadUsers();
                        loadChats();
                    }
                };
                
                socket.onclose = () => {
                    console.log('🔄 Reconnecting...');
                    setTimeout(connectWS, 3000);
                };
                
            } catch(e) {
                setTimeout(connectWS, 3000);
            }
        }
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