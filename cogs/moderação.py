import discord
from discord.ext import commands

class moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="up")
    @commands.has_permissions(manage_roles=True)
    async def up(self, ctx, membro: discord.Member, *, cargo: discord.Role):
        """Uso: ?up @membro Nome do Cargo OU ID"""
        
        if cargo in membro.roles:
            return await ctx.send(f"❌ {membro.mention} já possui o cargo {cargo.mention}")

        try:
            await membro.add_roles(cargo)
             
            await ctx.send(
                f"✅ {membro.mention} foi promovido para o cargo {cargo.mention}",
                allowed_mentions=discord.AllowedMentions(roles=False)
            )
        
        except discord.Forbidden:
            await ctx.send("❌ Erro de Hierarquia: Meu cargo precisa estar **ACIMA** do cargo que você quer dar")
        
        except Exception as e:
            await ctx.send(f"❌ Erro inesperado: {e}")

    @commands.hybrid_command(name="demote")
    @commands.has_permissions(manage_roles=True)
    async def demote(self, ctx, membro: discord.Member, *, cargo: discord.Role):
        """Uso: ?demote @membro Nome do Cargo OU ID"""

        try:
            if cargo in membro.roles:
                await membro.remove_roles(cargo)
                await ctx.send(
                    f"⚠️ {membro.mention} foi rebaixado e perdeu o cargo {cargo.mention}",
                    allowed_mentions=discord.AllowedMentions(roles=False)
                )
            else:
                await ctx.send(f"❌ {membro.mention} não possui o cargo {cargo.mention}?")
        
        except discord.Forbidden:
            await ctx.send("❌ Erro de Hierarquia: Meu cargo precisa estar **ACIMA** do cargo que você quer remover")
        
        except Exception as e:
            await ctx.send(f"❌ Erro ao remover cargo: {e}")

async def setup(bot):
    await bot.add_cog(moderacao(bot))