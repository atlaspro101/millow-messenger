const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const http = require('http');
const socketio = require('socket.io');
const fs = require('fs');
const path = require('path');
const multer = require('multer');

const app = express();
const server = http.createServer(app);

// Настройка CORS для продакшена
const allowedOrigins = [
  'http://localhost:5173',
  'http://localhost:5000',
  'https://atlaspro101.github.io',
  'https://millow-api.onrender.com',
  'https://millow-messenger.vercel.app',
  /\.railway\.app$/,
  /\.glitch\.me$/
];

app.use(cors({
  origin: function(origin, callback) {
    if (!origin || allowedOrigins.some(allowed => {
      if (allowed instanceof RegExp) {
        return allowed.test(origin);
      }
      return allowed === origin;
    })) {
      callback(null, true);
    } else {
      console.log('Blocked by CORS:', origin);
      callback(null, true); // Временно разрешаем все для отладки
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Socket.io с CORS
const io = socketio(server, {
  cors: {
    origin: true,
    credentials: true,
    methods: ["GET", "POST"]
  }
});

// Определяем пути для файлов
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const UPLOADS_DIR = process.env.UPLOADS_DIR || path.join(__dirname, 'uploads', 'avatars');

// Создаем директории если их нет
try {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
  if (!fs.existsSync(UPLOADS_DIR)) {
    fs.mkdirSync(UPLOADS_DIR, { recursive: true });
  }
} catch (err) {
  console.log('Using in-memory storage (no file system access)');
}

// Пути к файлам данных
const USERS_FILE = path.join(DATA_DIR, 'users.json');
const CHATS_FILE = path.join(DATA_DIR, 'chats.json');
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');

// In-memory storage (запасной вариант)
let memoryUsers = [];
let memoryChats = [];
let memoryMessages = [];

// Функции для работы с данными
const readJSON = (filePath, defaultValue = []) => {
  try {
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    }
    return defaultValue;
  } catch (error) {
    console.error(`Error reading ${filePath}, using memory storage`);
    if (filePath === USERS_FILE) return memoryUsers;
    if (filePath === CHATS_FILE) return memoryChats;
    if (filePath === MESSAGES_FILE) return memoryMessages;
    return defaultValue;
  }
};

const writeJSON = (filePath, data) => {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
    return true;
  } catch (error) {
    console.error(`Error writing ${filePath}, using memory storage`);
    if (filePath === USERS_FILE) memoryUsers = data;
    if (filePath === CHATS_FILE) memoryChats = data;
    if (filePath === MESSAGES_FILE) memoryMessages = data;
    return false;
  }
};

// Статические файлы
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Настройка multer для загрузки аватарок
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    try {
      if (!fs.existsSync(UPLOADS_DIR)) {
        fs.mkdirSync(UPLOADS_DIR, { recursive: true });
      }
      cb(null, UPLOADS_DIR);
    } catch (err) {
      cb(err, null);
    }
  },
  filename: (req, file, cb) => {
    const uniqueName = Date.now() + '-' + Math.round(Math.random() * 1E9) + path.extname(file.originalname);
    cb(null, uniqueName);
  }
});

const upload = multer({ 
  storage: storage,
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Only images are allowed'), false);
    }
  }
});

// Инициализация файлов
if (!fs.existsSync(USERS_FILE)) writeJSON(USERS_FILE, []);
if (!fs.existsSync(CHATS_FILE)) writeJSON(CHATS_FILE, []);
if (!fs.existsSync(MESSAGES_FILE)) writeJSON(MESSAGES_FILE, []);

console.log('📁 Server started');
console.log('📁 Data directory:', DATA_DIR);
console.log('📁 Uploads directory:', UPLOADS_DIR);

// Socket.io - онлайн пользователи
const onlineUsers = new Map();

io.on('connection', (socket) => {
  console.log('🔌 User connected:', socket.id);
  
  let currentUserId = null;
  
  socket.on('login', (userId) => {
    currentUserId = userId;
    onlineUsers.set(userId, socket.id);
    
    const users = readJSON(USERS_FILE);
    const userIndex = users.findIndex(u => u.id === userId);
    if (userIndex !== -1) {
      users[userIndex].online = true;
      users[userIndex].lastSeen = new Date().toISOString();
      writeJSON(USERS_FILE, users);
      console.log(`✅ User ${users[userIndex].name} is online`);
    }
    
    io.emit('user-status', { userId, online: true });
  });
  
  socket.on('private-message', (data) => {
    console.log('💬 New message from', data.senderId);
    
    const messages = readJSON(MESSAGES_FILE);
    const chats = readJSON(CHATS_FILE);
    const users = readJSON(USERS_FILE);
    
    const message = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      chatId: data.chatId,
      senderId: data.senderId,
      content: data.content,
      type: data.type || 'text',
      timestamp: new Date().toISOString(),
      read: false
    };
    
    messages.push(message);
    writeJSON(MESSAGES_FILE, messages);
    
    const chatIndex = chats.findIndex(c => c.id === data.chatId);
    if (chatIndex !== -1) {
      chats[chatIndex].lastMessage = message;
      chats[chatIndex].updatedAt = new Date().toISOString();
      writeJSON(CHATS_FILE, chats);
    }
    
    const chat = chats[chatIndex];
    if (chat) {
      const recipientId = chat.participants.find(p => p !== data.senderId);
      const recipientSocket = onlineUsers.get(recipientId);
      
      const sender = users.find(u => u.id === data.senderId);
      
      const messageWithSender = {
        ...message,
        sender: sender ? {
          id: sender.id,
          name: sender.name,
          avatar: sender.avatar
        } : null
      };
      
      if (recipientSocket) {
        io.to(recipientSocket).emit('private-message', messageWithSender);
      }
      
      socket.emit('private-message', messageWithSender);
    }
  });
  
  socket.on('typing', (data) => {
    const chats = readJSON(CHATS_FILE);
    const chat = chats.find(c => c.id === data.chatId);
    if (chat) {
      const recipientId = chat.participants.find(p => p !== data.userId);
      const recipientSocket = onlineUsers.get(recipientId);
      if (recipientSocket) {
        io.to(recipientSocket).emit('typing', data);
      }
    }
  });
  
  socket.on('disconnect', () => {
    console.log('🔌 User disconnected:', socket.id);
    if (currentUserId) {
      onlineUsers.delete(currentUserId);
      
      const users = readJSON(USERS_FILE);
      const userIndex = users.findIndex(u => u.id === currentUserId);
      if (userIndex !== -1) {
        users[userIndex].online = false;
        users[userIndex].lastSeen = new Date().toISOString();
        writeJSON(USERS_FILE, users);
      }
      
      io.emit('user-status', { userId: currentUserId, online: false });
    }
  });
});

// ============ API Routes ============

// Health check
app.get('/', (req, res) => {
  res.json({ 
    message: 'Millow Server is running! 🚀',
    timestamp: new Date().toISOString(),
    status: 'healthy'
  });
});

// Test route
app.get('/api/test', (req, res) => {
  const users = readJSON(USERS_FILE);
  res.json({ 
    message: 'API is working!', 
    usersCount: users.length,
    onlineUsers: onlineUsers.size
  });
});

// Register
app.post('/api/auth/register', async (req, res) => {
  console.log('📝 Register attempt:', req.body.email);
  
  try {
    const { name, email, password } = req.body;
    
    if (!name || !email || !password) {
      return res.status(400).json({ error: 'All fields are required' });
    }
    
    const users = readJSON(USERS_FILE);
    
    const existingUser = users.find(u => u.email === email);
    if (existingUser) {
      return res.status(400).json({ error: 'User already exists' });
    }
    
    const hashedPassword = await bcrypt.hash(password, 10);
    
    const user = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      name,
      email,
      password: hashedPassword,
      avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=8B5CF6&color=fff&size=200`,
      bio: 'Hey there! I am using Millow',
      phone: '',
      online: false,
      lastSeen: new Date().toISOString(),
      createdAt: new Date().toISOString()
    };
    
    users.push(user);
    writeJSON(USERS_FILE, users);
    
    console.log('✅ User registered:', email);
    
    const token = jwt.sign(
      { id: user.id, email: user.email },
      process.env.JWT_SECRET || 'millow_secret_key_2024',
      { expiresIn: '7d' }
    );
    
    const { password: _, ...userWithoutPassword } = user;
    
    res.json({
      token,
      user: userWithoutPassword
    });
  } catch (error) {
    console.error('❌ Register error:', error);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// Login
app.post('/api/auth/login', async (req, res) => {
  console.log('🔑 Login attempt:', req.body.email);
  
  try {
    const { email, password } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }
    
    const users = readJSON(USERS_FILE);
    const user = users.find(u => u.email === email);
    
    if (!user) {
      console.log('❌ User not found:', email);
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const validPassword = await bcrypt.compare(password, user.password);
    if (!validPassword) {
      console.log('❌ Invalid password for:', email);
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    console.log('✅ User logged in:', email);
    
    const token = jwt.sign(
      { id: user.id, email: user.email },
      process.env.JWT_SECRET || 'millow_secret_key_2024',
      { expiresIn: '7d' }
    );
    
    const { password: _, ...userWithoutPassword } = user;
    
    res.json({
      token,
      user: userWithoutPassword
    });
  } catch (error) {
    console.error('❌ Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// Get all users
app.get('/api/users', (req, res) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'millow_secret_key_2024');
    const currentUserId = decoded.id;
    
    const users = readJSON(USERS_FILE);
    const usersList = users
      .filter(u => u.id !== currentUserId)
      .map(u => {
        const { password, ...userWithoutPassword } = u;
        return userWithoutPassword;
      });
    
    res.json(usersList);
  } catch (error) {
    console.error('❌ Get users error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Get user chats
app.get('/api/chats', (req, res) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'millow_secret_key_2024');
    const currentUserId = decoded.id;
    
    const chats = readJSON(CHATS_FILE);
    const users = readJSON(USERS_FILE);
    
    const userChats = chats
      .filter(c => c.participants && c.participants.includes(currentUserId))
      .map(chat => {
        const otherUserId = chat.participants.find(p => p !== currentUserId);
        const otherUser = users.find(u => u.id === otherUserId);
        
        return {
          ...chat,
          otherUser: otherUser ? {
            id: otherUser.id,
            name: otherUser.name,
            avatar: otherUser.avatar,
            online: otherUser.online || false,
            lastSeen: otherUser.lastSeen
          } : null
        };
      })
      .sort((a, b) => new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt));
    
    res.json(userChats);
  } catch (error) {
    console.error('❌ Get chats error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Create or get chat
app.post('/api/chats', (req, res) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'millow_secret_key_2024');
    const currentUserId = decoded.id;
    const { participantId } = req.body;
    
    let chats = readJSON(CHATS_FILE);
    const users = readJSON(USERS_FILE);
    
    let chat = chats.find(c => 
      c.participants && 
      c.participants.includes(currentUserId) && 
      c.participants.includes(participantId) &&
      !c.isGroup
    );
    
    if (!chat) {
      chat = {
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        participants: [currentUserId, participantId],
        isGroup: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        lastMessage: null
      };
      chats.push(chat);
      writeJSON(CHATS_FILE, chats);
    }
    
    const otherUser = users.find(u => u.id === participantId);
    const { password, ...otherUserWithoutPassword } = otherUser || {};
    
    res.json({
      ...chat,
      otherUser: otherUserWithoutPassword || null
    });
  } catch (error) {
    console.error('❌ Create chat error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Get chat messages
app.get('/api/messages/:chatId', (req, res) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'millow_secret_key_2024');
    const { chatId } = req.params;
    
    const messages = readJSON(MESSAGES_FILE);
    const users = readJSON(USERS_FILE);
    
    const chatMessages = messages
      .filter(m => m.chatId === chatId)
      .map(m => {
        const sender = users.find(u => u.id === m.senderId);
        return {
          ...m,
          sender: sender ? {
            id: sender.id,
            name: sender.name,
            avatar: sender.avatar
          } : null
        };
      })
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    res.json(chatMessages);
  } catch (error) {
    console.error('❌ Get messages error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Update profile
app.put('/api/users/profile', async (req, res) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'millow_secret_key_2024');
    const userId = decoded.id;
    const { name, email, bio, phone, avatar } = req.body;
    
    const users = readJSON(USERS_FILE);
    const userIndex = users.findIndex(u => u.id === userId);
    
    if (userIndex === -1) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    if (name) users[userIndex].name = name;
    if (email) users[userIndex].email = email;
    if (bio) users[userIndex].bio = bio;
    if (phone) users[userIndex].phone = phone;
    if (avatar) users[userIndex].avatar = avatar;
    
    writeJSON(USERS_FILE, users);
    
    const { password, ...userWithoutPassword } = users[userIndex];
    
    res.json(userWithoutPassword);
  } catch (error) {
    console.error('❌ Update profile error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Upload avatar
app.post('/api/users/avatar', upload.single('avatar'), (req, res) => {
  console.log('📸 Avatar upload attempt');
  
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'millow_secret_key_2024');
    const userId = decoded.id;
    
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }
    
    const protocol = req.headers['x-forwarded-proto'] || req.protocol;
    const host = req.get('host');
    const avatarUrl = `${protocol}://${host}/uploads/avatars/${req.file.filename}`;
    
    const users = readJSON(USERS_FILE);
    const userIndex = users.findIndex(u => u.id === userId);
    
    if (userIndex !== -1) {
      users[userIndex].avatar = avatarUrl;
      writeJSON(USERS_FILE, users);
      console.log('✅ Avatar updated for user:', users[userIndex].name);
    }
    
    res.json({ url: avatarUrl });
  } catch (error) {
    console.error('❌ Avatar upload error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Запуск сервера
const PORT = process.env.PORT || 5000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`\n✅ Server running on port ${PORT}`);
  console.log(`📁 Data directory: ${DATA_DIR}`);
  console.log(`📁 Uploads directory: ${UPLOADS_DIR}`);
  console.log(`\n📝 API endpoints:`);
  console.log(`   POST /api/auth/register - Register`);
  console.log(`   POST /api/auth/login - Login`);
  console.log(`   GET /api/users - Get all users`);
  console.log(`   GET /api/chats - Get user chats`);
  console.log(`   POST /api/chats - Create chat`);
  console.log(`   GET /api/messages/:chatId - Get messages`);
  console.log(`   PUT /api/users/profile - Update profile`);
  console.log(`   POST /api/users/avatar - Upload avatar\n`);
});