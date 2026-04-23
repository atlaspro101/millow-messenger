from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import json
import os
import uuid
import asyncio
import pathlib

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хранилище данных (в памяти)
users_db = {}
chats_db = {}
messages_db = []

# Онлайн пользователи
online_users = {}
websocket_connections = {}

# Модели данных
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

# Функции для работы с JWT
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

# Создание папок для файлов
os.makedirs("uploads/avatars", exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ============ HTML ИНТЕРФЕЙС ============

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Millow Messenger</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        .container {
            max-width: 900px;
            margin: 20px;
            width: 100%;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 56px;
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: none;
        }
        .subtitle {
            color: #a78bfa;
            font-size: 16px;
            margin-top: 10px;
        }
        .card {
            background: rgba(31, 41, 55, 0.6);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        .card:hover {
            border-color: rgba(139, 92, 246, 0.3);
        }
        input, textarea, select {
            width: 100%;
            padding: 16px;
            margin: 10px 0;
            background: rgba(55, 65, 81, 0.6);
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            color: white;
            font-size: 15px;
            outline: none;
            transition: all 0.3s ease;
        }
        input:focus, textarea:focus, select:focus {
            border-color: #8b5cf6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2);
        }
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        button {
            padding: 14px 32px;
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            border: none;
            border-radius: 50px;
            color: white;
            font-weight: 600;
            font-size: 15px;
            cursor: pointer;
            margin: 8px 4px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(139, 92, 246, 0.5);
        }
        button:active {
            transform: translateY(0);
        }
        button.secondary {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
        }
        button.danger {
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }
        .chat-layout {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .sidebar {
            flex: 1;
            min-width: 250px;
        }
        .main-chat {
            flex: 2;
            min-width: 300px;
        }
        .chat-area {
            max-height: 400px;
            overflow-y: auto;
            margin: 15px 0;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .message {
            padding: 12px 18px;
            border-radius: 20px;
            max-width: 75%;
            animation: slideIn 0.3s ease;
            word-wrap: break-word;
        }
        .message.own {
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            align-self: flex-end;
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.other {
            background: rgba(55, 65, 81, 0.8);
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .message-time {
            font-size: 10px;
            color: rgba(255,255,255,0.5);
            margin-top: 6px;
            text-align: right;
        }
        .message-sender {
            font-size: 11px;
            color: rgba(255,255,255,0.6);
            margin-bottom: 4px;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            margin: 8px 0;
            background: rgba(55,65,81,0.4);
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .user-item:hover {
            background: rgba(139, 92, 246, 0.3);
            transform: translateX(4px);
        }
        .avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid rgba(139, 92, 246, 0.5);
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 4px;
        }
        .online { background: #10b981; box-shadow: 0 0 10px #10b981; }
        .offline { background: #6b7280; }
        .hidden { display: none !important; }
        .flex { display: flex; }
        .gap-2 { gap: 10px; }
        .items-center { align-items: center; }
        .justify-between { justify-content: space-between; }
        .mt-2 { margin-top: 10px; }
        .mt-4 { margin-top: 20px; }
        .mb-2 { margin-bottom: 10px; }
        .text-sm { font-size: 14px; }
        .text-gray { color: #9ca3af; }
        .text-green { color: #10b981; }
        .text-red { color: #ef4444; }
        .text-center { text-align: center; }
        .font-bold { font-weight: bold; }
        
        /* Profile Styles */
        .profile-avatar {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid #8b5cf6;
            box-shadow: 0 0 30px rgba(139, 92, 246, 0.3);
        }
        
        @media (max-width: 768px) {
            .chat-layout { flex-direction: column; }
            .header h1 { font-size: 40px; }
            input, button { font-size: 14px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 Millow</h1>
            <p class="subtitle">Connect with friends around the world</p>
            <p class="text-sm" style="margin-top: 8px;">
                API: <span id="apiStatus">Checking...</span>
            </p>
        </div>

        <!-- Auth Form -->
        <div class="card" id="authCard">
            <h2 class="mb-2" id="authTitle">Login to Millow</h2>
            <p class="text-gray text-sm mb-2">Enter your credentials to continue</p>
            
            <input type="text" id="nameInput" placeholder="Full Name" class="hidden">
            <input type="email" id="emailInput" placeholder="Email address">
            <input type="password" id="passwordInput" placeholder="Password">
            
            <div class="flex gap-2 mt-4">
                <button onclick="handleAuth()" id="authBtn" style="flex: 1;">Login</button>
                <button onclick="toggleAuth()" id="toggleBtn" class="secondary">Register</button>
            </div>
            
            <div id="authError" class="text-red text-center mt-2 hidden"></div>
        </div>

        <!-- Main Interface -->
        <div id="mainInterface" class="hidden">
            <!-- Navigation -->
            <div class="flex justify-between items-center mb-2">
                <div class="flex gap-2">
                    <button id="navChats" onclick="showSection('chats')" class="secondary">💬 Chats</button>
                    <button id="navUsers" onclick="showSection('users')" class="secondary">👥 Users</button>
                    <button id="navProfile" onclick="showSection('profile')" class="secondary">👤 Profile</button>
                </div>
                <button onclick="logout()" class="danger">🚪 Logout</button>
            </div>

            <!-- Chats Section -->
            <div id="chatsSection">
                <div class="chat-layout">
                    <div class="sidebar">
                        <div class="card">
                            <h3 class="mb-2">Your Chats</h3>
                            <div id="chatsList" style="max-height: 500px; overflow-y: auto;"></div>
                        </div>
                    </div>
                    <div class="main-chat">
                        <div class="card">
                            <div class="flex justify-between items-center mb-2">
                                <h3 id="chatTitle">Select a chat</h3>
                                <button onclick="deleteChat()" class="danger" style="padding: 8px 16px; font-size: 12px;">🗑️</button>
                            </div>
                            <div class="chat-area" id="chatArea">
                                <p class="text-gray text-center">Select a user to start chatting</p>
                            </div>
                            <div class="flex gap-2 mt-4">
                                <input type="text" id="messageInput" placeholder="Type a message..." style="flex: 1;" onkeypress="if(event.key==='Enter') sendMessage()">
                                <button onclick="sendMessage()">📤 Send</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Users Section -->
            <div id="usersSection" class="hidden">
                <div class="card">
                    <h3 class="mb-2">All Users</h3>
                    <input type="text" id="userSearch" placeholder="Search users..." onkeyup="filterUsers()">
                    <div id="usersList" style="max-height: 500px; overflow-y: auto;"></div>
                </div>
            </div>

            <!-- Profile Section -->
            <div id="profileSection" class="hidden">
                <div class="card">
                    <h2 class="mb-2">Edit Profile</h2>
                    <div class="text-center mt-4">
                        <img id="profileAvatar" class="profile-avatar" src="" alt="Avatar">
                        <div class="mt-2">
                            <input type="file" id="avatarFile" accept="image/*" style="display: none;" onchange="uploadAvatar()">
                            <button onclick="document.getElementById('avatarFile').click()" class="secondary">📷 Change Photo</button>
                        </div>
                    </div>
                    <div class="mt-4">
                        <label class="text-sm text-gray">Full Name</label>
                        <input type="text" id="profileName" placeholder="Your name">
                    </div>
                    <div>
                        <label class="text-sm text-gray">Email</label>
                        <input type="email" id="profileEmail" placeholder="your@email.com">
                    </div>
                    <div>
                        <label class="text-sm text-gray">Bio</label>
                        <textarea id="profileBio" placeholder="Tell us about yourself"></textarea>
                    </div>
                    <div>
                        <label class="text-sm text-gray">Phone</label>
                        <input type="tel" id="profilePhone" placeholder="+1234567890">
                    </div>
                    <div class="flex gap-2 mt-4">
                        <button onclick="updateProfile()" style="flex: 1;">💾 Save Changes</button>
                        <button onclick="showSection('chats')" class="secondary" style="flex: 1;">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_URL = window.location.origin;
        let token = localStorage.getItem('token');
        let user = JSON.parse(localStorage.getItem('user') || 'null');
        let isLoginMode = true;
        let socket = null;
        let currentChat = null;
        let allUsers = [];
        let allChats = [];

        // Initialize
        checkAPI();
        if (token && user) {
            showMainInterface();
            connectWebSocket();
        }

        // Auto-refresh messages
        setInterval(() => {
            if (currentChat) loadMessages();
        }, 1000);

        async function checkAPI() {
            try {
                const res = await fetch(API_URL + '/');
                const data = await res.json();
                document.getElementById('apiStatus').innerHTML = 
                    '✅ Connected <span class="text-sm">(' + data.users + ' users, ' + data.chats + ' chats)</span>';
                document.getElementById('apiStatus').style.color = '#10b981';
            } catch (e) {
                document.getElementById('apiStatus').textContent = '❌ Not connected';
                document.getElementById('apiStatus').style.color = '#ef4444';
            }
        }

        function toggleAuth() {
            isLoginMode = !isLoginMode;
            document.getElementById('nameInput').classList.toggle('hidden', isLoginMode);
            document.getElementById('authTitle').textContent = isLoginMode ? 'Login to Millow' : 'Create Account';
            document.getElementById('authBtn').textContent = isLoginMode ? 'Login' : 'Register';
            document.getElementById('toggleBtn').textContent = isLoginMode ? 'Create Account' : 'Back to Login';
        }

        async function handleAuth() {
            const email = document.getElementById('emailInput').value.trim();
            const password = document.getElementById('passwordInput').value;
            const name = document.getElementById('nameInput').value.trim();
            const errorDiv = document.getElementById('authError');
            
            errorDiv.classList.add('hidden');
            
            if (!email || !password) {
                showError('Please fill in all fields');
                return;
            }
            
            const endpoint = isLoginMode ? '/api/auth/login' : '/api/auth/register';
            const body = isLoginMode ? { email, password } : { name, email, password };
            
            try {
                const res = await fetch(API_URL + endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                
                const data = await res.json();
                
                if (!res.ok) {
                    throw new Error(data.detail || 'Authentication failed');
                }
                
                token = data.token;
                user = data.user;
                
                localStorage.setItem('token', token);
                localStorage.setItem('user', JSON.stringify(user));
                
                showMainInterface();
                connectWebSocket();
                loadAllData();
            } catch (err) {
                showError(err.message);
            }
        }

        function showError(msg) {
            const errorDiv = document.getElementById('authError');
            errorDiv.textContent = msg;
            errorDiv.classList.remove('hidden');
            setTimeout(() => errorDiv.classList.add('hidden'), 3000);
        }

        function showMainInterface() {
            document.getElementById('authCard').classList.add('hidden');
            document.getElementById('mainInterface').classList.remove('hidden');
            showSection('chats');
            loadAllData();
        }

        function showSection(section) {
            document.getElementById('chatsSection').classList.add('hidden');
            document.getElementById('usersSection').classList.add('hidden');
            document.getElementById('profileSection').classList.add('hidden');
            
            document.getElementById('navChats').style.background = '';
            document.getElementById('navUsers').style.background = '';
            document.getElementById('navProfile').style.background = '';
            
            if (section === 'chats') {
                document.getElementById('chatsSection').classList.remove('hidden');
                document.getElementById('navChats').style.background = 'linear-gradient(135deg, #8b5cf6, #7c3aed)';
                loadChats();
            } else if (section === 'users') {
                document.getElementById('usersSection').classList.remove('hidden');
                document.getElementById('navUsers').style.background = 'linear-gradient(135deg, #8b5cf6, #7c3aed)';
                loadUsers();
            } else if (section === 'profile') {
                document.getElementById('profileSection').classList.remove('hidden');
                document.getElementById('navProfile').style.background = 'linear-gradient(135deg, #8b5cf6, #7c3aed)';
                loadProfile();
            }
        }

        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            token = null;
            user = null;
            currentChat = null;
            if (socket) socket.close();
            document.getElementById('authCard').classList.remove('hidden');
            document.getElementById('mainInterface').classList.add('hidden');
        }

        async function loadAllData() {
            await loadUsers();
            await loadChats();
        }

        async function loadUsers() {
            try {
                const res = await fetch(API_URL + '/api/users', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                allUsers = await res.json();
                renderUsers();
            } catch (err) {
                console.error('Error loading users:', err);
            }
        }

        function renderUsers() {
            const usersList = document.getElementById('usersList');
            usersList.innerHTML = '';
            
            allUsers.forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                div.innerHTML = `
                    <img src="${u.avatar}" class="avatar" alt="${u.name}">
                    <div style="flex: 1;">
                        <div class="font-bold">${u.name}</div>
                        <div class="text-sm">
                            <span class="status-dot ${u.online ? 'online' : 'offline'}"></span>
                            ${u.online ? 'Online' : 'Offline'}
                        </div>
                    </div>
                `;
                div.onclick = () => startChat(u.id);
                usersList.appendChild(div);
            });
        }

        function filterUsers() {
            const search = document.getElementById('userSearch').value.toLowerCase();
            const filtered = allUsers.filter(u => 
                u.name.toLowerCase().includes(search) || 
                u.email.toLowerCase().includes(search)
            );
            
            const usersList = document.getElementById('usersList');
            usersList.innerHTML = '';
            
            filtered.forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                div.innerHTML = `
                    <img src="${u.avatar}" class="avatar" alt="${u.name}">
                    <div style="flex: 1;">
                        <div class="font-bold">${u.name}</div>
                        <div class="text-sm">
                            <span class="status-dot ${u.online ? 'online' : 'offline'}"></span>
                            ${u.online ? 'Online' : 'Offline'}
                        </div>
                    </div>
                `;
                div.onclick = () => startChat(u.id);
                usersList.appendChild(div);
            });
        }

        async function loadChats() {
            try {
                const res = await fetch(API_URL + '/api/chats', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                allChats = await res.json();
                renderChats();
            } catch (err) {
                console.error('Error loading chats:', err);
            }
        }

        function renderChats() {
            const chatsList = document.getElementById('chatsList');
            chatsList.innerHTML = '';
            
            if (allChats.length === 0) {
                chatsList.innerHTML = '<p class="text-gray text-center">No chats yet. Go to Users to start chatting!</p>';
                return;
            }
            
            allChats.forEach(chat => {
                const otherUser = chat.otherUser;
                if (!otherUser) return;
                
                const div = document.createElement('div');
                div.className = 'user-item';
                div.style.background = currentChat?.id === chat.id ? 'rgba(139, 92, 246, 0.3)' : '';
                div.innerHTML = `
                    <img src="${otherUser.avatar}" class="avatar" alt="${otherUser.name}">
                    <div style="flex: 1;">
                        <div class="font-bold">${otherUser.name}</div>
                        <div class="text-sm text-gray">
                            ${chat.lastMessage?.content?.substring(0, 30) || 'No messages'}
                        </div>
                    </div>
                    <div class="text-sm text-gray">
                        <span class="status-dot ${otherUser.online ? 'online' : 'offline'}"></span>
                    </div>
                `;
                div.onclick = () => selectChat(chat);
                chatsList.appendChild(div);
            });
        }

        async function startChat(otherUserId) {
            try {
                const res = await fetch(API_URL + '/api/chats', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ participantId: otherUserId })
                });
                
                currentChat = await res.json();
                selectChat(currentChat);
                showSection('chats');
            } catch (err) {
                console.error('Error starting chat:', err);
            }
        }

        function selectChat(chat) {
            currentChat = chat;
            document.getElementById('chatTitle').textContent = 
                chat.otherUser ? `Chat with ${chat.otherUser.name}` : 'Chat';
            document.getElementById('chatArea').innerHTML = '';
            loadMessages();
            renderChats();
        }

        async function loadMessages() {
            if (!currentChat) return;
            
            try {
                const res = await fetch(API_URL + '/api/messages/' + currentChat.id, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const messages = await res.json();
                
                const chatArea = document.getElementById('chatArea');
                chatArea.innerHTML = '';
                
                if (messages.length === 0) {
                    chatArea.innerHTML = '<p class="text-gray text-center">No messages yet. Say hello! 👋</p>';
                    return;
                }
                
                messages.forEach(msg => {
                    const isOwn = msg.senderId === user.id;
                    const div = document.createElement('div');
                    div.className = `message ${isOwn ? 'own' : 'other'}`;
                    div.innerHTML = `
                        ${!isOwn ? `<div class="message-sender">${msg.sender?.name || 'Unknown'}</div>` : ''}
                        ${msg.content}
                        <div class="message-time">${new Date(msg.timestamp).toLocaleTimeString()}</div>
                    `;
                    chatArea.appendChild(div);
                });
                
                chatArea.scrollTop = chatArea.scrollHeight;
            } catch (err) {
                console.error('Error loading messages:', err);
            }
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const content = input.value.trim();
            
            if (!content || !currentChat) return;
            
            input.value = '';
            
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'private-message',
                    chatId: currentChat.id,
                    senderId: user.id,
                    content: content
                }));
            }
            
            // Load messages after short delay
            setTimeout(loadMessages, 300);
        }

        function deleteChat() {
            if (currentChat && confirm('Delete this chat?')) {
                currentChat = null;
                document.getElementById('chatArea').innerHTML = '<p class="text-gray text-center">Select a user to start chatting</p>';
                document.getElementById('chatTitle').textContent = 'Select a chat';
                renderChats();
            }
        }

        function loadProfile() {
            document.getElementById('profileAvatar').src = user.avatar;
            document.getElementById('profileName').value = user.name;
            document.getElementById('profileEmail').value = user.email;
            document.getElementById('profileBio').value = user.bio || '';
            document.getElementById('profilePhone').value = user.phone || '';
        }

        async function updateProfile() {
            const name = document.getElementById('profileName').value.trim();
            const email = document.getElementById('profileEmail').value.trim();
            const bio = document.getElementById('profileBio').value.trim();
            const phone = document.getElementById('profilePhone').value.trim();
            
            try {
                const res = await fetch(API_URL + '/api/users/profile', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ name, email, bio, phone })
                });
                
                const updatedUser = await res.json();
                user = updatedUser;
                localStorage.setItem('user', JSON.stringify(user));
                
                alert('Profile updated successfully! ✅');
                showSection('chats');
            } catch (err) {
                alert('Error updating profile: ' + err.message);
            }
        }

        async function uploadAvatar() {
            const file = document.getElementById('avatarFile').files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('avatar', file);
            
            try {
                const res = await fetch(API_URL + '/api/users/avatar', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                });
                
                const data = await res.json();
                
                user.avatar = API_URL + data.url;
                localStorage.setItem('user', JSON.stringify(user));
                document.getElementById('profileAvatar').src = user.avatar;
                
                alert('Avatar updated! 📸');
            } catch (err) {
                alert('Error uploading avatar: ' + err.message);
            }
        }

        function connectWebSocket() {
            if (!token || !user) return;
            
            const wsUrl = (API_URL.startsWith('https') ? 'wss://' : 'ws://') + 
                         API_URL.replace('https://', '').replace('http://', '') + '/ws';
            
            socket = new WebSocket(wsUrl);
            
            socket.onopen = () => {
                console.log('WebSocket connected');
                socket.send(JSON.stringify({
                    type: 'login',
                    userId: user.id
                }));
            };
            
            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'private-message') {
                    if (currentChat && data.chatId === currentChat.id) {
                        loadMessages();
                    }
                    loadChats();
                } else if (data.type === 'user-status') {
                    loadUsers();
                }
            };
            
            socket.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            socket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
    </script>
</body>
</html>
"""

# ============ API ENDPOINTS ============

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLContent

@app.get("/api/test")
async def test():
    return {
        "message": "API is working!",
        "usersCount": len(users_db),
        "onlineUsers": len(online_users),
        "chatsCount": len(chats_db),
        "messagesCount": len(messages_db)
    }

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    print(f"📝 Register attempt: {user_data.email}")
    
    for user in users_db.values():
        if user["email"] == user_data.email:
            raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = pwd_context.hash(user_data.password)
    user_id = str(uuid.uuid4())
    avatar_url = f"https://ui-avatars.com/api/?name={user_data.name}&background=8B5CF6&color=fff&size=200"
    
    user = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password": hashed_password,
        "avatar": avatar_url,
        "bio": "Hey there! I am using Millow",
        "phone": "",
        "online": False,
        "lastSeen": datetime.utcnow().isoformat(),
        "createdAt": datetime.utcnow().isoformat()
    }
    
    users_db[user_id] = user
    print(f"✅ User registered: {user_data.email}")
    
    token = create_token({"id": user_id, "email": user_data.email})
    
    user_response = user.copy()
    del user_response["password"]
    
    return {"token": token, "user": user_response}

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    print(f"🔑 Login attempt: {user_data.email}")
    
    user = None
    for u in users_db.values():
        if u["email"] == user_data.email:
            user = u
            break
    
    if not user or not pwd_context.verify(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    print(f"✅ User logged in: {user_data.email}")
    
    token = create_token({"id": user["id"], "email": user["email"]})
    
    user_response = user.copy()
    del user_response["password"]
    
    return {"token": token, "user": user_response}

@app.get("/api/users")
async def get_users(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    current_user_id = payload["id"]
    
    users_list = []
    for user in users_db.values():
        if user["id"] != current_user_id:
            user_response = user.copy()
            del user_response["password"]
            users_list.append(user_response)
    
    return users_list

@app.get("/api/chats")
async def get_chats(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    current_user_id = payload["id"]
    
    user_chats = []
    for chat in chats_db.values():
        if current_user_id in chat.get("participants", []):
            other_user_id = None
            for pid in chat["participants"]:
                if pid != current_user_id:
                    other_user_id = pid
                    break
            
            other_user = None
            if other_user_id and other_user_id in users_db:
                u = users_db[other_user_id]
                other_user = {
                    "id": u["id"],
                    "name": u["name"],
                    "avatar": u["avatar"],
                    "online": u.get("online", False),
                    "lastSeen": u.get("lastSeen")
                }
            
            user_chats.append({**chat, "otherUser": other_user})
    
    user_chats.sort(key=lambda x: x.get("updatedAt", x.get("createdAt", "")), reverse=True)
    return user_chats

@app.post("/api/chats")
async def create_chat(chat_data: ChatCreate, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    current_user_id = payload["id"]
    participant_id = chat_data.participantId
    
    for chat in chats_db.values():
        if (current_user_id in chat.get("participants", []) and 
            participant_id in chat.get("participants", []) and 
            not chat.get("isGroup")):
            
            other_user = None
            if participant_id in users_db:
                u = users_db[participant_id]
                other_user = {
                    "id": u["id"],
                    "name": u["name"],
                    "avatar": u["avatar"],
                    "online": u.get("online", False),
                    "lastSeen": u.get("lastSeen")
                }
            
            return {**chat, "otherUser": other_user}
    
    chat_id = str(uuid.uuid4())
    chat = {
        "id": chat_id,
        "participants": [current_user_id, participant_id],
        "isGroup": False,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
        "lastMessage": None
    }
    
    chats_db[chat_id] = chat
    
    other_user = None
    if participant_id in users_db:
        u = users_db[participant_id]
        other_user = {
            "id": u["id"],
            "name": u["name"],
            "avatar": u["avatar"],
            "online": u.get("online", False),
            "lastSeen": u.get("lastSeen")
        }
    
    return {**chat, "otherUser": other_user}

@app.get("/api/messages/{chat_id}")
async def get_messages(chat_id: str, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    chat_messages = []
    for msg in messages_db:
        if msg["chatId"] == chat_id:
            sender = users_db.get(msg["senderId"])
            msg_with_sender = msg.copy()
            if sender:
                msg_with_sender["sender"] = {
                    "id": sender["id"],
                    "name": sender["name"],
                    "avatar": sender["avatar"]
                }
            chat_messages.append(msg_with_sender)
    
    chat_messages.sort(key=lambda x: x.get("timestamp", ""))
    return chat_messages

@app.put("/api/users/profile")
async def update_profile(user_data: UserUpdate, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload["id"]
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_data.name:
        users_db[user_id]["name"] = user_data.name
    if user_data.email:
        users_db[user_id]["email"] = user_data.email
    if user_data.bio:
        users_db[user_id]["bio"] = user_data.bio
    if user_data.phone:
        users_db[user_id]["phone"] = user_data.phone
    if user_data.avatar:
        users_db[user_id]["avatar"] = user_data.avatar
    
    user_response = users_db[user_id].copy()
    del user_response["password"]
    return user_response

@app.post("/api/users/avatar")
async def upload_avatar(avatar: UploadFile = File(...), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload["id"]
    
    print(f"📸 Avatar upload attempt for user: {user_id}")
    
    if not avatar:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    file_extension = os.path.splitext(avatar.filename)[1] if avatar.filename else ".jpg"
    unique_filename = f"{user_id}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = f"uploads/avatars/{unique_filename}"
    
    content = await avatar.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    avatar_url = f"/uploads/avatars/{unique_filename}"
    
    if user_id in users_db:
        users_db[user_id]["avatar"] = avatar_url
        print(f"✅ Avatar updated for user: {users_db[user_id]['name']}")
    
    return {"url": avatar_url}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    current_user_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "login":
                current_user_id = message["userId"]
                online_users[current_user_id] = websocket
                websocket_connections[current_user_id] = connection_id
                
                if current_user_id in users_db:
                    users_db[current_user_id]["online"] = True
                    users_db[current_user_id]["lastSeen"] = datetime.utcnow().isoformat()
                
                for uid, ws in online_users.items():
                    if uid != current_user_id:
                        try:
                            await ws.send_text(json.dumps({
                                "type": "user-status",
                                "userId": current_user_id,
                                "online": True
                            }))
                        except:
                            pass
            
            elif message.get("type") == "private-message":
                chat_id = message["chatId"]
                sender_id = message["senderId"]
                content = message["content"]
                
                new_message = {
                    "id": str(uuid.uuid4()),
                    "chatId": chat_id,
                    "senderId": sender_id,
                    "content": content,
                    "type": message.get("messageType", "text"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "read": False
                }
                
                messages_db.append(new_message)
                
                if chat_id in chats_db:
                    chats_db[chat_id]["lastMessage"] = new_message
                    chats_db[chat_id]["updatedAt"] = datetime.utcnow().isoformat()
                
                sender = users_db.get(sender_id)
                message_with_sender = {
                    **new_message,
                    "sender": {
                        "id": sender["id"],
                        "name": sender["name"],
                        "avatar": sender["avatar"]
                    } if sender else None
                }
                
                if chat_id in chats_db:
                    for pid in chats_db[chat_id]["participants"]:
                        if pid != sender_id and pid in online_users:
                            try:
                                await online_users[pid].send_text(json.dumps({
                                    "type": "private-message",
                                    **message_with_sender
                                }))
                            except:
                                pass
                
                await websocket.send_text(json.dumps({
                    "type": "private-message",
                    **message_with_sender
                }))
    
    except WebSocketDisconnect:
        if current_user_id:
            if current_user_id in online_users:
                del online_users[current_user_id]
            if current_user_id in users_db:
                users_db[current_user_id]["online"] = False
                users_db[current_user_id]["lastSeen"] = datetime.utcnow().isoformat()
            
            for uid, ws in online_users.items():
                try:
                    await ws.send_text(json.dumps({
                        "type": "user-status",
                        "userId": current_user_id,
                        "online": False
                    }))
                except:
                    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    print(f"\n🚀 Starting Millow server on port {port}")
    print(f"📍 Open http://localhost:{port} in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=port)