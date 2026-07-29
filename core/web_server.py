import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from PyQt5.QtCore import QThread
from .config import APP_CONFIG, save_config, set_autostart

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>李彤彤 - 控制中心</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #ff6b81;
            --secondary: #ff9fb3;
            --bg-color: #fdf2f4;
            --glass-bg: rgba(255, 255, 255, 0.7);
            --glass-border: rgba(255, 255, 255, 0.5);
            --text-main: #2d3436;
            --text-muted: #636e72;
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #fdf2f4 0%, #ffeaa7 100%);
            color: var(--text-main);
            margin: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem;
        }

        .container {
            width: 100%;
            max-width: 900px;
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            box-shadow: 0 8px 32px 0 rgba(255, 107, 129, 0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            min-height: 600px;
        }

        .header {
            padding: 2rem 3rem;
            background: rgba(255, 255, 255, 0.4);
            border-bottom: 1px solid var(--glass-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            margin: 0;
            font-size: 1.8rem;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .tabs {
            display: flex;
            gap: 1rem;
        }

        .tab-btn {
            background: transparent;
            border: none;
            padding: 0.5rem 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            border-radius: 12px;
            transition: all 0.3s ease;
        }

        .tab-btn:hover {
            background: rgba(255, 107, 129, 0.1);
            color: var(--primary);
        }

        .tab-btn.active {
            background: var(--primary);
            color: white;
            box-shadow: 0 4px 12px rgba(255, 107, 129, 0.3);
        }

        .content {
            padding: 3rem;
            flex-grow: 1;
            position: relative;
        }

        .panel {
            display: none;
            animation: fadeIn 0.4s ease forwards;
        }

        .panel.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-main);
        }

        input[type="text"], input[type="password"], select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid rgba(255, 107, 129, 0.2);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.9);
            font-size: 1rem;
            transition: all 0.3s ease;
            box-sizing: border-box;
            outline: none;
        }

        input[type="text"]:focus, input[type="password"]:focus, select:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(255, 107, 129, 0.1);
        }

        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 1rem;
        }

        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: var(--primary);
            cursor: pointer;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(255, 107, 129, 0.3);
            margin-top: 1rem;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(255, 107, 129, 0.4);
            background: #ff526a;
        }

        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: #2ed573;
            color: white;
            padding: 12px 24px;
            border-radius: 12px;
            font-weight: 500;
            box-shadow: 0 8px 24px rgba(46, 213, 115, 0.3);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }

        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.6);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid var(--glass-border);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.5rem;
        }

        .stat-label {
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--text-muted);
        }

        .chart-container {
            background: rgba(255, 255, 255, 0.6);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--glass-border);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
            margin-bottom: 2rem;
        }

        .details-container {
            background: rgba(255, 255, 255, 0.6);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--glass-border);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
        }

        .details-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 1rem;
        }

        .category-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.8rem 1rem;
            border-bottom: 1px solid var(--glass-border);
        }

        .category-item:last-child {
            border-bottom: none;
        }

        .category-name {
            font-weight: 600;
            color: #555;
        }

        .category-value {
            font-weight: 700;
            color: var(--primary);
        }

        /* History Panel */
        .history-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            max-height: 400px;
            overflow-y: auto;
            padding-right: 10px;
        }

        .history-item {
            background: rgba(255, 255, 255, 0.6);
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid var(--glass-border);
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .history-item.user {
            border-left: 4px solid #3498db;
        }

        .history-item.assistant {
            border-left: 4px solid var(--primary);
        }

        .history-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        
        .history-role {
            font-weight: 600;
        }

        .history-content {
            font-size: 1rem;
            color: var(--text-main);
            white-space: pre-wrap;
        }

        .history-tokens {
            font-size: 0.8rem;
            color: #e17055;
            text-align: right;
            font-weight: 500;
        }
    </style>
</head>
<body>

    <div class="container">
        <div class="header">
            <h1>🌸 李彤彤控制中心</h1>
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('settings')">⚙️ 核心设置</button>
                <button class="tab-btn" onclick="switchTab('stats')">📊 Token统计</button>
                <button class="tab-btn" onclick="switchTab('history')">💬 历史对话</button>
            </div>
        </div>

        <div class="content">
            <!-- Settings Panel -->
            <div id="settings-panel" class="panel active">
                <div class="form-group">
                    <label>DeepSeek API Key (核心大脑)</label>
                    <input type="password" id="api_key" placeholder="sk-...">
                </div>
                
                <div class="form-group">
                    <label>千帆智能搜索 API Key (可选，用于联网)</label>
                    <input type="password" id="qianfan_api_key" placeholder="如果不需要联网搜索可留空">
                </div>

                <div class="form-group">
                    <label>TTS 语音声线</label>
                    <select id="tts_voice">
                        <option value="zh-CN-XiaoxiaoNeural">晓晓 (温暖亲切)</option>
                        <option value="zh-CN-XiaoyiNeural">晓伊 (活泼可爱)</option>
                        <option value="zh-CN-liaoning-XiaobeiNeural">晓北 (东北幽默)</option>
                        <option value="zh-CN-shaanxi-XiaoniNeural">晓妮 (陕西明快)</option>
                        <option value="zh-TW-HsiaoChenNeural">晓臻 (台湾轻柔)</option>
                    </select>
                </div>

                <div class="checkbox-wrapper">
                    <input type="checkbox" id="autostart">
                    <label for="autostart" style="margin:0;">开机自启动</label>
                </div>
                
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="enable_voice">
                    <label for="enable_voice" style="margin:0;">允许彤彤说话</label>
                </div>

                <button class="btn-primary" onclick="saveSettings()">保存配置 💖</button>
            </div>

            <!-- Stats Panel -->
            <div id="stats-panel" class="panel">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" id="total-tokens">0</div>
                        <div class="stat-label">总消耗 Tokens</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="chat-tokens">0</div>
                        <div class="stat-label">聊天消耗</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="skill-tokens">0</div>
                        <div class="stat-label">技能/工具消耗</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="tokenChart" height="100"></canvas>
                </div>

                <div class="details-container">
                    <div class="details-title">详细消耗明细 (分类统计)</div>
                    <div id="category-list"></div>
                </div>
            </div>

            <!-- History Panel -->
            <div id="history-panel" class="panel">
                <div class="history-list" id="history-list">
                    <div style="text-align: center; color: var(--text-muted); margin-top: 2rem;">加载中...</div>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">✅ 保存成功！彤彤记住了哦~</div>

    <script>
        let myChart = null;
        const categoryMap = {
            'user_chat': '主被动聊天',
            'idle_chat': '挂机闲聊',
            'companion_chat': '主动情绪陪伴 (新)',
            'system_chat_music': '切歌识别 (旧版)',
            'system_chat_window': '窗口识别 (旧版)',
            'system_chat_unknown': '其他系统提醒',
            'system_chat': '切歌等特殊提醒 (旧版)',
            'tool_chat': '执行技能工具',
            'memory_extractor': '长期记忆提取',
            'quote_gen': '闲聊语录生成'
        };

        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(`${tabId}-panel`).classList.add('active');

            if (tabId === 'stats') {
                loadStats();
            } else if (tabId === 'history') {
                loadHistory();
            }
        }

        function showToast() {
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        async function loadSettings() {
            const res = await fetch('/api/settings');
            const data = await res.json();
            document.getElementById('api_key').value = data.api_key || '';
            document.getElementById('qianfan_api_key').value = data.qianfan_api_key || '';
            document.getElementById('tts_voice').value = data.tts_voice || 'zh-CN-XiaoxiaoNeural';
            document.getElementById('autostart').checked = !!data.autostart;
            document.getElementById('enable_voice').checked = data.enable_voice !== false;
        }

        async function saveSettings() {
            const data = {
                api_key: document.getElementById('api_key').value.trim(),
                qianfan_api_key: document.getElementById('qianfan_api_key').value.trim(),
                tts_voice: document.getElementById('tts_voice').value,
                autostart: document.getElementById('autostart').checked,
                enable_voice: document.getElementById('enable_voice').checked
            };

            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            showToast();
        }

        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            
            let total = 0, chatTotal = 0, skillTotal = 0;
            const catData = data.categories || {};
            
            for (const [k, v] of Object.entries(catData)) {
                total += v;
                if (k.includes('chat') && k !== 'tool_chat') chatTotal += v;
                if (k === 'tool_chat' || k === 'memory_extractor') skillTotal += v;
            }
            
            document.getElementById('total-tokens').innerText = total.toLocaleString();
            document.getElementById('chat-tokens').innerText = chatTotal.toLocaleString();
            document.getElementById('skill-tokens').innerText = skillTotal.toLocaleString();

            const categoryList = document.getElementById('category-list');
            categoryList.innerHTML = '';
            for (const [k, v] of Object.entries(catData)) {
                if (v > 0) {
                    const name = categoryMap[k] || k;
                    categoryList.innerHTML += `
                        <div class="category-item">
                            <span class="category-name">${name}</span>
                            <span class="category-value">${v.toLocaleString()}</span>
                        </div>
                    `;
                }
            }

            const daily = data.daily || [];
            const labels = daily.map(d => d.date);
            const values = daily.map(d => d.tokens);

            if (myChart) myChart.destroy();
            const ctx = document.getElementById('tokenChart').getContext('2d');
            myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '每日 Token 消耗',
                        data: values,
                        borderColor: '#ff6b81',
                        backgroundColor: 'rgba(255, 107, 129, 0.2)',
                        borderWidth: 3,
                        pointBackgroundColor: '#ff6b81',
                        pointRadius: 4,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { borderDash: [5, 5] } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        async function loadHistory() {
            const res = await fetch('/api/history');
            const data = await res.json();
            
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = '';
            
            if (!data || data.length === 0) {
                historyList.innerHTML = '<div style="text-align: center; color: var(--text-muted); margin-top: 2rem;">暂无对话记录哦~</div>';
                return;
            }

            data.forEach(item => {
                const isUser = item.role === 'user';
                const roleName = isUser ? '累累' : '彤彤';
                const dateStr = new Date(item.timestamp).toLocaleString();
                
                let tokenHtml = '';
                if (!isUser && item.total_tokens > 0) {
                    tokenHtml = `<div class="history-tokens">消耗: ${item.total_tokens} Tokens (提示:${item.prompt_tokens} 返回:${item.completion_tokens})</div>`;
                }

                historyList.innerHTML += `
                    <div class="history-item ${item.role}">
                        <div class="history-meta">
                            <span class="history-role">${roleName}</span>
                            <span>${dateStr}</span>
                        </div>
                        <div class="history-content">${item.content}</div>
                        ${tokenHtml}
                    </div>
                `;
            });
        }

        loadSettings();
    </script>
</body>
</html>
"""

class SettingsRequestHandler(BaseHTTPRequestHandler):
    memory_manager = None
    
    def log_message(self, format, *args):
        pass # 禁用默认日志
        
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif self.path == '/api/settings':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(APP_CONFIG).encode('utf-8'))
        elif self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            stats = self.memory_manager.get_token_stats() if self.memory_manager else {}
            self.wfile.write(json.dumps(stats).encode('utf-8'))
        elif self.path == '/api/history':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            history = self.memory_manager.get_chat_history(50) if self.memory_manager else []
            self.wfile.write(json.dumps(history).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_POST(self):
        if self.path == '/api/settings':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                new_config = json.loads(post_data.decode('utf-8'))
                for k, v in new_config.items():
                    APP_CONFIG[k] = v
                save_config(APP_CONFIG)
                set_autostart(APP_CONFIG.get("autostart", False))
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

class WebServerThread(QThread):
    def __init__(self, memory_manager, port=5050, parent=None):
        super().__init__(parent)
        self.port = port
        self.memory_manager = memory_manager
        self.server = None
        
    def run(self):
        SettingsRequestHandler.memory_manager = self.memory_manager
        self.server = HTTPServer(('127.0.0.1', self.port), SettingsRequestHandler)
        print(f"[DEBUG] Web server started at http://127.0.0.1:{self.port}")
        self.server.serve_forever()
        
    def stop(self):
        if self.server:
            import threading
            # shutdown() can deadlock if called from the main thread in some environments,
            # so we run it in a daemon thread.
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            # server_close() should ideally be called after shutdown, but closing it here
            # can sometimes also help unblock serve_forever immediately.
            try:
                self.server.server_close()
            except:
                pass
