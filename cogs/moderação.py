import discord
from discord.ext import commands

class moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="up", description="Promove um membro a um cargo")
    @commands.has_permissions(manage_roles=True)
    async def up(self, ctx, membro: discord.Member, *, cargo: discord.Role):
        """Uso: ?up @membro Nome do Cargo OU ID"""
        
        # O defer é essencial para comandos híbridos não expirarem
        if ctx.interaction:
            await ctx.defer()

        # --- TRAVA DE HIERARQUIA DO AUTOR ---
        if ctx.author.top_role.position <= cargo.position and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(f"❌ Você não pode dar um cargo que é superior ou igual ao seu ({cargo.mention}).")

        # --- TRAVA DE HIERARQUIA DO BOT ---
        if cargo.position >= ctx.guild.me.top_role.position:
            return await ctx.send(f"❌ Erro de Hierarquia: O cargo {cargo.name} está acima do meu cargo mais alto. Arraste meu cargo para cima dele nas configurações.")

        if cargo in membro.roles:
            return await ctx.send(f"❌ {membro.mention} já possui o cargo {cargo.mention}")

        try:
            await membro.add_roles(cargo, reason=f"Promovido por {ctx.author}")
            await ctx.send(
                f"✅ {membro.mention} foi promovido para o cargo {cargo.mention}",
                allowed_mentions=discord.AllowedMentions(roles=False)
            )
        
        except discord.Forbidden:
            await ctx.send("❌ Eu não tenho permissão de 'Gerenciar Cargos' ou meu cargo está abaixo do necessário.")
        
        except Exception as e:
            await ctx.send(f"❌ Erro inesperado: {e}")

    @commands.hybrid_command(name="demote", description="Remove um cargo de um membro")
    @commands.has_permissions(manage_roles=True)
    async def demote(self, ctx, membro: discord.Member, *, cargo: discord.Role):
        """Uso: ?demote @membro Nome do Cargo OU ID"""

        if ctx.interaction:
            await ctx.defer()

        # --- TRAVA DE HIERARQUIA DO AUTOR ---
        if ctx.author.top_role.position <= cargo.position and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(f"❌ Você não pode remover um cargo que é superior ou igual ao seu ({cargo.mention}).")

        # --- TRAVA DE HIERARQUIA DO BOT ---
        if cargo.position >= ctx.guild.me.top_role.position:
            return await ctx.send(f"❌ Erro de Hierarquia: Não posso remover o cargo {cargo.name} porque ele é superior ao meu.")

        try:
            if cargo in membro.roles:
                await membro.remove_roles(cargo, reason=f"Rebaixado por {ctx.author}")
                await ctx.send(
                    f"⚠️ {membro.mention} foi rebaixado e perdeu o cargo {cargo.mention}",
                    allowed_mentions=discord.AllowedMentions(roles=False)
                )
            else:
                await ctx.send(f"❌ {membro.mention} não possui o cargo {cargo.mention}.")
        
        except discord.Forbidden:
            await ctx.send("❌ Falha na permissão: Verifique se meu cargo tem 'Gerenciar Cargos' e está acima do cargo alvo.")
        
        except Exception as e:
            await ctx.send(f"❌ Erro ao remover cargo: {e}")

async def setup(bot):
    await bot.add_cog(moderacao(bot))

