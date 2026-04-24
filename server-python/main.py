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

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for d in ["data", "uploads", "uploads/avatars"]:
    os.makedirs(d, exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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

if len(users_db) == 0:
    users_db["startup_1"] = {
        "id": "startup_1", "name": "TARAN", "email": "taran@millow.com",
        "password": hash_password("fastyk26tyr"),
        "avatar": "https://ui-avatars.com/api/?name=TARAN&background=8B5CF6&color=fff&size=200&bold=true",
        "bio": "Hey there! 💜", "phone": "", "online": False,
        "lastSeen": datetime.utcnow().isoformat(), "createdAt": datetime.utcnow().isoformat()
    }
    users_db["startup_2"] = {
        "id": "startup_2", "name": "Test", "email": "test@millow.com",
        "password": hash_password("test123"),
        "avatar": "https://ui-avatars.com/api/?name=TEST&background=EC4899&color=fff&size=200&bold=true",
        "bio": "Just testing", "phone": "", "online": False,
        "lastSeen": datetime.utcnow().isoformat(), "createdAt": datetime.utcnow().isoformat()
    }

class UserRegister(BaseModel): name: str; email: str; password: str
class UserLogin(BaseModel): email: str; password: str
class ChatCreate(BaseModel): participantId: str
class UserUpdate(BaseModel):
    name: Optional[str] = None; email: Optional[str] = None
    bio: Optional[str] = None; phone: Optional[str] = None; avatar: Optional[str] = None

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Millow Messenger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a1a;
            color: #fff;
            min-height: 100vh;
            overflow-x: hidden;
        }
        body::before {
            content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(circle at 30% 40%, rgba(139,92,246,0.08), transparent 50%),
                        radial-gradient(circle at 70% 60%, rgba(236,72,153,0.06), transparent 50%);
            z-index: 0; pointer-events: none;
        }
        .glass {
            background: rgba(20, 20, 40, 0.6);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
        }
        .glass-strong {
            background: rgba(25, 25, 50, 0.7);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 20px;
        }
        button {
            padding: 10px 20px;
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            border: none; border-radius: 50px; color: #fff;
            font-weight: 600; font-size: 13px; cursor: pointer;
            transition: all 0.2s;
        }
        button:active { transform: scale(0.96); }
        button.secondary {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
        }
        button.danger { background: linear-gradient(135deg, #ef4444, #dc2626); }
        button.demo {
            background: rgba(139,92,246,0.15);
            border: 1px solid rgba(139,92,246,0.25);
            font-size: 12px; padding: 8px 16px;
        }
        input, textarea {
            width: 100%; padding: 12px 16px; margin: 6px 0;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 14px; color: #fff; font-size: 14px;
            outline: none; transition: all 0.2s;
        }
        input:focus, textarea:focus {
            border-color: #8b5cf6;
            box-shadow: 0 0 0 3px rgba(139,92,246,0.15);
        }
        textarea { resize: none; min-height: 70px; }
        .hidden { display: none !important; }
        .avatar {
            width: 44px; height: 44px; border-radius: 14px;
            object-fit: cover; flex-shrink: 0;
        }
        .status-dot {
            width: 8px; height: 8px; border-radius: 50%;
            display: inline-block; margin-right: 5px;
        }
        .online { background: #10b981; box-shadow: 0 0 8px #10b981; }
        .offline { background: #6b7280; }
        .user-row {
            display: flex; align-items: center; gap: 12px;
            padding: 12px; margin: 4px 0;
            background: rgba(255,255,255,0.02);
            border-radius: 16px; cursor: pointer;
            transition: all 0.15s; border: 1px solid transparent;
        }
        .user-row:hover { background: rgba(139,92,246,0.1); }
        .user-row.active {
            background: rgba(139,92,246,0.2);
            border-color: rgba(139,92,246,0.3);
        }
        .msg-bubble {
            padding: 10px 14px; border-radius: 18px;
            max-width: 75%; word-wrap: break-word;
            animation: msgIn 0.2s ease;
        }
        @keyframes msgIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Desktop */
        @media (min-width: 769px) {
            .layout {
                display: flex; min-height: 100vh;
                padding: 15px; gap: 15px; position: relative; z-index: 1;
            }
            .sidebar {
                width: 330px; display: flex; flex-direction: column;
                gap: 10px; flex-shrink: 0;
            }
            .main { flex: 1; display: flex; flex-direction: column; gap: 10px; }
            .chat-list-box { flex: 1; overflow-y: auto; padding: 15px; }
            .chat-area-box { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 8px; }
            .input-row { display: flex; gap: 8px; padding: 12px; }
            .mobile-only { display: none !important; }
            #mobileApp { display: none !important; }
        }
        
        /* Mobile */
        @media (max-width: 768px) {
            .pc-only { display: none !important; }
            #authBox { margin: 15px; }
            #desktopApp { display: none !important; }
            #mobileApp {
                display: flex; flex-direction: column;
                min-height: 100vh; position: relative; z-index: 1;
                padding: 10px; padding-bottom: 130px;
            }
            .mobile-screen { flex: 1; overflow-y: auto; }
            .mobile-nav {
                position: fixed; bottom: 0; left: 0; right: 0;
                display: flex; justify-content: space-around; padding: 8px 20px;
                background: rgba(15,15,30,0.8);
                backdrop-filter: blur(25px);
                -webkit-backdrop-filter: blur(25px);
                border-top: 1px solid rgba(255,255,255,0.08);
                z-index: 10;
            }
            .nav-item {
                display: flex; flex-direction: column; align-items: center;
                gap: 2px; padding: 6px 14px; border-radius: 50px;
                background: transparent; border: none; color: #6b7280;
                font-size: 10px; font-weight: 500; cursor: pointer;
                transition: all 0.2s;
            }
            .nav-item.active { color: #8b5cf6; }
            .nav-item .icon { font-size: 20px; }
            .mobile-msg-input {
                position: fixed; bottom: 70px; left: 10px; right: 10px;
                display: flex; gap: 8px; padding: 8px; z-index: 5;
            }
            .mobile-msg-input input { font-size: 15px; }
        }
    </style>
</head>
<body>

<!-- АВТОРИЗАЦИЯ -->
<div id="authScreen" style="position:relative;z-index:1;min-height:100vh;display:flex;align-items:center;justify-content:center;">
    <div id="authBox" class="glass-strong" style="width:100%;max-width:400px;padding:30px;">
        <div style="text-align:center;margin-bottom:25px;">
            <h1 style="font-size:36px;background:linear-gradient(135deg,#a78bfa,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">💬 Millow</h1>
            <p style="color:#9ca3af;font-size:13px;margin-top:6px;" id="authTitle">Login to continue</p>
        </div>
        <div style="display:flex;gap:8px;justify-content:center;margin-bottom:15px;flex-wrap:wrap;">
            <button class="demo" onclick="quickLogin('taran@millow.com','fastyk26tyr')">👤 TARAN</button>
            <button class="demo" onclick="quickLogin('test@millow.com','test123')">👤 Test</button>
        </div>
        <div style="text-align:center;color:#4b5563;font-size:11px;margin-bottom:12px;">or manually</div>
        <input type="text" id="regName" placeholder="Full Name" class="hidden">
        <input type="email" id="email" placeholder="Email">
        <input type="password" id="password" placeholder="Password">
        <div style="display:flex;gap:8px;margin-top:15px;">
            <button onclick="handleAuth()" id="authBtn" style="flex:1;">Login</button>
            <button onclick="toggleAuth()" id="toggleBtn" class="secondary">Register</button>
        </div>
        <p id="authError" style="color:#ef4444;text-align:center;margin-top:10px;font-size:12px;"></p>
    </div>
</div>

<!-- ДЕСКТОП -->
<div id="desktopApp" class="hidden layout pc-only">
    <div class="sidebar">
        <div class="glass-strong" style="padding:15px;text-align:center;">
            <h2 style="background:linear-gradient(135deg,#a78bfa,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">💬 Millow</h2>
            <div style="display:flex;gap:6px;margin-top:10px;">
                <button onclick="switchTab('chats')" id="tabChats" style="flex:1;font-size:11px;">Chats</button>
                <button onclick="switchTab('users')" id="tabUsers" class="secondary" style="flex:1;font-size:11px;">Users</button>
                <button onclick="switchTab('profile')" id="tabProfile" class="secondary" style="flex:1;font-size:11px;">Profile</button>
            </div>
        </div>
        <div class="chat-list-box glass" id="chatList" style="display:flex;flex-direction:column;"></div>
        <div class="glass-strong" style="padding:12px;display:flex;align-items:center;gap:10px;">
            <img id="miniAvatar" class="avatar" src="">
            <div style="flex:1;font-size:13px;"><b id="miniName"></b><br><span style="color:#10b981;font-size:11px;">Online</span></div>
            <button onclick="logout()" class="danger" style="padding:6px 12px;font-size:11px;">Exit</button>
        </div>
    </div>
    <div class="main">
        <!-- CHATS TAB -->
        <div id="desktopChats">
            <div class="glass-strong" style="padding:12px 20px;"><b id="chatTitleD">Select a chat</b></div>
            <div class="chat-area-box glass" id="chatAreaD"><p style="color:#6b7280;text-align:center;margin-top:60px;">👋 Select a user</p></div>
            <div class="input-row glass-strong">
                <input type="text" id="msgInputD" placeholder="Type a message..." onkeypress="if(event.key==='Enter')sendMsg()">
                <button onclick="sendMsg()">Send</button>
            </div>
        </div>
        <!-- USERS TAB -->
        <div id="desktopUsers" class="hidden">
            <div class="glass-strong" style="padding:20px;">
                <input type="text" placeholder="Search users..." oninput="renderUserList()" id="userSearchD">
                <div id="userListD" style="margin-top:10px;max-height:500px;overflow-y:auto;"></div>
            </div>
        </div>
        <!-- PROFILE TAB -->
        <div id="desktopProfile" class="hidden">
            <div class="glass-strong" style="padding:25px;text-align:center;">
                <img id="profilePicD" class="avatar" style="width:90px;height:90px;border-radius:50%;margin-bottom:10px;" src="">
                <input type="file" id="avatarFileD" accept="image/*" style="display:none;" onchange="uploadAvatar()">
                <button onclick="document.getElementById('avatarFileD').click()" class="secondary" style="margin-bottom:15px;">Change Photo</button>
                <input type="text" id="profileNameD" placeholder="Name">
                <input type="email" id="profileEmailD" placeholder="Email">
                <textarea id="profileBioD" placeholder="Bio"></textarea>
                <input type="tel" id="profilePhoneD" placeholder="Phone">
                <div style="display:flex;gap:8px;margin-top:15px;">
                    <button onclick="saveProfile()" style="flex:1;">Save</button>
                    <button onclick="switchTab('chats')" class="secondary" style="flex:1;">Cancel</button>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- МОБИЛЬНЫЙ -->
<div id="mobileApp" class="hidden">
    <div class="mobile-screen" id="mobileScreen"></div>
    <div class="mobile-nav">
        <button class="nav-item active" onclick="mobSwitch('chats')" id="mobNavChats"><span class="icon">💬</span>Chats</button>
        <button class="nav-item" onclick="mobSwitch('users')" id="mobNavUsers"><span class="icon">👥</span>Users</button>
        <button class="nav-item" onclick="mobSwitch('profile')" id="mobNavProfile"><span class="icon">👤</span>Profile</button>
    </div>
    <div class="mobile-msg-input glass-strong hidden" id="mobInputBar">
        <input type="text" id="msgInputM" placeholder="Message..." onkeypress="if(event.key==='Enter')sendMsg()">
        <button onclick="sendMsg()">Send</button>
    </div>
</div>

<script>
// ============ STATE ============
const API = location.origin;
let token = localStorage.getItem('mt');
let user = JSON.parse(localStorage.getItem('mu')||'null');
let isLogin = true;
let ws = null;
let currentChat = null;
let allUsers = [];
let allChats = [];
let allMessages = [];
let currentTab = 'chats';
let mobTab = 'chats';

// ============ AUTH ============
if(token && user) { boot(); }

function quickLogin(e,p) { document.getElementById('email').value=e; document.getElementById('password').value=p; handleAuth(); }

function toggleAuth() {
    isLogin = !isLogin;
    document.getElementById('regName').classList.toggle('hidden', isLogin);
    document.getElementById('authTitle').textContent = isLogin ? 'Login to continue' : 'Create account';
    document.getElementById('authBtn').textContent = isLogin ? 'Login' : 'Register';
    document.getElementById('toggleBtn').textContent = isLogin ? 'Create Account' : 'Back to Login';
}

async function handleAuth() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const name = document.getElementById('regName').value.trim();
    if(!email||!password) return err('Fill all fields');
    
    const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
    const body = isLogin ? {email,password} : {name,email,password};
    
    try {
        const r = await fetch(API+endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const d = await r.json();
        if(!r.ok) throw new Error(d.detail||'Error');
        token = d.token; user = d.user;
        localStorage.setItem('mt', token); localStorage.setItem('mu', JSON.stringify(user));
        boot();
    } catch(e) { err(e.message); }
}

function err(msg) { document.getElementById('authError').textContent = msg; setTimeout(()=>document.getElementById('authError').textContent='',3000); }

// ============ BOOT ============
function boot() {
    document.getElementById('authScreen').classList.add('hidden');
    document.getElementById('desktopApp').classList.remove('hidden');
    document.getElementById('mobileApp').classList.remove('hidden');
    document.getElementById('miniAvatar').src = user.avatar;
    document.getElementById('miniName').textContent = user.name;
    connectWS();
    loadAll();
    switchTab('chats');
    mobSwitch('chats');
}

function logout() { localStorage.clear(); location.reload(); }

// ============ DATA ============
async function loadAll() { await loadUsers(); await loadChats(); }

async function loadUsers() {
    try {
        const r = await fetch(API+'/api/users', {headers:{'Authorization':'Bearer '+token}});
        allUsers = await r.json() || [];
        renderUserList();
        renderMobile();
    } catch(e) {}
}

async function loadChats() {
    try {
        const r = await fetch(API+'/api/chats', {headers:{'Authorization':'Bearer '+token}});
        const newChats = await r.json() || [];
        if(JSON.stringify(newChats) !== JSON.stringify(allChats)) {
            allChats = newChats;
            renderChatList();
            renderMobile();
        }
    } catch(e) {}
}

async function loadMessages() {
    if(!currentChat) return;
    try {
        const r = await fetch(API+'/api/messages/'+currentChat.id, {headers:{'Authorization':'Bearer '+token}});
        const newMsgs = await r.json() || [];
        if(JSON.stringify(newMsgs) !== JSON.stringify(allMessages)) {
            allMessages = newMsgs;
            renderMessages();
        }
    } catch(e) {}
}

// ============ RENDER ============
function renderChatList() {
    const container = document.getElementById('chatList');
    if(!container) return;
    container.innerHTML = allChats.length ? allChats.map(c => {
        if(!c.otherUser) return '';
        return `<div class="user-row ${currentChat?.id===c.id?'active':''}" onclick="openChat('${c.id}')">
            <img src="${c.otherUser.avatar}" class="avatar" onerror="this.src='https://ui-avatars.com/api/?name=U&background=8B5CF6&color=fff'">
            <div style="flex:1;min-width:0;">
                <b style="font-size:13px;">${c.otherUser.name}</b>
                <p style="color:#6b7280;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${c.lastMessage?.content||'No messages'}</p>
            </div>
            <span class="status-dot ${c.otherUser.online?'online':'offline'}"></span>
        </div>`;
    }).join('') : '<p style="color:#6b7280;text-align:center;padding:30px;">No chats yet</p>';
}

function renderUserList() {
    const container = document.getElementById('userListD');
    if(!container) return;
    const s = (document.getElementById('userSearchD')?.value||'').toLowerCase();
    const filtered = allUsers.filter(u => u.name.toLowerCase().includes(s));
    container.innerHTML = filtered.length ? filtered.map(u => `<div class="user-row" onclick="startChatUser('${u.id}')">
        <img src="${u.avatar}" class="avatar">
        <div style="flex:1;"><b style="font-size:13px;">${u.name}</b><br><span style="color:#6b7280;font-size:11px;"><span class="status-dot ${u.online?'online':'offline'}"></span>${u.online?'Online':'Offline'}</span></div>
    </div>`).join('') : '<p style="color:#6b7280;text-align:center;">No users</p>';
}

function renderMessages() {
    const areaD = document.getElementById('chatAreaD');
    const html = allMessages.length ? allMessages.map(m => {
        const isOwn = m.senderId === user.id;
        return `<div style="display:flex;flex-direction:column;align-items:${isOwn?'flex-end':'flex-start'};">
            <div class="msg-bubble" style="background:${isOwn?'linear-gradient(135deg,#8b5cf6,#7c3aed)':'rgba(255,255,255,0.06)'};${isOwn?'border-bottom-right-radius:6px;':'border-bottom-left-radius:6px;'}">
                ${!isOwn?`<div style="font-size:10px;color:#8b5cf6;margin-bottom:3px;">${m.sender?.name||''}</div>`:''}
                ${m.content}
                <div style="font-size:9px;color:rgba(255,255,255,0.3);margin-top:3px;text-align:right;">${new Date(m.timestamp).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</div>
            </div>
        </div>`;
    }).join('') : '<p style="color:#6b7280;text-align:center;margin-top:50px;">No messages yet 👋</p>';
    
    if(areaD) { areaD.innerHTML = html; areaD.scrollTop = areaD.scrollHeight; }
    
    // Mobile chat view
    if(currentChat && mobTab==='chats') renderMobileChat();
}

function renderMobile() {
    const screen = document.getElementById('mobileScreen');
    if(!screen) return;
    
    if(mobTab === 'chats' && !currentChat) {
        screen.innerHTML = '<div style="padding:5px;">' + (allChats.length ? allChats.map(c => {
            if(!c.otherUser) return '';
            return `<div class="user-row" onclick="openChat('${c.id}')">
                <img src="${c.otherUser.avatar}" class="avatar">
                <div style="flex:1;min-width:0;"><b>${c.otherUser.name}</b><p style="color:#6b7280;font-size:11px;">${(c.lastMessage?.content||'No messages').substring(0,30)}</p></div>
                <span class="status-dot ${c.otherUser.online?'online':'offline'}"></span>
            </div>`;
        }).join('') : '<p style="color:#6b7280;text-align:center;padding:40px;">No chats</p>') + '</div>';
    } else if(mobTab === 'chats' && currentChat) {
        renderMobileChat();
    } else if(mobTab === 'users') {
        screen.innerHTML = '<div style="padding:5px;">' + (allUsers.length ? allUsers.map(u => `<div class="user-row" onclick="startChatUser('${u.id}')">
            <img src="${u.avatar}" class="avatar"><div style="flex:1;"><b>${u.name}</b><br><span style="color:#6b7280;font-size:11px;">${u.online?'Online':'Offline'}</span></div>
        </div>`).join('') : '<p style="color:#6b7280;text-align:center;padding:40px;">No users</p>') + '</div>';
    } else if(mobTab === 'profile') {
        screen.innerHTML = `<div class="glass-strong" style="padding:20px;text-align:center;">
            <img src="${user.avatar}" style="width:80px;height:80px;border-radius:50%;margin-bottom:10px;">
            <h3>${user.name}</h3><p style="color:#9ca3af;">${user.email}</p>
            <button onclick="logout()" class="danger" style="width:100%;margin-top:15px;">Logout</button>
        </div>`;
    }
}

function renderMobileChat() {
    const screen = document.getElementById('mobileScreen');
    if(!screen || !currentChat) return;
    const msgsHtml = allMessages.length ? allMessages.map(m => {
        const isOwn = m.senderId === user.id;
        return `<div style="display:flex;flex-direction:column;align-items:${isOwn?'flex-end':'flex-start'};">
            <div class="msg-bubble" style="background:${isOwn?'linear-gradient(135deg,#8b5cf6,#7c3aed)':'rgba(255,255,255,0.06)'};max-width:85%;">
                ${!isOwn?`<div style="font-size:10px;color:#8b5cf6;margin-bottom:2px;">${m.sender?.name||''}</div>`:''}
                ${m.content}
                <div style="font-size:9px;color:rgba(255,255,255,0.3);margin-top:2px;text-align:right;">${new Date(m.timestamp).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</div>
            </div>
        </div>`;
    }).join('') : '<p style="color:#6b7280;text-align:center;margin-top:50px;">No messages 👋</p>';
    
    screen.innerHTML = `
        <div style="padding:8px;display:flex;justify-content:space-between;align-items:center;" class="glass-strong">
            <b>${currentChat.otherUser?.name||'Chat'}</b>
            <button onclick="closeMobileChat()" style="padding:5px 12px;font-size:11px;">← Back</button>
        </div>
        <div style="padding:10px;display:flex;flex-direction:column;gap:8px;min-height:200px;">${msgsHtml}</div>
    `;
    document.getElementById('mobInputBar').classList.remove('hidden');
    setTimeout(() => {
        const area = screen.querySelector('div:last-child');
        if(area) area.scrollTop = area.scrollHeight;
    }, 100);
}

function closeMobileChat() {
    currentChat = null;
    allMessages = [];
    document.getElementById('mobInputBar').classList.add('hidden');
    renderMobile();
}

// ============ ACTIONS ============
function switchTab(tab) {
    currentTab = tab;
    document.getElementById('desktopChats').classList.toggle('hidden', tab!=='chats');
    document.getElementById('desktopUsers').classList.toggle('hidden', tab!=='users');
    document.getElementById('desktopProfile').classList.toggle('hidden', tab!=='profile');
    
    ['tabChats','tabUsers','tabProfile'].forEach((id,i) => {
        const btn = document.getElementById(id);
        if(btn) btn.className = tab===['chats','users','profile'][i] ? '' : 'secondary';
    });
    
    if(tab==='users') renderUserList();
    if(tab==='profile') {
        document.getElementById('profilePicD').src = user.avatar;
        document.getElementById('profileNameD').value = user.name||'';
        document.getElementById('profileEmailD').value = user.email||'';
        document.getElementById('profileBioD').value = user.bio||'';
        document.getElementById('profilePhoneD').value = user.phone||'';
    }
}

function mobSwitch(tab) {
    mobTab = tab;
    currentChat = null;
    allMessages = [];
    document.getElementById('mobInputBar').classList.add('hidden');
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.getElementById('mobNav'+tab.charAt(0).toUpperCase()+tab.slice(1)).classList.add('active');
    renderMobile();
}

async function startChatUser(uid) {
    try {
        const r = await fetch(API+'/api/chats', {method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify({participantId:uid})});
        currentChat = await r.json();
        allMessages = [];
        await loadMessages();
        if(!document.getElementById('mobileApp').classList.contains('hidden')) mobSwitch('chats');
        switchTab('chats');
        renderChatList();
    } catch(e) {}
}

function openChat(chatId) {
    currentChat = allChats.find(c => c.id===chatId) || currentChat;
    if(!currentChat) return;
    allMessages = [];
    document.getElementById('chatTitleD').textContent = '💬 ' + (currentChat.otherUser?.name||'Chat');
    loadMessages();
    renderChatList();
    if(!document.getElementById('mobileApp').classList.contains('hidden')) renderMobileChat();
}

async function sendMsg() {
    const input = document.getElementById('msgInputD') || document.getElementById('msgInputM');
    if(!input) return;
    const content = input.value.trim();
    if(!content || !currentChat) return;
    input.value = '';
    
    if(ws && ws.readyState===WebSocket.OPEN) {
        ws.send(JSON.stringify({type:'private-message',chatId:currentChat.id,senderId:user.id,content}));
    }
    // Оптимистичное обновление
    const tempMsg = {
        id: Date.now().toString(),
        chatId: currentChat.id,
        senderId: user.id,
        content: content,
        timestamp: new Date().toISOString(),
        sender: user
    };
    allMessages.push(tempMsg);
    renderMessages();
    setTimeout(loadMessages, 500);
}

async function saveProfile() {
    const body = {
        name: document.getElementById('profileNameD').value,
        email: document.getElementById('profileEmailD').value,
        bio: document.getElementById('profileBioD').value,
        phone: document.getElementById('profilePhoneD').value
    };
    try {
        const r = await fetch(API+'/api/users/profile', {method:'PUT',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify(body)});
        if(r.ok) {
            user = await r.json();
            localStorage.setItem('mu', JSON.stringify(user));
            document.getElementById('miniAvatar').src = user.avatar;
            document.getElementById('miniName').textContent = user.name;
            switchTab('chats');
        }
    } catch(e) {}
}

async function uploadAvatar() {
    const file = document.getElementById('avatarFileD').files[0];
    if(!file) return;
    const fd = new FormData(); fd.append('avatar', file);
    const r = await fetch(API+'/api/users/avatar', {method:'POST',headers:{'Authorization':'Bearer '+token},body:fd});
    if(r.ok) {
        const d = await r.json();
        user.avatar = API + d.url;
        localStorage.setItem('mu', JSON.stringify(user));
        document.getElementById('profilePicD').src = user.avatar;
        document.getElementById('miniAvatar').src = user.avatar;
    }
}

// ============ WEBSOCKET ============
function connectWS() {
    if(!token||!user) return;
    try {
        const proto = location.protocol==='https:'?'wss':'ws';
        ws = new WebSocket(proto+'://'+location.host+'/ws');
        ws.onopen = () => ws.send(JSON.stringify({type:'login',userId:user.id}));
        ws.onmessage = (e) => {
            const d = JSON.parse(e.data);
            if(d.type==='private-message') {
                if(currentChat && d.chatId===currentChat.id) loadMessages();
                loadChats();
            }
            if(d.type==='user-status') { loadUsers(); loadChats(); }
        };
        ws.onclose = () => setTimeout(connectWS, 3000);
    } catch(e) { setTimeout(connectWS, 3000); }
}

// ============ AUTO-REFRESH (плавный) ============
setInterval(() => {
    if(token && user) {
        loadChats();
        if(currentChat) loadMessages();
    }
}, 3000);

loadAll();
</script>
</body>
</html>"""

# ============ API ============
@app.get("/", response_class=HTMLResponse)
async def home(): return HTML_PAGE

@app.post("/api/auth/register")
async def register(data: UserRegister):
    for u in users_db.values():
        if u["email"] == data.email: raise HTTPException(400, "User already exists")
    uid = str(uuid.uuid4())
    users_db[uid] = {
        "id":uid,"name":data.name,"email":data.email,"password":hash_password(data.password),
        "avatar":f"https://ui-avatars.com/api/?name={data.name}&background=8B5CF6&color=fff&size=200&bold=true",
        "bio":"Hey there! 💜","phone":"","online":False,"lastSeen":datetime.utcnow().isoformat(),"createdAt":datetime.utcnow().isoformat()
    }
    token = create_token(uid)
    return {"token":token,"user":{k:v for k,v in users_db[uid].items() if k!="password"}}

@app.post("/api/auth/login")
async def login(data: UserLogin):
    user = next((u for u in users_db.values() if u["email"]==data.email), None)
    if not user or user["password"]!=hash_password(data.password): raise HTTPException(401, "Invalid credentials")
    token = create_token(user["id"])
    return {"token":token,"user":{k:v for k,v in user.items() if k!="password"}}

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
            result.append({**c,"otherUser":{k:v for k,v in other.items() if k!="password"} if other else None})
    return sorted(result, key=lambda x: x.get("updatedAt",""), reverse=True)

@app.post("/api/chats")
async def create_chat(data: ChatCreate, authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    for c in chats_db.values():
        if payload["user_id"] in c["participants"] and data.participantId in c["participants"]:
            other = users_db.get(data.participantId, {})
            return {**c,"otherUser":{k:v for k,v in other.items() if k!="password"} if other else None}
    cid = str(uuid.uuid4())
    chats_db[cid] = {"id":cid,"participants":[payload["user_id"],data.participantId],"isGroup":False,"createdAt":datetime.utcnow().isoformat(),"updatedAt":datetime.utcnow().isoformat(),"lastMessage":None}
    other = users_db.get(data.participantId, {})
    return {**chats_db[cid],"otherUser":{k:v for k,v in other.items() if k!="password"} if other else None}

@app.get("/api/messages/{chat_id}")
async def get_messages(chat_id: str, authorization: str = Header(None)):
    payload = verify_token(authorization.split(" ")[1] if authorization else "")
    if not payload: raise HTTPException(401)
    result = []
    for m in messages_db:
        if m["chatId"]==chat_id:
            sender = users_db.get(m["senderId"], {})
            result.append({**m,"sender":{k:v for k,v in sender.items() if k!="password"} if sender else None})
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
    with open(f"uploads/avatars/{fname}", "wb") as f: f.write(await avatar.read())
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
                for u_id, w in online_users.items():
                    if u_id!=uid:
                        try: await w.send_text(json.dumps({"type":"user-status","userId":uid,"online":True}))
                        except: pass
            elif data.get("type")=="private-message":
                msg = {"id":str(uuid.uuid4()),"chatId":data["chatId"],"senderId":data["senderId"],"content":data["content"],"type":"text","timestamp":datetime.utcnow().isoformat(),"read":False}
                messages_db.append(msg)
                if data["chatId"] in chats_db:
                    chats_db[data["chatId"]]["lastMessage"] = msg
                    chats_db[data["chatId"]]["updatedAt"] = datetime.utcnow().isoformat()
                sender = users_db.get(data["senderId"], {})
                msg_s = {**msg,"sender":{k:v for k,v in sender.items() if k!="password"} if sender else None}
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
            for u_id, w in online_users.items():
                try: await w.send_text(json.dumps({"type":"user-status","userId":uid,"online":False}))
                except: pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    uvicorn.run(app, host="0.0.0.0", port=port)