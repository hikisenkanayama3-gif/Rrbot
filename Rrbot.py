import discord
from discord.ext import commands
from quart import Quart, render_template_string, request
import asyncio
import json
import os

# --- 設定エリア ---
# 24時間稼働させる場合は、TOKENを直接書かずにサーバーの設定（環境変数）に入れるのが安全です
TOKEN = os.environ.get('DISCORD_TOKEN', 'あなたのトークンをここに貼り付け')
CONFIG_FILE = 'config.json'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
app = Quart(__name__)

# --- 設定の読み込みと保存 ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                pass
    return {"message_id": 0, "role_id": 0, "emoji": "✅"}

def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

config = load_config()

# --- Webダッシュボード ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Bot Dashboard</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background-color: #f4f4f9; color: #333; }
        .container { max-width: 500px; margin: auto; padding: 30px; background: white; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 16px; }
        button { background: #5865F2; color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; }
        button:hover { background: #4752c4; }
        label { font-weight: bold; font-size: 14px; }
        .hint { font-size: 12px; color: #666; margin-top: 15px; background: #eee; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>リアクションロール設定</h2>
        <form method="POST" action="/update">
            <label>監視メッセージID:</label>
            <input type="number" name="msg_id" value="{{ message_id }}" required>
            <label>付与/削除するロールID:</label>
            <input type="number" name="role_id" value="{{ role_id }}" required>
            <label>反応する絵文字:</label>
            <input type="text" name="emoji" value="{{ emoji }}" required>
            <button type="submit">設定を保存して反映</button>
        </form>
        <div class="hint">
            <strong>使い方:</strong><br>
            1. IDを保存する<br>
            2. 対象のメッセージに自分で1回リアクションを付ける<br>
            3. これで付け外しが可能になります！
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
async def index():
    return await render_template_string(HTML_TEMPLATE, **config)

@app.route('/update', methods=['POST'])
async def update():
    form = await request.form
    config["message_id"] = int(form.get("msg_id", 0))
    config["role_id"] = int(form.get("role_id", 0))
    config["emoji"] = form.get("emoji", "✅")
    save_config(config)
    return "<h2>設定を更新しました！</h2><p>Botが動作を開始します。</p><a href='/'>戻る</a>"

@bot.event
async def on_ready():
    print(f'✅ Bot起動成功: {bot.user.name}')
    print(f'--- 稼働中 ---')

# --- ロール付与 (リアクション追加) ---
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
    if payload.message_id == config["message_id"] and str(payload.emoji) == config["emoji"]:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(config["role_id"])
        member = payload.member or await guild.fetch_member(payload.user_id)
        if role and member:
            try:
                await member.add_roles(role)
                print(f"✨ {member.display_name} にロールを付与しました")
            except Exception as e:
                print(f"❌ 付与失敗: {e}")

# --- ロール削除 (リアクション除去) ---
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id: return
    if payload.message_id == config["message_id"] and str(payload.emoji) == config["emoji"]:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(config["role_id"])
        try:
            member = await guild.fetch_member(payload.user_id)
            if role and member:
                await member.remove_roles(role)
                print(f"🗑️ {member.display_name} からロールを削除しました")
        except Exception as e:
            print(f"❌ 削除失敗: {e}")

# --- 24時間稼働のための実行設定 ---
async def main():
    # サーバー側が指定するポート番号を取得（デフォルト5000）
    port = int(os.environ.get("PORT", 5000))
    
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host='0.0.0.0', port=port)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass