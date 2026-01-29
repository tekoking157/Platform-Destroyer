import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv 
from keep_alive import keep_alive

# 1. CARREGAMENTO DE CONFIGURAÇÕES
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") 
PREFIXO = "?" 
MEU_ID = 1304003843172077659 

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

class PlatformDestroyer(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIXO,
            intents=intents,
            help_command=None 
        )
        self.manutencao = False 
        self.quantidade_slash = 0 

    async def setup_hook(self):
        print("\n--- 📦 Carregando Módulos ---")
        if not os.path.exists('./cogs'):
            os.makedirs('./cogs')
            print("⚠️ Pasta './cogs' não encontrada. Criada agora.")

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Módulo: {filename}')
                except Exception as e:
                    print(f'❌ Erro ao carregar {filename}: {e}')
        
        print("\n--- 🔄 Sincronizando Sistema ---")
        synced = await self.tree.sync()
        self.quantidade_slash = len(synced)
        print(f"✅ {self.quantidade_slash} comandos slash sincronizados!")

    async def on_ready(self):
        print("\n" + "="*40)
        print(f"✅ O bot {self.user.name} está online!")
        print(f"📡 {self.quantidade_slash} comandos slash prontos para uso.")
        print(f"🌍 Atuando em {len(self.guilds)} servidor(es).")
        print("="*40 + "\n")
        await self.change_presence(activity=discord.Game(name="Platform Destroyer 2026"))

    async def on_message(self, message):
        if message.author.bot:
            return

        if self.manutencao and message.author.id != MEU_ID:
            if message.content.startswith(self.command_prefix):
                return await message.channel.send("🚧 **Modo Manutenção:** O bot está sendo atualizado e voltará em breve!", delete_after=5)
        
        await self.process_commands(message)

bot = PlatformDestroyer()

# --- 🔄 COMANDO DE RELOAD ---
@bot.command(name="reload")
async def reload(ctx, extension: str):
    """Reinicia um módulo específico (Ex: ?reload punicoes)"""
    if ctx.author.id != MEU_ID:
        return await ctx.send("❌ Apenas o meu desenvolvedor pode usar este comando.")

    try:
        await bot.reload_extension(f"cogs.{extension}")
        await ctx.send(f"✅ O módulo `{extension}` foi reiniciado com sucesso!")
        print(f"🔄 Módulo {extension} reiniciado via comando por {ctx.author}")
    except Exception as e:
        await ctx.send(f"❌ Erro ao reiniciar o módulo `{extension}`: {e}")

# 4. TRATAMENTO DE ERROS GLOBAL
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        perms = ", ".join(error.missing_permissions).replace("_", " ").title()
        await ctx.send(f"❌ Você não tem permissão para usar este comando.\nRequer: `{perms}`", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membro não encontrado. Use a menção ou o ID.", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass 
    else:
        print(f"Erro no comando {ctx.command}: {error}")

# 5. EXECUÇÃO
if TOKEN:
    keep_alive()
    bot.run(TOKEN)
else:
    print("❌ ERRO: DISCORD_TOKEN não encontrado no arquivo .env!")
