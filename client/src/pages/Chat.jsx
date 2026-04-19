import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import io from 'socket.io-client';

const Chat = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [chats, setChats] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('chats');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socket, setSocket] = useState(null);
  const [typingUsers, setTypingUsers] = useState({});
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // Автообновление каждую секунду
  useEffect(() => {
    const interval = setInterval(() => {
      if (user) {
        fetchChats();
        fetchUsers();
        if (selectedChat) {
          fetchMessages(selectedChat.id);
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [user, selectedChat]);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    
    if (!userData || !token) {
      navigate('/login');
      return;
    }
    
    const parsedUser = JSON.parse(userData);
    setUser(parsedUser);
    
    const newSocket = io(import.meta.env.VITE_API_URL);
    setSocket(newSocket);
    
    newSocket.emit('login', parsedUser.id);
    
    newSocket.on('private-message', (message) => {
      if (selectedChat && message.chatId === selectedChat.id) {
        setMessages(prev => [...prev, message]);
      }
      fetchChats();
    });
    
    newSocket.on('user-status', ({ userId, online }) => {
      setUsers(prev => prev.map(u => 
        u.id === userId ? { ...u, online } : u
      ));
      setChats(prev => prev.map(c => {
        if (c.otherUser?.id === userId) {
          return { ...c, otherUser: { ...c.otherUser, online } };
        }
        return c;
      }));
    });
    
    fetchChats();
    fetchUsers();
    
    return () => newSocket.close();
  }, [navigate]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchChats = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/chats`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      setChats(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Error fetching chats:', error);
      setChats([]);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/users`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      setUsers(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Error fetching users:', error);
      setUsers([]);
    }
  };

  const fetchMessages = async (chatId) => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/messages/${chatId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      setMessages(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Error fetching messages:', error);
      setMessages([]);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedChat || !socket) return;

    const messageData = {
      chatId: selectedChat.id,
      senderId: user.id,
      content: newMessage,
      type: 'text'
    };

    socket.emit('private-message', messageData);
    setNewMessage('');
  };

  const handleTyping = () => {
    if (!selectedChat || !socket) return;
    
    socket.emit('typing', {
      chatId: selectedChat.id,
      userId: user.id,
      isTyping: true
    });
    
    clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      socket.emit('typing', {
        chatId: selectedChat.id,
        userId: user.id,
        isTyping: false
      });
    }, 1000);
  };

  const startNewChat = async (otherUserId) => {
    try {
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/chats`,
        { participantId: otherUserId },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      
      setChats(prev => {
        const exists = prev.find(c => c.id === res.data.id);
        if (exists) return prev;
        return [res.data, ...prev];
      });
      
      setSelectedChat(res.data);
      setActiveTab('chats');
      setSidebarOpen(false);
    } catch (error) {
      console.error('Error creating chat:', error);
    }
  };

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  const filteredChats = Array.isArray(chats) ? chats.filter(chat => 
    chat.otherUser?.name.toLowerCase().includes(searchTerm.toLowerCase())
  ) : [];

  const filteredUsers = Array.isArray(users) ? users.filter(u =>
    u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email.toLowerCase().includes(searchTerm.toLowerCase())
  ) : [];

  if (!user) return null;

  return (
    <div className="chat-container">
      <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2 className="gradient-text">Millow</h2>
          <div className="search-container">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search"
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'chats' ? 'active' : ''}`}
            onClick={() => setActiveTab('chats')}
          >
            Chats
          </button>
          <button 
            className={`tab ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            Users
          </button>
        </div>

        <div className="chat-list">
          {activeTab === 'chats' ? (
            filteredChats.length > 0 ? (
              filteredChats.map(chat => (
                <div
                  key={chat.id}
                  className={`chat-item ${selectedChat?.id === chat.id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedChat(chat);
                    setSidebarOpen(false);
                  }}
                >
                  <div className="chat-avatar">
                    <img src={chat.otherUser?.avatar || 'https://ui-avatars.com/api/?name=User&background=8B5CF6&color=fff'} alt={chat.otherUser?.name} />
                    {chat.otherUser?.online && <span className="online-indicator"></span>}
                  </div>
                  <div className="chat-info">
                    <div className="chat-name">
                      <span>{chat.otherUser?.name}</span>
                      {chat.lastMessage && (
                        <span className="chat-time">
                          {new Date(chat.lastMessage.timestamp).toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                          })}
                        </span>
                      )}
                    </div>
                    <div className="chat-last-message">
                      {chat.lastMessage?.content || 'No messages yet'}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">💬</div>
                <p>No chats yet</p>
              </div>
            )
          ) : (
            filteredUsers.length > 0 ? (
              filteredUsers.map(u => (
                <div
                  key={u.id}
                  className="chat-item"
                  onClick={() => startNewChat(u.id)}
                >
                  <div className="chat-avatar">
                    <img src={u.avatar || 'https://ui-avatars.com/api/?name=User&background=8B5CF6&color=fff'} alt={u.name} />
                    {u.online && <span className="online-indicator"></span>}
                  </div>
                  <div className="chat-info">
                    <div className="chat-name">{u.name}</div>
                    <div className="chat-last-message">{u.bio || 'Hey there!'}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <p>No users found</p>
              </div>
            )
          )}
        </div>

        <div className="sidebar-footer">
          <div className="user-profile-mini" onClick={() => navigate('/profile')}>
            <div className="user-avatar-small">
              <img src={user.avatar || 'https://ui-avatars.com/api/?name=User&background=8B5CF6&color=fff'} alt={user.name} />
            </div>
            <div className="user-info-mini">
              <div className="user-name">{user.name}</div>
              <div className="user-status">Online</div>
            </div>
          </div>
          <button 
            onClick={() => {
              localStorage.removeItem('token');
              localStorage.removeItem('user');
              navigate('/login');
            }}
            className="logout-btn-mini"
            style={{
              padding: '12px 16px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '2px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '20px',
              color: '#ef4444',
              cursor: 'pointer'
            }}
          >
            🚪
          </button>
        </div>
      </div>

      <div className="chat-area">
        {selectedChat ? (
          <>
            <div className="chat-header">
              <div className="chat-header-left">
                <button 
                  className="menu-toggle"
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                >
                  ☰
                </button>
                <div className="chat-header-info">
                  <div className="header-avatar">
                    <img src={selectedChat.otherUser?.avatar || 'https://ui-avatars.com/api/?name=User&background=8B5CF6&color=fff'} alt={selectedChat.otherUser?.name} />
                  </div>
                  <div>
                    <h3>{selectedChat.otherUser?.name}</h3>
                    <div className={`status-text ${selectedChat.otherUser?.online ? 'online' : 'offline'}`}>
                      {selectedChat.otherUser?.online ? 'Online' : 'Offline'}
                    </div>
                  </div>
                </div>
              </div>
              <div className="chat-actions">
                <button className="theme-toggle" onClick={toggleTheme}>
                  {theme === 'dark' ? '☀️' : '🌙'}
                </button>
                <button onClick={() => navigate('/profile')}>👤</button>
              </div>
            </div>

            <div className="messages-container">
              {messages.map(message => {
                const isOwn = message.senderId === user.id;
                return (
                  <div key={message.id} className={`message ${isOwn ? 'own' : ''}`}>
                    {!isOwn && (
                      <div className="message-avatar">
                        <img src={selectedChat.otherUser?.avatar} alt="" />
                      </div>
                    )}
                    <div className="message-content">
                      <div className="message-bubble">
                        {message.content}
                      </div>
                      <div className="message-time">
                        {new Date(message.timestamp).toLocaleTimeString('en-US', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </div>
                    </div>
                    {isOwn && (
                      <div className="message-avatar">
                        <img src={user.avatar} alt="" />
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <div className="message-input-container">
              <form onSubmit={handleSendMessage} className="message-form">
                <input
                  type="text"
                  placeholder="Type a message..."
                  className="message-input"
                  value={newMessage}
                  onChange={(e) => {
                    setNewMessage(e.target.value);
                    handleTyping();
                  }}
                />
                <div className="input-actions">
                  <button type="button" className="input-action-btn">😊</button>
                  <button type="button" className="input-action-btn">📎</button>
                </div>
                <button type="submit" className="send-button" disabled={!newMessage.trim()}>
                  Send
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">💬</div>
            <h2>Welcome to Millow</h2>
            <p>Select a chat or find users to start messaging</p>
            <button 
              onClick={() => setSidebarOpen(true)}
              className="start-chatting-btn"
            >
              Start Chatting
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chat;