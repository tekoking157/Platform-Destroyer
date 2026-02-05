import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv 
from keep_alive import keep_alive

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
        self.quantidade_slash = 0 

    async def setup_hook(self):
        if not os.path.exists('./cogs'):
            os.makedirs('./cogs')

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                except Exception as e:
                    print(f'Erro: {e}')
        
        try:
            synced = await self.tree.sync()
            self.quantidade_slash = len(synced)
        except Exception as e:
            print(f'Erro Sync: {e}')

    async def on_ready(self):
        print(f"Bot {self.user.name} online")
        await self.change_presence(activity=discord.Game(name="Platform Destroyer 2026"))

    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if self.manutencao and message.author.id != MEU_ID:
            if message.content.startswith(self.command_prefix):
                if not message.content.startswith(f"{self.command_prefix}manutencao"):
                    return await message.channel.send("🚧 **Modo Manutenção:** O bot está sendo atualizado e voltará em breve!", delete_after=5)
        
        await self.process_commands(message)

    async def on_interaction(self, interaction: discord.Interaction):
        if self.manutencao and interaction.user.id != MEU_ID:
            if interaction.type == discord.InteractionType.application_command:
                if interaction.data.get('name') != "manutencao":
                    return await interaction.response.send_message("🚧 **Modo Manutenção:** O bot está sendo atualizado e voltará em breve!", ephemeral=True)
        
        await self.tree.process_interactions(interaction)

bot = PlatformDestroyer()

@bot.hybrid_command(name="manutencao", description="ativa/desativa o modo de manutenção")
async def manutencao(ctx, status: str):
    if ctx.author.id != MEU_ID: 
        return await ctx.send("❌ Apenas o desenvolvedor supremo pode usar isso.", ephemeral=True)
    
    status_lower = status.lower()
    bot.manutencao = (status_lower == "on")
    
    if bot.manutencao:
        msg = "🚨 ATIVADO"
        await bot.change_presence(status=discord.Status.dnd, activity=discord.Game(name="⚠️ MANUTENÇÃO"))
    else:
        msg = "✅ DESATIVADO"
        await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Platform Destroyer"))
        
    await ctx.send(f"Modo manutenção {msg}.")

@bot.command(name="reload")
async def reload(ctx, extension: str):
    if ctx.author.id != MEU_ID:
        return await ctx.send("❌ Apenas o meu desenvolvedor pode usar este comando.")

    try:
        await bot.reload_extension(f"cogs.{extension}")
        await ctx.send(f"✅ O módulo `{extension}` foi reiniciado com sucesso!")
    except Exception as e:
        await ctx.send(f"❌ Erro ao reiniciar o módulo `{extension}`: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        perms = ", ".join(error.missing_permissions).replace("_", " ").title()
        await ctx.send(f"❌ Você não tem permissão para usar este comando.\nRequer: `{perms}`", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membro não encontrado. Use a menção ou o ID.", delete_after=5)
    elif isinstance(error, commands.NotOwner):
        await ctx.send("❌ Este comando é restrito ao dono do bot.", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass 
    else:
        print(f"Erro: {error}")

if TOKEN:
    keep_alive()
    bot.run(TOKEN)
else:
    print("Erro Token")

