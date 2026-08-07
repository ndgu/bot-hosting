from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import json
import time
import signal

app = Flask(__name__)
CORS(app)

BOTS_DIR = "/app/bots"

# تأكد من وجود مجلد البوتات
os.makedirs(BOTS_DIR, exist_ok=True)

@app.route('/')
def home():
    return "🚀 خادم استضافة البوتات يعمل!"

@app.route('/api/start_bot', methods=['POST'])
def start_bot():
    try:
        data = request.json
        bot_id = data.get('bot_id', str(int(time.time())))
        token = data.get('bot_token')
        code = data.get('code')
        
        if not token or not code:
            return jsonify({'error': 'التوكن والكود مطلوبان'}), 400
        
        # إنشاء مجلد للبوت
        bot_folder = os.path.join(BOTS_DIR, bot_id)
        os.makedirs(bot_folder, exist_ok=True)
        
        # حفظ كود البوت
        with open(os.path.join(bot_folder, 'bot.py'), 'w', encoding='utf-8') as f:
            f.write(code)
        
        # حفظ التوكن في ملف منفصل
        with open(os.path.join(bot_folder, 'token.txt'), 'w') as f:
            f.write(token)
        
        # تشغيل البوت
        cmd = ['python', os.path.join(bot_folder, 'bot.py')]
        env = os.environ.copy()
        env['BOT_TOKEN'] = token
        
        process = subprocess.Popen(
            cmd, 
            env=env,
            cwd=bot_folder,
            stdout=open(os.path.join(bot_folder, 'output.log'), 'w'),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        # حفظ PID
        with open(os.path.join(bot_folder, 'pid.txt'), 'w') as f:
            f.write(str(process.pid))
        
        return jsonify({
            'status': 'running',
            'bot_id': bot_id,
            'pid': process.pid
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_bot/<bot_id>', methods=['POST'])
def stop_bot(bot_id):
    try:
        bot_folder = os.path.join(BOTS_DIR, bot_id)
        pid_file = os.path.join(bot_folder, 'pid.txt')
        
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            # قتل العملية ومجموعتها
            if os.name != 'nt':
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            else:
                os.kill(pid, 9)
            os.remove(pid_file)
            return jsonify({'status': 'stopped'})
        else:
            return jsonify({'status': 'already_stopped'})
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/bot_status/<bot_id>')
def bot_status(bot_id):
    try:
        bot_folder = os.path.join(BOTS_DIR, bot_id)
        pid_file = os.path.join(bot_folder, 'pid.txt')
        
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            # تحقق من وجود العملية
            try:
                os.kill(pid, 0)
                return jsonify({'status': 'running'})
            except:
                return jsonify({'status': 'stopped'})
        else:
            return jsonify({'status': 'not_found'})
            
    except:
        return jsonify({'status': 'unknown'})

@app.route('/api/bot_logs/<bot_id>')
def bot_logs(bot_id):
    try:
        log_file = os.path.join(BOTS_DIR, bot_id, 'output.log')
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = f.read().split('\n')[-50:]
            return jsonify({'logs': '\n'.join(logs)})
        else:
            return jsonify({'logs': 'لا توجد سجلات'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/list_bots')
def list_bots():
    try:
        bots = []
        if os.path.exists(BOTS_DIR):
            for bot_id in os.listdir(BOTS_DIR):
                if os.path.isdir(os.path.join(BOTS_DIR, bot_id)):
                    status_response = bot_status(bot_id)
                    if status_response.status_code == 200:
                        status_data = status_response.json
                        bots.append({
                            'id': bot_id,
                            'status': status_data.get('status', 'unknown')
                        })
        return jsonify({'bots': bots})
    except Exception as e:
        return jsonify({'bots': [], 'error': str(e)}), 500

@app.route('/api/delete_bot/<bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    try:
        # إيقاف البوت أولاً
        stop_bot(bot_id)
        
        # حذف المجلد
        import shutil
        bot_folder = os.path.join(BOTS_DIR, bot_id)
        if os.path.exists(bot_folder):
            shutil.rmtree(bot_folder)
            return jsonify({'status': 'deleted'})
        else:
            return jsonify({'status': 'not_found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
