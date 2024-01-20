import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import datetime

def discord_name(member: discord.Member):
    return member.nick or member.global_name or member.display_name or member.name

class GoDb:
    """
    cur.execute("CREATE TABLE teams(team_id INTEGER PRIMARY KEY, team_name UNIQUE, player_count)")
    cur.execute("CREATE TABLE players(discord_id, discord_name, pfid, ign)")
    cur.execute("CREATE TABLE rosters(team_id, discord_id)")
    cur.execute("CREATE TABLE signups(date, team_id)")
    cur.execute("CREATE TABLE ratings(pfid UNIQUE, ign, go_rating)")
    """

    def __init__(self, cur):
        self.cur = cur


    def get_player_signups(self, discord_id:int, date:datetime.date=None):
        
        base_query = "SELECT s.date, r.team_id, t.team_name, r.discord_id " + \
                    "FROM signups as s, rosters as r, teams as t " + \
                    "WHERE s.team_id=r.team_id and r.team_id=t.team_id"
        
        if date is None:
            query = base_query + " and discord_id=?"
            self.cur.execute(query, (discord_id,))
        else:
            query = base_query + " and discord_id=? and date=?"
            #print(f"query {query}")
            self.cur.execute(query, (discord_id, date))

        result = self.cur.fetchall()
        #print(f"get_player_signups({discord_id}, {date})--> {result}")
        for row in result:
            row.date = datetime.date.fromisoformat(row.date)
        print(f"get_player_signups({discord_id}, {date})--> {result}")
        return result
    

    def get_team_id(self, team_name:str):
        self.cur.execute("SELECT team_id FROM teams WHERE team_name=?", (team_name,))
        result = self.cur.fetchone()
        if result is None:
            result = None
        else:
            result = result.team_id
        print(f"get_team_id({team_name}) = {result}")
        return result

    def get_team_name(self, team_id:int):
        self.cur.execute("SELECT * FROM teams WHERE team_id=?", (team_id,))
        result = self.cur.fetchone()
        if result is None:
            result = None
        else:
            result = result.team_name
        print(f"get_team_name({team_id}) = {result}")
        return result

    def get_max_team_id(self):
        self.cur.execute("SELECT max(team_id) as team_id FROM teams")
        result = self.cur.fetchone()
        # print(f"SELECT max(team_id) FROM teams --> {result}")
        if result is None or result.team_id is None:
            result = 0
        else:
            result = result.team_id
        print(f"get_max_team_id() = {result}")
        return result


    def get_signup_dates(self, team_id:int):
        self.cur.execute('SELECT date FROM signups WHERE team_id=?', (team_id,))
        dates = set()
        result = self.cur.fetchall()
        for row in result:
            d = datetime.date.fromisoformat(row.date)
            dates.add(d)
        print(f"SELECT date FROM signups WHERE team_id={team_id} --> {result}")
        print(f"get_signup_dates({team_id}) = {dates}")
        return dates


    def get_roster(self, team_id:int):
        self.cur.execute("SELECT discord_id FROM rosters WHERE team_id=?", (team_id,))
        discord_ids = set()
        result = self.cur.fetchall()
        for row in result:
            discord_ids.add(row.discord_id)
        print(f"SELECT discord_id FROM rosters --> {result}")
        print(f"get_roster({team_id}) = {discord_ids}")
        return discord_ids

#  players(discord_id, discord_name, pfid, ign
    
    def get_discord_names(self, discord_ids: set):
        discord_names = set()
        for did in discord_ids:
            self.cur.execute("SELECT discord_name FROM players WHERE discord_id=?", (did,))
            result = self.cur.fetchone()
            print(f"discord_name fetchone {result}")
            if result is not None and result.discord_name is not None:
                discord_names.add(result.discord_name)

        print(f"get_discord_names({discord_ids}) = {discord_names}")
        return discord_names    


    def get_player_count(self, discord_id=None, ign=None):
        if discord_id is not None:
            if ign is not None:
                self.cur.execute("SELECT count(*) as n FROM players WHERE discord_id=? and ign=?", (discord_id, ign))
            else: 
                self.cur.execute("SELECT count(*) as n FROM players WHERE discord_id=?", (discord_id,))
        else:
            if ign is not None:
                self.cur.execute("SELECT count(*) as n FROM players WHERE ign=?", (ign,))
            else: 
                self.cur.execute("SELECT count(*) as n FROM players")
        result = self.cur.fetchone().n
    
        print(f"get_player_count({discord_id}, {ign}) = {result}")
        return result
    

    def is_player_ign_set(self, discord_id):
        return self.get_player_count(discord_id=discord_id) > 0



class GoCog(commands.Cog):


    def __init__(self, bot: commands.Bot) -> None:
       self.bot = bot
       self.cur = bot.cur #db cursor
       self.godb = GoDb(self.cur)    

    group = app_commands.Group(name="go", description="...")
    # Above, we declare a command Group, in discord terms this is a parent command
    # We define it within the class scope (not an instance scope) so we can use it as a decorator.
    # This does have namespace caveats but i don't believe they're worth outlining in our needs.

    # @app_commands.command(name="top-command")
    # async def my_top_command(self, interaction: discord.Interaction) -> None:
    #   """ /top-command """
    #   await interaction.response.send_message("Hello from top level command!", ephemeral=True)


    @group.command( # we use the declared group to make a command.
        description="Set your In Game Name"
        )
    async def set_ign(self, interaction: discord.Interaction, ign: str):
        print(f"\nset ign({discord_name(interaction.user)}, {ign})")

        if(self.godb.get_player_count(interaction.user.id, ign)>0):
            await interaction.response.send_message(f'ign for {discord_name(interaction.user)} already set to = {ign}') 
        else:
            self.cur.execute("INSERT INTO players VALUES (?,?,?,?)", (interaction.user.id,
                discord_name(interaction.user), 0, ign))
            self.cur.connection.commit()

        await interaction.response.send_message(f'IGN set to "{ign}"') 


    @group.command( # we use the declared group to make a command.
        description="Sign up team to play on a day"
        )
    async def signup(self, interaction: discord.Interaction, 
                     team_name: str, 
                     player1: discord.Member, 
                     player2: discord.Member = None, 
                     player3: discord.Member = None):

        print(f"\nsignup({team_name}, {player1}, {player2}, {player3})")

        date = datetime.date.today()

        discord_ids = set()
        discord_ids.add(player1.id)
        if player2: discord_ids.add(player2.id)
        if player3: discord_ids.add(player3.id)

        if not self.godb.is_player_ign_set(player1.id):
            await interaction.response.send_message(f'Signup failed. Player {discord_name(player1)} needs run `/go set_ign`.')
            return
        
        if (player2 is not None) and not self.godb.is_player_ign_set(player2.id):
            await interaction.response.send_message(f'Signup failed. Player {discord_name(player2)} needs run `/go set_ign`.')
            return
        
        if (player3 is not None) and not self.godb.is_player_ign_set(player3.id):
            await interaction.response.send_message(f'Signup failed. Player {discord_name(player3)} needs run `/go set_ign`.')
            return
        
        if player3 and not player2:
            await interaction.response.send_message(f'Signup failed. Player3 included but Player2 was not.')
            return

        if player2 is not None and len(discord_ids)<2:
            await interaction.response.send_message(f'Signup failed. Duplicate players detected.')
            return
        
        if player3 is not None and len(discord_ids)<3:
            await interaction.response.send_message(f'Signup failed. Duplicate players detected.')
            return
        

        team_id = self.godb.get_team_id(team_name=team_name)

        # if it's an existing team
        if team_id is not None:

            discord_ids_db = self.godb.get_roster(team_id=team_id)
            print(f"discord_ids in command: {discord_ids}")
            print(f"discord_ids in db     : {discord_ids_db}")

            # check the players are the same
            if discord_ids!=discord_ids_db:
                other_roster = self.godb.get_discord_names(discord_ids=discord_ids_db)
                await interaction.response.send_message(f'Signup failed. Team name "{team_name}" already exists but with different players ({", ".join(other_roster)}).')
                return
            
            signup_dates = self.godb.get_signup_dates(team_id=team_id)

            # already signed up for today?
            if date in signup_dates:
                await interaction.response.send_message(f'Team "{team_name}" is already signed up for {date}.')
                return
                        
            # signed up for too many dates?
            if len(signup_dates) >= 4:
                await interaction.response.send_message(f'Signup failed. Team "{team_name}" is already signed up for {len(signup_dates)} dates (max is 4).')
                return
        
        # check that the players aren't on a different team today
        for player in [player1, player2, player3]:
            if player is None:
                continue

            rows = self.godb.get_player_signups(discord_id=player.id, date=date)
            if len(rows) > 0:
                other_team = self.godb.get_team_name(rows[0].team_id)
                await interaction.response.send_message(f'Signup failed. Player {discord_name(player)} already signed up on {date} with team "{other_team}".')
                return

        # # make sure the player includes themselves in the roster
        # if interaction.user.id not in discord_ids:
        #         await interaction.response.send_message(f'Signup failed. Player signing up ({discord_name(interaction.user)}) must be on the roster".')
        #         return

        # if it's a new team
        if team_id is None:
            
            team_id = self.godb.get_max_team_id() + 1
            self.cur.execute("INSERT INTO teams VALUES (?,?,?)", (team_id, team_name, len(discord_ids)))

            for player_id in sorted(discord_ids):
                self.cur.execute("INSERT INTO rosters VALUES (?,?)", (team_id, player_id))

        self.cur.execute("INSERT INTO signups VALUES (?,?)", (date, team_id))
        self.cur.connection.commit()

        roster = self.godb.get_discord_names(discord_ids=discord_ids)
        signup_dates = self.godb.get_signup_dates(team_id=team_id)
        n = len(signup_dates)
        await interaction.response.send_message(f'Signed up "{team_name}" on {date} with players: {", ".join(roster)}. \nThis is signup #{n} for the team.')


    @group.command( # we use the declared group to make a command.
        description="Cancel a signup for a day"
        )
    async def cancel(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'cancelling your signup')         


async def setup(bot: commands.Bot) -> None:
    print("setup cog start")
    await bot.add_cog(GoCog(bot))
    print("setup cog end")
