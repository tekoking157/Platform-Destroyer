import discord
from discord.ext import commands
import datetime
import asyncio

ID_CANAL_LOGS = 1357569804273324285 
WHITELIST_USERS = [1304003843172077659, 935566792384991303] 
IDS_CARGOS_PERMITIDOS = [1357569800947237000, 1414283694662750268, 1357569800947236998]
COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)

def check_seguranca():
    async def predicate(ctx):
        tem_cargo = any(role.id in IDS_CARGOS_PERMITIDOS for role in ctx.author.roles)
        if ctx.author.id in WHITELIST_USERS or tem_cargo or ctx.author.guild_permissions.administrator:
            return True
        await ctx.send("❌ Você não tem permissão para configurar o sistema de segurança.", ephemeral=True)
        return False
    return commands.check(predicate)

class seguranca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitor_ban = {}
        self.monitor_kick = {}
        self.monitor_cargos = {}
        self.spam_control = {}
        self.spam_warned = set() 
        self.anti_invite_ativo = {}
        self.anti_spam_ativo = {}

    def verificar_limite(self, member, dicionario, limite=10, tempo=60):
        if member.id in WHITELIST_USERS: return False
        if any(role.id in IDS_CARGOS_PERMITIDOS for role in member.roles): return False
        
        agora = datetime.datetime.now()
        user_id = member.id
        
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
    @check_seguranca()
    async def antiinvite(self, ctx, status: str):
        status = status.lower()
        if status not in ["on", "off"]: return await ctx.send("Use `on` ou `off`.")
        self.anti_invite_ativo[ctx.guild.id] = (status == "on")
        emoji = "✅" if status == "on" else "❌"
        await ctx.send(f"{emoji} | Anti-Invite: **{status.upper()}**")

    @commands.hybrid_command(name="antispam", description="Liga/Desliga anti-flood de mensagens")
    @check_seguranca()
    async def antispam(self, ctx, status: str):
        status = status.lower()
        if status not in ["on", "off"]: return await ctx.send("Use `on` ou `off`.")
        self.anti_spam_ativo[ctx.guild.id] = (status == "on")
        emoji = "✅" if status == "on" else "❌"
        await ctx.send(f"{emoji} | Anti-Spam (Flood): **{status.upper()}**")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if message.author.id in WHITELIST_USERS or any(role.id in IDS_CARGOS_PERMITIDOS for role in message.author.roles):
            return

        gid = message.guild.id
        
        if self.anti_invite_ativo.get(gid, False):
            invites = ["discord.gg/", "discord.com/invite/", "discord.me/", "discord.io/"]
            if any(invite in message.content.lower() for invite in invites):
                try:
                    await message.delete()
                    return await message.channel.send(f"⚠️ {message.author.mention}, proibido enviar convites.", delete_after=3)
                except: pass

        if self.anti_spam_ativo.get(gid, False):
            agora = datetime.datetime.now()
            user_id = message.author.id
            if user_id not in self.spam_control: self.spam_control[user_id] = []
            
            self.spam_control[user_id] = [t for t in self.spam_control[user_id] if (agora - t).total_seconds() < 5]
            self.spam_control[user_id].append(agora)

            if len(self.spam_control[user_id]) > 5:
                try:
                    await message.delete() 
                    if user_id not in self.spam_warned:
                        self.spam_warned.add(user_id)
                        await message.channel.send(f"❌ {message.author.mention}, pare de floodar!", delete_after=3)
                        await asyncio.sleep(15)
                        self.spam_warned.discard(user_id)
                except: pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await asyncio.sleep(0.5)
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            staff = entry.user
            if staff.bot or staff.id in WHITELIST_USERS: return
            if self.verificar_limite(staff, self.monitor_ban, limite=5, tempo=60):
                try:
                    if staff.top_role < guild.me.top_role:
                        await staff.edit(roles=[], reason="Anti-Raid: Mass Ban")
                        await self.enviar_log(guild, staff, "Remoção de cargos por Mass Ban.", discord.Color.red())
                except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await asyncio.sleep(0.5)
        guild = member.guild
        async for entry in guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
            if entry.target.id == member.id:
                staff = entry.user
                if staff.bot or staff.id in WHITELIST_USERS: return
                if self.verificar_limite(staff, self.monitor_kick, limite=5, tempo=60):
                    try:
                        if staff.top_role < guild.me.top_role:
                            await staff.edit(roles=[], reason="Anti-Raid: Mass Kick")
                            await self.enviar_log(guild, staff, "Remoção de cargos por Mass Kick.", discord.Color.red())
                    except: pass
                break

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if len(before.roles) < len(after.roles):
            if after.joined_at:
                tempo_no_servidor = (datetime.datetime.now(datetime.timezone.utc) - after.joined_at).total_seconds()
                if tempo_no_servidor < 30:
                    return

            await asyncio.sleep(1)
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                staff = entry.user
                if staff.bot or staff.id in WHITELIST_USERS or staff.id == after.id: 
                    return
                if self.verificar_limite(staff, self.monitor_cargos, limite=3, tempo=60):
                    try:
                        if staff.top_role < after.guild.me.top_role:
                            await staff.edit(roles=[], reason="Anti-Raid: Mass Role Update")
                            await self.enviar_log(after.guild, staff, "Remoção de cargos por Spam de Cargos.", discord.Color.red())
                    except: 
                        pass

async def setup(bot):
    await bot.add_cog(seguranca(bot))







