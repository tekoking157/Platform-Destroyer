import discord
from discord.ext import commands
import datetime
import asyncio

ID_CANAL_LOGS = 1465185281484525825 
WHITELIST = [1304003843172077659] 
COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)

class seguranca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitor_ban = {}
        self.monitor_kick = {}
        self.monitor_cargos = {}
        self.spam_control = {}
        self.spam_warned = set() # Novo: Armazena quem já foi avisado para não repetir
        self.anti_invite_ativo = {}
        self.anti_raid_ativo = {}

    def verificar_limite(self, user_id, dicionario, limite=10, tempo=60):
        if user_id in WHITELIST: return False
        agora = datetime.datetime.now()
        
        if user_id not in dicionario: 
            dicionario[user_id] = []
            
        dicionario[user_id] = [ts for ts in dicionario[user_id] if (agora - ts).total_seconds() < tempo]
        dicionario[user_id].append(agora)
        
        return len(dicionario[user_id]) > limite

    async def enviar_log(self, guild, usuario, acao, cor=discord.Color.orange()):
        canal = guild.get_channel(ID_CANAL_LOGS)
        if canal:
            embed = discord.Embed(title="🛡️ SEGURANÇA PLATFORM", color=cor, timestamp=datetime.datetime.now())
            embed.add_field(name="👤 Usuário", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
            embed.add_field(name="📝 Ação", value=acao, inline=True)
            try: await canal.send(embed=embed)
            except: pass

    @commands.hybrid_command(name="antiinvite", description="Liga/Desliga bloqueio de convites")
    @commands.has_permissions(manage_guild=True)
    async def antiinvite(self, ctx, status: str):
        status = status.lower()
        self.anti_invite_ativo[ctx.guild.id] = (status == "on")
        emoji = "✅" if status == "on" else "❌"
        await ctx.send(f"{emoji} | Anti-Invite: **{status.upper()}**")

    @commands.hybrid_command(name="antiraid", description="Liga/Desliga anti-flood de mensagens")
    @commands.has_permissions(manage_guild=True)
    async def antiraid(self, ctx, status: str):
        status = status.lower()
        self.anti_raid_ativo[ctx.guild.id] = (status == "on")
        emoji = "✅" if status == "on" else "❌"
        await ctx.send(f"{emoji} | Anti-Raid (Flood): **{status.upper()}**")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or message.author.id in WHITELIST:
            return

        gid = message.guild.id
        
        # --- ANTI INVITE ---
        if self.anti_invite_ativo.get(gid, False):
            invites = ["discord.gg/", "discord.com/invite/", "discord.me/", "discord.io/"]
            if any(invite in message.content.lower() for invite in invites):
                try:
                    await message.delete()
                    return await message.channel.send(f"⚠️ {message.author.mention}, proibido enviar convites.", delete_after=3)
                except: pass

        # --- ANTI RAID (FLOOD) ---
        status_raid = self.anti_raid_ativo.get(gid, False)
        if status_raid:
            if message.author.guild_permissions.manage_messages: 
                return
            
            agora = datetime.datetime.now()
            user_id = message.author.id
            
            if user_id not in self.spam_control:
                self.spam_control[user_id] = []
            
            # Mantém apenas mensagens dos últimos 5 segundos no histórico
            self.spam_control[user_id] = [t for t in self.spam_control[user_id] if (agora - t).total_seconds() < 5]
            self.spam_control[user_id].append(agora)

            # Se exceder 5 mensagens em 5 segundos
            if len(self.spam_control[user_id]) > 5:
                try:
                    await message.delete() # Deleta todas as excedentes
                    
                    # Se ele ainda não foi avisado NESTE flood, avisa agora
                    if user_id not in self.spam_warned:
                        self.spam_warned.add(user_id)
                        await message.channel.send(f"❌ {message.author.mention}, pare de floodar!", delete_after=3)
                        
                        # Espera 5 segundos e remove do cache de avisos para poder avisar de novo depois
                        await asyncio.sleep(5)
                        if user_id in self.spam_warned:
                            self.spam_warned.remove(user_id)
                except: pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            staff = entry.user
            if staff.bot or staff.id in WHITELIST: return
            
            if self.verificar_limite(staff.id, self.monitor_ban, limite=10, tempo=60):
                try:
                    await staff.edit(roles=[], reason="Anti-Raid: Spam de Banimentos")
                    await self.enviar_log(guild, staff, "Cargos removidos por Mass Ban.", discord.Color.red())
                except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        async for entry in guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
            if entry.target.id == member.id:
                staff = entry.user
                if staff.bot or staff.id in WHITELIST: return
                
                if self.verificar_limite(staff.id, self.monitor_kick, limite=10, tempo=60):
                    try:
                        await staff.edit(roles=[], reason="Anti-Raid: Spam de Expulsões (Mass Kick)")
                        await self.enviar_log(guild, staff, "Cargos removidos por Mass Kick.", discord.Color.red())
                    except: pass
                break

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if len(before.roles) < len(after.roles):
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                staff = entry.user
                if staff.bot or staff.id in WHITELIST: return
                
                if self.verificar_limite(staff.id, self.monitor_cargos, limite=3, tempo=60):
                    try:
                        await staff.edit(roles=[], reason="Anti-Raid: Spam de Cargos")
                        await self.enviar_log(after.guild, staff, "Cargos removidos por Mass Role.", discord.Color.red())
                    except: pass

async def setup(bot):
    await bot.add_cog(seguranca(bot))

