const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const http = require('http');
const socketio = require('socket.io');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = socketio(server, {
  cors: {
    origin: "http://localhost:5173",
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE"]
  }
});

const allowedOrigins = [
  'http://localhost:5173',
  'http://localhost:5000',
  'https://millow-client.onrender.com',
  'https://millow-server.onrender.com'
];

app.use(cors({
  origin: function(origin, callback) {
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true
}));

// Middleware
app.use(cors({
  origin: "http://localhost:5173",
  credentials: true
}));
app.use(express.json());
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Пути к файлам данных
const DATA_DIR = path.join(__dirname, 'data');
const USERS_FILE = path.join(DATA_DIR, 'users.json');
const CHATS_FILE = path.join(DATA_DIR, 'chats.json');
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');

// Создаем папки
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}
if (!fs.existsSync(path.join(__dirname, 'uploads', 'avatars'))) {
  fs.mkdirSync(path.join(__dirname, 'uploads', 'avatars'), { recursive: true });
}

// Функции для работы с файлами
const readJSON = (filePath) => {
  try {
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    }
    return [];
  } catch (error) {
    console.error(`Error reading ${filePath}:`, error);
    return [];
  }
};

const writeJSON = (filePath, data) => {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
    return true;
  } catch (error) {
    console.error(`Error writing ${filePath}:`, error);
    return false;
  }
};

// Инициализация файлов
if (!fs.existsSync(USERS_FILE)) writeJSON(USERS_FILE, []);
if (!fs.existsSync(CHATS_FILE)) writeJSON(CHATS_FILE, []);
if (!fs.existsSync(MESSAGES_FILE)) writeJSON(MESSAGES_FILE, []);

console.log('📁 Data directory:', DATA_DIR);
console.log('📁 Users file exists:', fs.existsSync(USERS_FILE));

// Socket.io
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
      writeJSON(USERS_FILE, users);
      console.log(`✅ User ${users[userIndex].name} is online`);
    }
    
    io.emit('user-status', { userId, online: true });
  });
  
  socket.on('private-message', (data) => {
    console.log('💬 New message:', data.content);
    
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

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'Millow Server is running! 🚀', timestamp: new Date().toISOString() });
});

// Test route
app.get('/api/test', (req, res) => {
  const users = readJSON(USERS_FILE);
  res.json({ 
    message: 'API is working!', 
    usersCount: users.length,
    dataDir: DATA_DIR 
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
    const saved = writeJSON(USERS_FILE, users);
    
    if (!saved) {
      return res.status(500).json({ error: 'Failed to save user' });
    }
    
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
    res.status(500).json({ error: 'Registration failed: ' + error.message });
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
    res.status(500).json({ error: 'Login failed: ' + error.message });
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
      .filter(c => c.participants.includes(currentUserId))
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
      .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
    
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
    const { password, ...otherUserWithoutPassword } = otherUser;
    
    res.json({
      ...chat,
      otherUser: otherUserWithoutPassword
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
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(__dirname, 'uploads', 'avatars');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueName = Date.now() + '-' + Math.round(Math.random() * 1E9) + path.extname(file.originalname);
    cb(null, uniqueName);
  }
});
const upload = multer({ 
  storage,
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Only images are allowed'));
    }
  }
});

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
    
    const avatarUrl = `http://localhost:5000/uploads/avatars/${req.file.filename}`;
    
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

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`\n✅ Server running on http://localhost:${PORT}`);
  console.log(`📁 Data directory: ${DATA_DIR}`);
  console.log(`📁 Users file: ${USERS_FILE}`);
  console.log(`\n📝 Test endpoints:`);
  console.log(`   GET  http://localhost:${PORT}/api/test`);
  console.log(`   POST http://localhost:${PORT}/api/auth/register`);
  console.log(`   POST http://localhost:${PORT}/api/auth/login\n`);
});