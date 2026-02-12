import discord
from discord.ext import commands
import os
from dotenv import load_dotenv 

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") 
PREFIXO = "?" 
MEU_ID = 1304003843172077659 

intents = discord.Intents.all()

class PlatformDestroyer(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIXO,
            intents=intents,
            help_command=None 
        )
        self.manutencao = False 

    async def setup_hook(self):
        if not os.path.exists('./cogs'):
            os.makedirs('./cogs')
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                except Exception as e:
                    print(f'Erro ao carregar {filename}: {e}')
        await self.tree.sync()

    async def on_ready(self):
        print(f"Bot {self.user.name} online")
        await self.change_presence(activity=discord.Game(name="Platform Destroyer"))

    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if self.manutencao and message.author.id != MEU_ID:
            if message.content.startswith(self.command_prefix):
                if not message.content.startswith(f"{self.command_prefix}manutencao"):
                    return await message.channel.send("🚧 **Modo Manutenção!**", delete_after=5)
        await self.process_commands(message)

    async def on_interaction(self, interaction: discord.Interaction):
        if self.manutencao and interaction.user.id != MEU_ID:
            if interaction.type == discord.InteractionType.application_command:
                if interaction.data.get('name') != "manutencao":
                    if not interaction.response.is_done():
                        return await interaction.response.send_message("🚧 **Modo Manutenção!**", ephemeral=True)

bot = PlatformDestroyer()

@bot.hybrid_command(name="manutencao", description="ativa/desativa o modo de manutenção")
async def manutencao(ctx, status: str):
    if ctx.author.id != MEU_ID: 
        return await ctx.send("❌ Negado.", ephemeral=True)
    
    if ctx.interaction:
        await ctx.interaction.response.defer()

    bot.manutencao = (status.lower() == "on")
    if bot.manutencao:
        await bot.change_presence(status=discord.Status.dnd, activity=discord.Game(name="⚠️ MANUTENÇÃO"))
        msg = "🚨 ATIVADO"
    else:
        await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Platform Destroyer"))
        msg = "✅ DESATIVADO"
        
    await ctx.send(f"Modo manutenção {msg}.")

@bot.command(name="sync")
async def sync(ctx):
    if ctx.author.id != MEU_ID: return
    fmt = await bot.tree.sync()
    await ctx.send(f"✅ Sincronizados {len(fmt)} comandos slash.")

if TOKEN:
    bot.run(TOKEN)
else:
    print("Erro Token")
