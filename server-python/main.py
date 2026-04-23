from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Header
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

app = FastAPI(title="Millow API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Секретный ключ
SECRET_KEY = os.getenv("JWT_SECRET", "millow_secret_key_2024")
ALGORITHM = "HS256"

# Проверка паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хранилище данных (словари)
users_db = {}
chats_db = {}
messages_db = []
online_users = {}

# Модели
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

# JWT функции
def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Создаем папки
os.makedirs("uploads/avatars", exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except:
    print("⚠️ Could not mount uploads directory")

# ============ HTML ИНТЕРФЕЙС ============
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Millow Messenger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        .container { max-width: 900px; margin: 20px; width: 100%; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 56px; background: linear-gradient(135deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .card { background: rgba(31,41,55,0.6); backdrop-filter: blur(20px); border-radius: 24px; padding: 30px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1); }
        input, textarea { width: 100%; padding: 16px; margin: 10px 0; background: rgba(55,65,81,0.6); border: 2px solid rgba(255,255,255,0.1); border-radius: 16px; color: white; font-size: 15px; }
        button { padding: 14px 32px; background: linear-gradient(135deg, #8b5cf6, #7c3aed); border: none; border-radius: 50px; color: white; font-weight: 600; cursor: pointer; margin: 8px 4px; }
        button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(139,92,246,0.5); }
        button.secondary { background: rgba(255,255,255,0.1); }
        button.danger { background: linear-gradient(135deg, #ef4444, #dc2626); }
        .chat-layout { display: flex; gap: 20px; flex-wrap: wrap; }
        .sidebar { flex: 1; min-width: 250px; }
        .main-chat { flex: 2; min-width: 300px; }
        .chat-area { max-height: 400px; overflow-y: auto; margin: 15px 0; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 16px; display: flex; flex-direction: column; gap: 10px; }
        .message { padding: 12px 18px; border-radius: 20px; max-width: 75%; animation: slideIn 0.3s; word-wrap: break-word; }
        .message.own { background: linear-gradient(135deg, #8b5cf6, #7c3aed); align-self: flex-end; }
        .message.other { background: rgba(55,65,81,0.8); align-self: flex-start; }
        .message-time { font-size: 10px; color: rgba(255,255,255,0.5); margin-top: 6px; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .user-item { display: flex; align-items: center; gap: 12px; padding: 12px; margin: 8px 0; background: rgba(55,65,81,0.4); border-radius: 14px; cursor: pointer; }
        .user-item:hover { background: rgba(139,92,246,0.3); }
        .avatar { width: 44px; height: 44px; border-radius: 50%; }
        .status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
        .online { background: #10b981; }
        .offline { background: #6b7280; }
        .hidden { display: none !important; }
        .flex { display: flex; }
        .gap-2 { gap: 10px; }
        .mt-2 { margin-top: 10px; }
        .mt-4 { margin-top: 20px; }
        .text-center { text-align: center; }
        .text-sm { font-size: 14px; }
        .text-gray { color: #9ca3af; }
        @media (max-width: 768px) { .chat-layout { flex-direction: column; } .header h1 { font-size: 36px; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Millow Messenger</h1>
            <p class="text-gray text-sm mt-2">API: <span id="apiStatus">Checking...</span></p>
        </div>
        <div class="card" id="authCard">
            <h2 id="authTitle">Login</h2>
            <input type="text" id="nameInput" placeholder="Full Name" class="hidden">
            <input type="email" id="emailInput" placeholder="Email">
            <input type="password" id="passwordInput" placeholder="Password">
            <div class="flex gap-2 mt-4">
                <button onclick="handleAuth()" id="authBtn" style="flex:1">Login</button>
                <button onclick="toggleAuth()" id="toggleBtn" class="secondary">Register</button>
            </div>
            <div id="authError" class="text-center mt-2" style="color:#ef4444;"></div>
        </div>
        <div id="mainInterface" class="hidden">
            <div class="flex gap-2" style="justify-content:space-between; margin-bottom:20px;">
                <div class="flex gap-2">
                    <button onclick="showTab('chats')" id="navChats">Chats</button>
                    <button onclick="showTab('users')" id="navUsers" class="secondary">Users</button>
                    <button onclick="showTab('profile')" id="navProfile" class="secondary">Profile</button>
                </div>
                <button onclick="logout()" class="danger">Logout</button>
            </div>
            <div id="chatsTab">
                <div class="chat-layout">
                    <div class="sidebar"><div class="card"><h3>Your Chats</h3><div id="chatsList"></div></div></div>
                    <div class="main-chat">
                        <div class="card">
                            <h3 id="chatTitle">Select a chat</h3>
                            <div class="chat-area" id="chatArea"><p class="text-gray text-center">Select a user</p></div>
                            <div class="flex gap-2 mt-4">
                                <input type="text" id="messageInput" placeholder="Type a message..." style="flex:1" onkeypress="if(event.key==='Enter') sendMessage()">
                                <button onclick="sendMessage()">Send</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div id="usersTab" class="hidden">
                <div class="card"><h3>All Users</h3><input type="text" id="userSearch" placeholder="Search..." onkeyup="filterUsers()"><div id="usersList"></div></div>
            </div>
            <div id="profileTab" class="hidden">
                <div class="card">
                    <h2>Edit Profile</h2>
                    <div class="text-center mt-4">
                        <img id="profileAvatar" style="width:100px;height:100px;border-radius:50%;" src="">
                        <div class="mt-2"><input type="file" id="avatarFile" accept="image/*" style="display:none" onchange="uploadAvatar()"><button onclick="document.getElementById('avatarFile').click()" class="secondary">Change Photo</button></div>
                    </div>
                    <input type="text" id="profileName" placeholder="Name">
                    <input type="email" id="profileEmail" placeholder="Email">
                    <textarea id="profileBio" placeholder="Bio"></textarea>
                    <input type="tel" id="profilePhone" placeholder="Phone">
                    <div class="flex gap-2 mt-4">
                        <button onclick="updateProfile()" style="flex:1">Save</button>
                        <button onclick="showTab('chats')" class="secondary" style="flex:1">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API = window.location.origin;
        let token = localStorage.getItem('token');
        let user = JSON.parse(localStorage.getItem('user')||'null');
        let isLogin = true;
        let socket = null;
        let currentChat = null;
        let allUsers = [];
        let allChats = [];

        checkAPI();
        if(token && user) { showMain(); connectWS(); }
        setInterval(() => { if(currentChat) loadMessages(); }, 2000);

        async function checkAPI() {
            try {
                const r = await fetch(API+'/api/test');
                const d = await r.json();
                document.getElementById('apiStatus').innerHTML = 'Connected ('+d.usersCount+' users)';
                document.getElementById('apiStatus').style.color = '#10b981';
            } catch(e) {
                document.getElementById('apiStatus').textContent = 'Connecting...';
            }
        }

        function toggleAuth() {
            isLogin = !isLogin;
            document.getElementById('nameInput').classList.toggle('hidden', isLogin);
            document.getElementById('authTitle').textContent = isLogin ? 'Login' : 'Register';
            document.getElementById('authBtn').textContent = isLogin ? 'Login' : 'Register';
            document.getElementById('toggleBtn').textContent = isLogin ? 'Switch to Register' : 'Switch to Login';
        }

        async function handleAuth() {
            const email = document.getElementById('emailInput').value.trim();
            const password = document.getElementById('passwordInput').value;
            const name = document.getElementById('nameInput').value.trim();
            const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
            const body = isLogin ? {email, password} : {name, email, password};
            
            try {
                const r = await fetch(API+endpoint, {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify(body)
                });
                const d = await r.json();
                if(!r.ok) throw new Error(d.detail||'Error');
                token = d.token; user = d.user;
                localStorage.setItem('token', token);
                localStorage.setItem('user', JSON.stringify(user));
                showMain(); connectWS(); loadAll();
            } catch(e) {
                document.getElementById('authError').textContent = e.message;
            }
        }

        function showMain() {
            document.getElementById('authCard').classList.add('hidden');
            document.getElementById('mainInterface').classList.remove('hidden');
            showTab('chats');
        }

        function showTab(t) {
            ['chatsTab','usersTab','profileTab'].forEach(id => document.getElementById(id).classList.add('hidden'));
            document.getElementById(t+'Tab').classList.remove('hidden');
            if(t==='users') loadUsers();
            if(t==='profile') loadProfile();
            if(t==='chats') loadChats();
        }

        function logout() {
            localStorage.clear();
            token=null; user=null;
            if(socket) socket.close();
            location.reload();
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
            const list = document.getElementById('usersList');
            list.innerHTML = '';
            allUsers.forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                div.innerHTML = `<img src="${u.avatar}" class="avatar"><div style="flex:1"><b>${u.name}</b><br><span class="status-dot ${u.online?'online':'offline'}"></span> ${u.online?'Online':'Offline'}</div>`;
                div.onclick = () => startChat(u.id);
                list.appendChild(div);
            });
        }

        function filterUsers() {
            const s = document.getElementById('userSearch').value.toLowerCase();
            const list = document.getElementById('usersList');
            list.innerHTML = '';
            allUsers.filter(u => u.name.toLowerCase().includes(s)).forEach(u => {
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
                div.innerHTML = `<img src="${c.otherUser.avatar}" class="avatar"><div style="flex:1"><b>${c.otherUser.name}</b><br><span class="text-sm text-gray">${c.lastMessage?.content?.substring(0,30)||'No messages'}</span></div>`;
                div.onclick = () => selectChat(c);
                list.appendChild(div);
            });
        }

        async function startChat(uid) {
            const r = await fetch(API+'/api/chats', {
                method:'POST',
                headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
                body:JSON.stringify({participantId:uid})
            });
            currentChat = await r.json();
            selectChat(currentChat);
            showTab('chats');
        }

        function selectChat(c) {
            currentChat = c;
            document.getElementById('chatTitle').textContent = c.otherUser ? 'Chat with '+c.otherUser.name : 'Chat';
            loadMessages();
            renderChats();
        }

        async function loadMessages() {
            if(!currentChat) return;
            const r = await fetch(API+'/api/messages/'+currentChat.id, {headers:{'Authorization':'Bearer '+token}});
            const msgs = await r.json();
            const area = document.getElementById('chatArea');
            area.innerHTML = msgs.length ? '' : '<p class="text-gray text-center">No messages yet</p>';
            msgs.forEach(m => {
                const div = document.createElement('div');
                div.className = 'message '+(m.senderId===user.id?'own':'other');
                div.innerHTML = `${m.content}<div class="message-time">${new Date(m.timestamp).toLocaleTimeString()}</div>`;
                area.appendChild(div);
            });
            area.scrollTop = area.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const content = input.value.trim();
            if(!content || !currentChat) return;
            input.value = '';
            
            if(socket && socket.readyState===WebSocket.OPEN) {
                socket.send(JSON.stringify({type:'private-message', chatId:currentChat.id, senderId:user.id, content}));
            }
            setTimeout(loadMessages, 500);
        }

        function loadProfile() {
            document.getElementById('profileAvatar').src = user.avatar;
            document.getElementById('profileName').value = user.name;
            document.getElementById('profileEmail').value = user.email;
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
            const r = await fetch(API+'/api/users/profile', {
                method:'PUT',
                headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
                body:JSON.stringify(body)
            });
            user = await r.json();
            localStorage.setItem('user', JSON.stringify(user));
            alert('Profile updated!');
            showTab('chats');
        }

        async function uploadAvatar() {
            const file = document.getElementById('avatarFile').files[0];
            if(!file) return;
            const fd = new FormData();
            fd.append('avatar', file);
            const r = await fetch(API+'/api/users/avatar', {
                method:'POST',
                headers:{'Authorization':'Bearer '+token},
                body:fd
            });
            const d = await r.json();
            user.avatar = API + d.url;
            localStorage.setItem('user', JSON.stringify(user));
            document.getElementById('profileAvatar').src = user.avatar;
            alert('Avatar updated!');
        }

        function connectWS() {
            const wsUrl = (API.startsWith('https')?'wss://':'ws://')+API.replace('https://','').replace('http://','')+'/ws';
            socket = new WebSocket(wsUrl);
            socket.onopen = () => {
                socket.send(JSON.stringify({type:'login', userId:user.id}));
            };
            socket.onmessage = (e) => {
                const d = JSON.parse(e.data);
                if(d.type==='private-message' && currentChat && d.chatId===currentChat.id) loadMessages();
                if(d.type==='user-status') loadUsers();
                loadChats();
            };
            socket.onclose = () => setTimeout(connectWS, 3000);
        }
    </script>
</body>
</html>
"""

# ============ API ENDPOINTS ============

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_PAGE

@app.get("/api/test")
async def test():
    return {"message":"API OK","usersCount":len(users_db),"chatsCount":len(chats_db)}

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    for u in users_db.values():
        if u["email"] == user_data.email:
            raise HTTPException(400, "User already exists")
    
    uid = str(uuid.uuid4())
    users_db[uid] = {
        "id": uid, "name": user_data.name, "email": user_data.email,
        "password": pwd_context.hash(user_data.password),
        "avatar": f"https://ui-avatars.com/api/?name={user_data.name}&background=8B5CF6&color=fff&size=200",
        "bio": "Hey there!", "phone": "", "online": False,
        "lastSeen": datetime.utcnow().isoformat(), "createdAt": datetime.utcnow().isoformat()
    }
    token = create_token({"id": uid, "email": user_data.email})
    user_resp = {k:v for k,v in users_db[uid].items() if k != "password"}
    return {"token": token, "user": user_resp}

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    user = next((u for u in users_db.values() if u["email"] == user_data.email), None)
    if not user or not pwd_context.verify(user_data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_token({"id": user["id"], "email": user["email"]})
    user_resp = {k:v for k,v in user.items() if k != "password"}
    return {"token": token, "user": user_resp}

@app.get("/api/users")
async def get_users(authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "No token")
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401, "Invalid token")
    return [{k:v for k,v in u.items() if k!="password"} for u in users_db.values() if u["id"]!=payload["id"]]

@app.get("/api/chats")
async def get_chats(authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "No token")
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401, "Invalid token")
    
    result = []
    for c in chats_db.values():
        if payload["id"] in c["participants"]:
            other_id = next((p for p in c["participants"] if p!=payload["id"]), None)
            other = users_db.get(other_id)
            result.append({**c, "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None})
    return sorted(result, key=lambda x: x.get("updatedAt",""), reverse=True)

@app.post("/api/chats")
async def create_chat(data: ChatCreate, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "No token")
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401, "Invalid token")
    
    existing = next((c for c in chats_db.values() if payload["id"] in c["participants"] and data.participantId in c["participants"]), None)
    if existing:
        other = users_db.get(data.participantId)
        return {**existing, "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None}
    
    cid = str(uuid.uuid4())
    chats_db[cid] = {
        "id": cid, "participants": [payload["id"], data.participantId],
        "isGroup": False, "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(), "lastMessage": None
    }
    other = users_db.get(data.participantId)
    return {**chats_db[cid], "otherUser": {k:v for k,v in other.items() if k!="password"} if other else None}

@app.get("/api/messages/{chat_id}")
async def get_messages(chat_id: str, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "No token")
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401, "Invalid token")
    
    msgs = []
    for m in messages_db:
        if m["chatId"] == chat_id:
            sender = users_db.get(m["senderId"])
            msgs.append({**m, "sender": {k:v for k,v in sender.items() if k!="password"} if sender else None})
    return sorted(msgs, key=lambda x: x["timestamp"])

@app.put("/api/users/profile")
async def update_profile(data: UserUpdate, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "No token")
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401, "Invalid token")
    
    u = users_db.get(payload["id"])
    if not u: raise HTTPException(404, "Not found")
    
    for field in ["name","email","bio","phone","avatar"]:
        val = getattr(data, field, None)
        if val: u[field] = val
    
    return {k:v for k,v in u.items() if k!="password"}

@app.post("/api/users/avatar")
async def upload_avatar(avatar: UploadFile = File(...), authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "No token")
    payload = verify_token(authorization.split(" ")[1])
    if not payload: raise HTTPException(401, "Invalid token")
    
    ext = os.path.splitext(avatar.filename)[1] if avatar.filename else ".jpg"
    fname = f"{payload['id']}_{uuid.uuid4().hex[:8]}{ext}"
    fpath = f"uploads/avatars/{fname}"
    
    with open(fpath, "wb") as f:
        f.write(await avatar.read())
    
    url = f"/uploads/avatars/{fname}"
    if payload["id"] in users_db:
        users_db[payload["id"]]["avatar"] = url
    
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
                if uid in users_db: users_db[uid]["online"] = True
                for u, ws in online_users.items():
                    if u != uid:
                        try: await ws.send_text(json.dumps({"type":"user-status","userId":uid,"online":True}))
                        except: pass
            
            elif data.get("type") == "private-message":
                msg = {
                    "id": str(uuid.uuid4()), "chatId": data["chatId"],
                    "senderId": data["senderId"], "content": data["content"],
                    "type": "text", "timestamp": datetime.utcnow().isoformat(), "read": False
                }
                messages_db.append(msg)
                
                if data["chatId"] in chats_db:
                    chats_db[data["chatId"]]["lastMessage"] = msg
                    chats_db[data["chatId"]]["updatedAt"] = datetime.utcnow().isoformat()
                
                sender = users_db.get(data["senderId"])
                msg_with_sender = {**msg, "sender": {k:v for k,v in sender.items() if k!="password"} if sender else None}
                
                if data["chatId"] in chats_db:
                    for pid in chats_db[data["chatId"]]["participants"]:
                        if pid != data["senderId"] and pid in online_users:
                            try: await online_users[pid].send_text(json.dumps({"type":"private-message",**msg_with_sender}))
                            except: pass
                
                await websocket.send_text(json.dumps({"type":"private-message",**msg_with_sender}))
    
    except:
        pass
    finally:
        if uid and uid in online_users:
            del online_users[uid]
            if uid in users_db: users_db[uid]["online"] = False
            for u, ws in online_users.items():
                try: await ws.send_text(json.dumps({"type":"user-status","userId":uid,"online":False}))
                except: pass

# Запуск
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    print(f"\n✅ Millow server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)