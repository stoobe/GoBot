import datetime
from datetime import date as datetype
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from pydantic import BaseModel
from sqlmodel import Session

from go.logger import create_logger
from go.go_db import GoDB, GoTeamPlayerSignup
from go.models import GoPlayer, GoTeam
from go.playfab_db import PlayfabDB
from go.exceptions import DiscordUserError, ErrorCode, GoDbError


logger = create_logger()


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


    group = app_commands.Group(name="go", description="...")
    # Above, we declare a command Group, in discord terms this is a parent command
    # We define it within the class scope (not an instance scope) so we can use it as a decorator.
    # This does have namespace caveats but i don't believe they're worth outlining in our needs.

    # @app_commands.command(name="top-command")
    # async def my_top_command(self, interaction: discord.Interaction) -> None:
    #   """ /top-command """
    #   await interaction.response.send_message("Hello from top level command!", ephemeral=True)


    def do_set_ign(self, player: DiscordUser, ign: str):
        
        with Session(self.engine) as session:
            # if GoPlayer doesn't exist create it
            if not self.godb.player_exists(discord_id=player.id, session=session): 
                go_p = GoPlayer(discord_id=player.id, discord_name=player.name)
                self.godb.create_player(go_player=go_p, session=session)
                
            go_p = self.godb.read_player(discord_id=player.id, session=session)
            
            if go_p is None:
                msg = f'Could not create/read player from DB for user {player.name}'
                raise DiscordUserError(msg, code=ErrorCode.DB_FAIL)
            
            # check if the ign has alredy been set (discord_id has associated playfab player_id)
            if go_p.pf_player_id is not None:
                pf_p = self.pfdb.read_player(pf_player_id=go_p.pf_player_id, session=session)
                msg = f'IGN for {player.name} already set to = {pf_p.ign}'
                raise DiscordUserError(msg)

            # lookup the playfab_player by ign
            pf_p = self.pfdb.read_player_by_ign(ign=ign, session=session)
            if pf_p == None:
                msg = f'Could not find any stats for IGN = {ign}'
                raise DiscordUserError(msg, code=ErrorCode.IGN_NOT_FOUND)

            go_p.pf_player_id = pf_p.id
            session.add(go_p)
            session.commit()


    @group.command( 
        description="Set your In Game Name"
        )
    async def set_ign(self, interaction: discord.Interaction, ign: str):
        player = convert_user(interaction.user)
        logger.info(f"Running set_ign({player.name}, {ign})")
        
        try:
            self.do_set_ign(player=player, ign=ign)
            msg = f'IGN for {player.name} set to "{ign}"'
            logger.info(msg)
            await interaction.response.send_message(msg) 
            
        except DiscordUserError as err:
            logger.warn(f"set_ign resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message) 



    def do_signup(self, players: List[DiscordUser], team_name: str, date: datetype) -> int:

        # make sure no players were skipped
        none_seen_at = None
        for i,p in enumerate(players):
            if p is not None and none_seen_at is not None:
                msg = f'Signup failed. Player{i+1} included but Player{none_seen_at+1} was not.'
                raise DiscordUserError(msg)
            if p is None:
                none_seen_at = i

        with Session(self.engine) as session:  
            
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

            try:
                self.godb.add_signup(team=go_team_by_roster, date=date, session=session)
            except GoDbError as err:
                # godb.add_signup checks that the players aren't on a different team that day
                # convert that error to this one we expect to throw
                raise DiscordUserError(err.args[0])
            
            session.refresh(go_team_by_roster)
            return go_team_by_roster.id

        
        
    @group.command( 
        description="Sign up your team to play on a day"
        )
    async def signup(self, interaction: discord.Interaction, 
                     player1: discord.Member, 
                     player2: discord.Member = None, 
                     player3: discord.Member = None,
                     team_name: str = None ):

        logger.info("")
        logger.info(f"GoCog.signup names ({interaction.channel}, {team_name}, {get_name(player1)}, {player2 and get_name(player2)}, {player3 and get_name(player3)})")
        logger.info(f"GoCog.signup ids   ({interaction.channel_id}, {team_name}, {player1.id}, {player2 and player2.id}, {player3 and player3.id})")

        date = datetime.date.today()

        players = [convert_user(player1)]
        players.append(convert_user(player2) if player2 else None)
        players.append(convert_user(player3) if player3 else None)
        
        if team_name:
            team_name = team_name.strip()
                
        try:
            team = self.do_signup(players=players, team_name=team_name, date=date)
            
            igns = [r.player.pf_player.ign for r in team.rosters]
            msg = f'Signed up "{team.team_name}" on {date} with players: {", ".join(igns)}.'
            msg += f'\nThis is signup #{len(team.signups)} for the team.'
            logger.info(msg)
            await interaction.response.send_message(msg)
            
        except DiscordUserError as err:
            logger.warn(f"signup resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message) 
        

    def do_cancel(self, player: DiscordUser, date: datetype) -> GoTeamPlayerSignup:
        
        with Session(self.engine) as session:  
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

        
        
    @group.command( 
        description="Cancel a signup for a day"
        )
    async def cancel(self, interaction: discord.Interaction):

        player = convert_user(interaction.user)

        logger.info("")
        logger.info(f"GoCog.cancel names ({interaction.channel}, {player.name})")
        logger.info(f"GoCog.cancel ids   ({interaction.channel_id}, {player.id})")

        date = datetime.date.today()
    
        try:
            tpsignup = self.do_cancel(player=player, date=date)
            
            msg = f'Cancelled "{tpsignup.team.team_name}" for session on {date}.'
            msg += f'\nThere are #{len(tpsignup.team.signups)} signups still active for the team.'
            logger.info(msg)
            await interaction.response.send_message(msg)
            
        except DiscordUserError as err:
            logger.warn(f"do_cancel resulted in error code {err.code}: {err.message}")
            await interaction.response.send_message(err.message) 
            


async def setup(bot: commands.Bot) -> None:
    logger.info("setup cog start")
    await bot.add_cog(GoCog(bot))
    logger.info("setup cog end")
