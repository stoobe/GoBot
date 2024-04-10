import datetime
from datetime import date as datetype
from dateutil import parser
from typing import List

import dateutil
import discord
from discord import app_commands
from discord.ext import commands
from pydantic import BaseModel
from sqlmodel import Session

import _config

from go.logger import create_logger
from go.go_db import GoDB, GoTeamPlayerSignup
from go.models import GoPlayer, GoRatings, GoSchedule, GoSignup, GoTeam
from go.playfab_api import as_player_id, is_playfab_str
from go.playfab_db import PlayfabDB
from go.exceptions import DiscordUserError, ErrorCode, GoDbError


MY_GUILD = discord.Object(id=_config.guild_id)

logger = create_logger(__name__)


def get_name(member: discord.Member):
    if member is None:
        return ""
    return member.nick or member.global_name or member.display_name or member.name
    

class DiscordUser(BaseModel):
    id: int
    name: str

def convert_user(user: discord.Member):
    return DiscordUser(id=user.id, name=get_name(user))


class GoCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.engine = bot.engine #db cursor
        self.godb:GoDB = bot.godb
        self.pfdb:PlayfabDB = bot.pfdb


    go_group = app_commands.Group(name="go", description="GO League Commands")
    admin_group = app_commands.Group(name="go_admin", description="Admin Commands")
    
    # Above, we declare a command Group, in discord terms this is a parent command
    # We define it within the class scope (not an instance scope) so we can use it as a decorator.
    # This does have namespace caveats but i don't believe they're worth outlining in our needs.
    # @app_commands.command(name="top-command")
    # async def my_top_command(self, interaction: discord.Interaction) -> None:
    #   """ /top-command """
    #   await interaction.response.send_message("Hello from top level command!", ephemeral=True)


    def set_rating_if_needed(self, pf_player_id, session) -> float:
        
        # make sure the player has a rating
        # if not pull one in from recent career stats
        go_rating = self.godb.get_official_rating(pf_player_id=pf_player_id, session=session)
        
        if go_rating is None:
            go_rating = self.pfdb.calc_rating_from_stats(pf_player_id=pf_player_id, session=session)
            
            if go_rating is None:
                logger.error(f"In get_rating_default -- calc_rating_from_stats failed for id {pf_player_id}")
                return None
            else:
                official_rating = GoRatings(pf_player_id=pf_player_id,
                                            season=_config.go_season,
                                            rating_type='official',
                                            go_rating=go_rating)
                logger.info(f"In get_rating_default -- setting go_rating for {pf_player_id} to {go_rating:,.2f} from career stats")
                session.add(official_rating)
                session.commit()
                
        return go_rating


    def do_set_ign(self, player: DiscordUser, ign: str, session: Session) -> GoPlayer:
    
        # if GoPlayer doesn't exist create it
        if not self.godb.player_exists(discord_id=player.id, session=session): 
            go_p = GoPlayer(discord_id=player.id, discord_name=player.name)
            self.godb.create_player(go_player=go_p, session=session)
            
        go_p = self.godb.read_player(discord_id=player.id, session=session)
        
        if go_p is None:
            msg = f'Could not create/read player from DB for user {player.name}'
            raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)
        
        # check if the ign has already been set (discord_id has associated playfab player_id)
        if go_p.pf_player_id is not None:
            pf_p = self.pfdb.read_player(pf_player_id=go_p.pf_player_id, session=session)
            msg = f'IGN for {player.name} already set to {pf_p.ign}'
            raise DiscordUserError(msg)

        # lookup the playfab_player by ign
        pf_p = None
        pf_players = self.pfdb.read_players_by_ign(ign=ign, session=session)
        
        if len(pf_players) > 1:
            msg = f'Found {len(pf_players)} players with IGN = "{ign}". Reach out to @GO_STOOOBE to help fix this.'
            raise DiscordUserError(msg, code=ErrorCode.MISC_ERROR)
        elif len(pf_players) == 1:
            pf_p = pf_players[0]
        elif is_playfab_str(ign):
            pf_player_id = as_player_id(ign)
            pf_p = self.pfdb.read_player(pf_player_id=pf_player_id, session=session)

        if pf_p is None:
            msg = f'Could not find a Population One account with IGN = "{ign}"'
            raise DiscordUserError(msg, code=ErrorCode.IGN_NOT_FOUND)

        
        if pf_p.go_player is not None:
            msg = f'This IGN is allready associated with Discord user = "{pf_p.go_player.discord_name}"'
            raise DiscordUserError(msg, code=ErrorCode.MISC_ERROR)

        go_p.pf_player_id = pf_p.id
        session.add(go_p)

        session.commit()
        return go_p


    @go_group.command( 
        description="Set your In Game Name"
        )
    async def set_ign(self, interaction: discord.Interaction, ign: str):
        player = convert_user(interaction.user)
        logger.info(f"Running set_ign({player.name}, {ign})")
        
        try:
            with Session(self.engine) as session:

                go_p = self.do_set_ign(player=player, ign=ign, session=session)     
                                                
                go_rating = self.set_rating_if_needed(go_p.pf_player_id, session)
                if go_rating is None:
                    msg = f'Could not find a go_rating for {ign}.  Reach out to @GO_STOOOBE to help fix this.'
                    raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)
                       
                go_rating = self.godb.get_official_rating(pf_player_id=go_p.pf_player_id, session=session)
                msg = f'IGN for {player.name} set to "{ign}" with GO Rating {go_rating:,.0f}'

                stats = go_p.pf_player.career_stats[-1]
                msg += f'\n* Account created on {go_p.pf_player.account_created.date()}'                
                msg += f'\n* Career Stats: games={stats.games}, win rate={100.0*stats.wins/stats.games:.0f}%, kpg={stats.kills/stats.games:.1f}'
                
                logger.info(msg)
                await interaction.response.send_message(msg)
            
        except DiscordUserError as err:
            logger.warn(f"set_ign resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message) 


    @go_group.command( 
        description="Get the In Game Name for a user"
        )
    async def get_ign(self, 
                    interaction: discord.Interaction, 
                    user: discord.Member = None, 
                    ):
        
        if user is None:
            user = interaction.user
            
        player = convert_user(user)
        logger.info(f"Running get_ign({player.name})")
        
        try:
            with Session(self.engine) as session:
                
                go_p = self.godb.read_player(discord_id=player.id, session=session)
                if go_p is not None:
                    ign = go_p.pf_player.ign              
                    msg = f'IGN for {player.name} set to "{ign}"'
                else:
                    msg = f'{player.name} is not registered with GoBot'
                
                logger.info(msg)
                await interaction.response.send_message(msg) 
                    
        except DiscordUserError as err:
            logger.warn(f"get_ign resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message) 




    def do_signup(self, players: List[DiscordUser], team_name: str, date: datetype, session: Session) -> GoSignup:

        if not team_name:
            msg = f'Signup failed. Team name required.'
            raise DiscordUserError(msg)

        # make sure no players were skipped
        none_seen_at = None
        for i,p in enumerate(players):
            if p is not None and none_seen_at is not None:
                msg = f'Signup failed. Player{i+1} included but Player{none_seen_at+1} was not.'
                raise DiscordUserError(msg)
            if p is None:
                none_seen_at = i
        
        players = [p for p in players if p is not None]
        if len(players) == 0:
            msg = f'Signup failed. No players specified.'
            raise DiscordUserError(msg)
        
        go_players = []
        discord_ids = set()
        
        for player in players:
            discord_ids.add(player.id)
            go_player = self.godb.read_player(discord_id=player.id, session=session)
            go_players.append(go_player)
            if go_player is None or go_player.pf_player is None:
                msg = f'Signup failed. Player {player.name} needs run `/go set_ign`.'
                raise DiscordUserError(msg)
            
            # make sure all players have ratings
            player_rating = self.godb.get_official_rating(pf_player_id=go_player.pf_player_id, session=session)
            if player_rating is None:
                msg = f'Signup failed. Player {player.name} does not have a GO Rating. Contact @GO_STOOOBE to help fix this.'
                raise DiscordUserError(msg)

        if len(discord_ids) < len(players):
            msg = f'Signup failed. The same player can not be on one team twice.'
            raise DiscordUserError(msg)

        go_team_by_roster = self.godb.read_team_with_roster(discord_ids=discord_ids, session=session)        
        
        # make sure if our team already exists the name is the same
        if go_team_by_roster and go_team_by_roster.team_name != team_name:
            msg = f'Signup failed. Your team is already signed up with a different name: "{go_team_by_roster.team_name}".'
            raise DiscordUserError(msg)
        
        # read_team_with_name can handle team_name=None
        go_team_by_name = self.godb.read_team_with_name(team_name=team_name, session=session) 
        
        # if the team_name already exists make sure it's for our team
        if go_team_by_name:
            if not go_team_by_roster or go_team_by_roster.id != go_team_by_name.id:
                igns = [r.player.pf_player.ign for r in go_team_by_name.rosters]
                msg = f'Signup failed. Team name "{go_team_by_name.team_name}" is already taken by players {", ".join(igns)}.'
                raise DiscordUserError(msg)
                        
        # if it's an existing team
        if go_team_by_roster:
            # already signed up for today?
            signup_dates = [_.session_date for _ in go_team_by_roster.signups]
            if date in signup_dates:
                msg = f'Team "{team_name}" is already signed up for {date}.'
                raise DiscordUserError(msg)
                        
            # signed up for too many dates?
            if len(signup_dates) >= 4:
                msg = f'Signup failed. Team "{team_name}" is already signed up for {len(signup_dates)} dates (max is 4).'
                raise DiscordUserError(msg)

        # if it's a new team
        if go_team_by_roster is None:
            go_team_by_roster = self.godb.create_team(team_name=team_name, go_players=go_players, session=session)
            
        if go_team_by_roster is None:
            msg = f'Could not create team in DB'
            raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)

        rating_limit = _config.go_rating_limits.get(go_team_by_roster.team_size, None)
        if rating_limit is not None and go_team_by_roster.team_rating > rating_limit:
                msg = f'Signup failed. Team "{team_name}" rating {go_team_by_roster.team_rating:,.0f} is over the cap {rating_limit:,.0f}.'
                raise DiscordUserError(msg)

        try:
           signup = self.godb.add_signup(team=go_team_by_roster, date=date, session=session)
        except GoDbError as err:
            # godb.add_signup checks that the players aren't on a different team that day
            # convert that error to this one we expect to throw
            raise DiscordUserError(err.args[0])
        
        session.refresh(go_team_by_roster)
        return signup

        
        
    @go_group.command( 
        description="Sign up your team to play on a day"
        )
    async def signup(self, interaction: discord.Interaction, 
                     team_name: str, 
                     player1: discord.Member, 
                     player2: discord.Member = None, 
                     player3: discord.Member = None,):

        logger.info("")
        logger.info(f"GoCog.signup names ({interaction.channel}, {team_name}, {get_name(player1)}, {player2 and get_name(player2)}, {player3 and get_name(player3)})")
        logger.info(f"GoCog.signup ids   ({interaction.channel_id}, {team_name}, {player1.id}, {player2 and player2.id}, {player3 and player3.id})")
        
        with Session(self.engine) as session:  
            
            date = self.godb.get_session_date(session_id=interaction.channel_id, session=session)
            if date is None:
                msg = "Signup failed -- This channel hasn't been assigned as session date."
                logger.warn(msg)
                await interaction.response.send_message(msg)
                return

            players = [convert_user(player1)]
            players.append(convert_user(player2) if player2 else None)
            players.append(convert_user(player3) if player3 else None)
            
            if team_name:
                team_name = team_name.strip()
                    
            try:            
                signup = self.do_signup(players=players, team_name=team_name, date=date, session=session)

                team = signup.team

                igns = [r.player.pf_player.ign for r in team.rosters]
                msg = f'Signed up "{team.team_name}" on {date} with players: {", ".join(igns)}.'
                msg += f'\nTeam GO Rating is {team.team_rating:,.0f}.'
                msg += f'\nThis is signup #{len(team.signups)} for the team.'
                logger.info(msg)
                await interaction.response.send_message(msg)
                
            except DiscordUserError as err:
                logger.warn(f"signup resulted in error code {err.code}: {err.message}")
                await interaction.response.send_message(err.message) 
        

    def do_cancel(self, player: DiscordUser, date: datetype, session: Session) -> GoTeamPlayerSignup:
        # with Session(self.engine) as session:  
        tpsignups = self.godb.read_player_signups(session=session, discord_id=player.id, date=date)
        if len(tpsignups) == 0:
            msg = f'Cancel failed. Player {player.name} is not signed up on {date}.'
            raise DiscordUserError(msg)

        if len(tpsignups) > 1:
            logger.error(f"Somehow player {player.name} has signed up more than once on {date}")
            
        for tpsignup in tpsignups:
            logger.info(f"cancel row {tpsignup}")
            session.delete(tpsignup.signup)
        session.commit()
        
        tpsignup = tpsignups[0]
        session.refresh(tpsignup.team)
        session.refresh(tpsignup.player)
        return tpsignup

        
        
    @go_group.command( 
        description="Cancel a signup for a day"
        )
    async def cancel(self, interaction: discord.Interaction):

        player = convert_user(interaction.user)

        logger.info("")
        logger.info(f"GoCog.cancel names ({interaction.channel}, {player.name})")
        logger.info(f"GoCog.cancel ids   ({interaction.channel_id}, {player.id})")

        with Session(self.engine) as session:  

            date = self.godb.get_session_date(session_id=interaction.channel_id, session=session)
            if date is None:
                msg = "Cancel failed -- This channel hasn't been assigned as session date."
                logger.warn(msg)
                await interaction.response.send_message(msg)
                return
                
            try:            
                tpsignup = self.do_cancel(player=player, date=date, session=session)
                
                msg = f'Cancelled "{tpsignup.team.team_name}" for session on {date}.'
                msg += f'\nThere are {len(tpsignup.team.signups)} signups still active for the team.'
                logger.info(msg)
                await interaction.response.send_message(msg)
            
            except DiscordUserError as err:
                logger.warn(f"do_cancel resulted in error code {err.code}: {err.message}")
                await interaction.response.send_message(err.message) 



    @go_group.command( 
        description="List the teams playing today"
        )
    async def list_teams(
            self, 
            interaction: discord.Interaction
        ):
        
        logger.info(f"Running list_teams on  channel_id: {interaction.channel_id}  channel.name: {interaction.channel.name}")
        
        with Session(self.engine) as session:  
            session_id = interaction.channel_id
            date = self.godb.get_session_date(session_id=session_id, session=session)
            
            msg = ''
            if date is None:
                msg = 'This channel has no games to signup for.'
            else:
                teams = self.godb.get_teams_for_date(session_date=date, session=session)
                msg = ''
                player_count = 0
                for team in teams:
                    session.refresh(team)
                    players = [r.player for r in team.rosters]
                    players_str = ''
                    for p in players:
                        player_count += 1
                        session.refresh(p.pf_player)
                        if players_str:
                            players_str += ', '
                        players_str += p.pf_player.ign
                    rating_str = f'{team.team_rating:,.0f}' if team.team_rating else 'None'
                    msg += f'**{team.team_name}** (*{rating_str}*) -- {players_str}\n'
                msg = f'**teams:** {len(teams)}\n**players:** {player_count}\n\n' + msg 
            logger.info(msg)
            await interaction.response.send_message(msg) 
            

    @admin_group.command( 
        description="Admin tool for syncing commands"
        )
    async def sync(self, interaction: discord.Interaction):
        logger.info(f'Command sync called by user {get_name(interaction.user)}.')
        if interaction.user.id != _config.owner_id:
            await interaction.response.send_message('You dont have permission to use this command!')
            return

        await interaction.response.send_message('Sync starting.')
        self.bot.tree.copy_global_to(guild=MY_GUILD)
        await self.bot.tree.sync(guild=MY_GUILD)
        
        await interaction.user.send('Command tree synced.')
        logger.info('Command tree synced.')


    @admin_group.command()
    async def clear_commands(self, interaction: discord.Interaction):
        logger.info(f'Command clear_commands alled by user {get_name(interaction.user)}.')
        if interaction.user.id != _config.owner_id:
            await interaction.response.send_message('You dont have permission to use this command!')
            return

        await interaction.response.send_message('clear_commands starting.')
        await self.bot.tree.sync(guild=MY_GUILD)
        self.bot.tree.clear_commands(guild=MY_GUILD)
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()
        
        await interaction.user.send('clear_commands complete.')
        logger.info(f'clear_commands complete.')




    @admin_group.command( 
        description="Admin tool to set a user's In Game Name"
        )
    async def set_ign(
            self, 
            interaction: discord.Interaction, 
            user: discord.Member, 
            ign: str
        ):
        if interaction.user.id != _config.owner_id:
            await interaction.response.send_message('You dont have permission to use this command!')
            return
        
        player = convert_user(user)
        logger.info(f"Running go_admin.set_ign({player.name}, {ign})")
        
        try:
            with Session(self.engine) as session:
                
                go_p = self.do_set_ign(player=player, ign=ign, session=session)
                         
                go_rating = self.set_rating_if_needed(go_p.pf_player_id, session)
                if go_rating is None:
                    msg = f'Could not find a go_rating for {ign}.  Reach out to @GO_STOOOBE to help fix this.'
                    raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)
                                       
                msg = f'IGN for {player.name} set to "{ign}" with GO Rating {go_rating:,.0f}'
                logger.info(msg)
                await interaction.response.send_message(msg) 
            
        except DiscordUserError as err:
            logger.warn(f"set_ign resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message) 


    

    @admin_group.command( 
        description="Set the session date for this channel"
        )
    async def set_session_date(
            self, 
            interaction: discord.Interaction, 
            date: str
        ):
        if interaction.user.id != _config.owner_id:
            await interaction.response.send_message('You dont have permission to use this command!')
            return
        
        logger.info(f"Running go_admin.set_session_date({date})")
        
        try:
            date2 = parser.parse(date).date()
            
            with Session(self.engine) as session:  
                session_id=interaction.channel_id
                self.godb.set_session_date(session_id=session_id, session_date=date2, session=session)
                msg = f'Session date for "{interaction.channel.name}" set to {date2}'
                logger.info(msg)
                await interaction.response.send_message(msg) 

        except parser.ParserError as err:
            msg = f"Error: Could not parse date string '{date}'"
            logger.warn(msg)
            await interaction.response.send_message(msg)


    @admin_group.command( 
        description="Get the session date for this channel"
        )
    async def get_session_date(
            self, 
            interaction: discord.Interaction
        ):
        if interaction.user.id != _config.owner_id:
            await interaction.response.send_message('You dont have permission to use this command!')
            return
        
        logger.info(f"Running go_admin.get_session_date")
        
        with Session(self.engine) as session:  
            session_id = interaction.channel_id
            date = self.godb.get_session_date(session_id=session_id, session=session)
            msg = f'Session date for "{interaction.channel.name}" is {date}'            
            logger.info(msg)
            await interaction.response.send_message(msg) 


    
    
    async def cog_load(self):
        logger.info(f"cog_load()")

        


async def setup(bot: commands.Bot) -> None:
    logger.info("setup cog start")
    await bot.add_cog(GoCog(bot))
    logger.info("setup cog end")
