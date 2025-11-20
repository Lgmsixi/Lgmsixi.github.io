import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# 存储在线用户
online_users = set()

# 初始化数据库
def init_db():
    conn = sqlite3.connect('chat.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         username TEXT NOT NULL,
         message TEXT NOT NULL,
         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)
    ''')
    conn.commit()
    conn.close()

# 保存消息到数据库
def save_message(username, message):
    conn = sqlite3.connect('chat.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, message) VALUES (?, ?)", (username, message))
    conn.commit()
    conn.close()

# 获取聊天历史
def get_chat_history(limit=100):
    conn = sqlite3.connect('chat.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT username, message, timestamp FROM messages ORDER BY timestamp ASC LIMIT ?", (limit,))
    messages = c.fetchall()
    conn.close()
    
    # 转换为字典列表
    result = []
    for msg in messages:
        result.append({
            'username': msg[0],
            'message': msg[1],
            'timestamp': msg[2]
        })
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def get_history():
    try:
        messages = get_chat_history()
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    print(f'客户端已连接: {request.sid}')
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'客户端断开连接: {request.sid}')
    # 找到断开连接的用户并从在线用户中移除
    for user in list(online_users):
        online_users.discard(user)
        emit('user_list', {'users': list(online_users)}, broadcast=True)
        emit('system', {'message': f'{user} 离开了聊天室'}, broadcast=True)
        break

@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    if username and username not in online_users:
        online_users.add(username)
        print(f'用户 {username} 加入聊天室')
        emit('user_list', {'users': list(online_users)}, broadcast=True)
        emit('system', {'message': f'{username} 加入了聊天室'}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    username = data.get('username')
    message = data.get('message')
    
    if username and message:
        print(f'收到消息 from {username}: {message}')
        # 保存消息到数据库
        save_message(username, message)
        
        # 广播消息给所有客户端
        emit('message', {
            'username': username,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)

if __name__ == '__main__':
    print("初始化数据库...")
    init_db()
    print("启动服务器...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
