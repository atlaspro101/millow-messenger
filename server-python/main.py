from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import json
import os
import uuid
import asyncio

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
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Health check
@app.get("/")
async def root():
    return {
        "message": "Millow Server is running! 🚀",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "users": len(users_db),
        "chats": len(chats_db)
    }

@app.get("/api/test")
async def test():
    return {
        "message": "API is working!",
        "usersCount": len(users_db),
        "onlineUsers": len(online_users)
    }

# Регистрация
@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    print(f"📝 Register attempt: {user_data.email}")
    
    # Проверка существующего пользователя
    for user in users_db.values():
        if user["email"] == user_data.email:
            raise HTTPException(status_code=400, detail="User already exists")
    
    # Хеширование пароля
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

# Вход
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

# Получить всех пользователей
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

# Получить чаты пользователя
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
            
            user_chats.append({
                **chat,
                "otherUser": other_user
            })
    
    # Сортировка по времени обновления
    user_chats.sort(key=lambda x: x.get("updatedAt", x.get("createdAt", "")), reverse=True)
    
    return user_chats

# Создать или получить чат
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
    
    # Проверка существующего чата
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
    
    # Создание нового чата
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

# Получить сообщения чата
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
    
    # Сортировка по времени
    chat_messages.sort(key=lambda x: x.get("timestamp", ""))
    
    return chat_messages

# Обновить профиль
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

# Загрузка аватарки
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
    
    # Сохранение файла
    file_extension = os.path.splitext(avatar.filename)[1]
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

# WebSocket
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
                
                # Оповестить всех о статусе
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
                
                # Обновить чат
                if chat_id in chats_db:
                    chats_db[chat_id]["lastMessage"] = new_message
                    chats_db[chat_id]["updatedAt"] = datetime.utcnow().isoformat()
                
                # Отправить получателю
                sender = users_db.get(sender_id)
                message_with_sender = {
                    **new_message,
                    "sender": {
                        "id": sender["id"],
                        "name": sender["name"],
                        "avatar": sender["avatar"]
                    } if sender else None
                }
                
                # Найти получателя
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
                
                # Отправить отправителю подтверждение
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
            
            # Оповестить всех об оффлайне
            for uid, ws in online_users.items():
                try:
                    await ws.send_text(json.dumps({
                        "type": "user-status",
                        "userId": current_user_id,
                        "online": False
                    }))
                except:
                    pass

# Запуск
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)