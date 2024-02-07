from datetime import datetime, timedelta
from dateutil import parser
import requests
import json
import config
import models.playfab as pf
from sqlmodel import Field, ForeignKey, Relationship, SQLModel, Session, create_engine, select

title_id = 'ca875' # pop1 title

def run_request(command, payload, headers): 
    api_url = f'https://{title_id}.playfabapi.com/Client/{command}'
    response = requests.post(api_url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        print("Request succeeded.")
        # print(json.dumps(response_data, indent=4))
        return response
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def playfab_id_to_hex(playfab_id):
    return hex(playfab_id + 2**63).upper()[2:]


def get_player_career_stats(playfab_id):
    headers = {
        'Content-Type': 'application/json',
        'X-Authorization': session_ticket
    }

    payload = {
        'PlayFabId': playfab_id_to_hex(playfab_id),
        'InfoRequestParameters':{
                'GetPlayerStatistics':True,
                'GetUserAccountInfo':False,
               'PlayerStatisticNames': ['CareerGamesPlayed','CareerKills','CareerDamage','CareerWins','MMR1','PlayerSkill']
                }
    }

    response = run_request('GetPlayerCombinedInfo', payload, headers)
    response_data = response.json()
    stat_name_to_val = {}
    for stat_json in response_data["data"]["InfoResultPayload"]["PlayerStatistics"]:
        stat_name_to_val[stat_json["StatisticName"]] = stat_json["Value"]

    stats = pf.CareerStats(
        date=datetime.now(),
        playfab_id=playfab_id,
        games=stat_name_to_val["CareerGamesPlayed"],
        wins=stat_name_to_val["CareerWins"],
        kills=stat_name_to_val["CareerGamesPlayed"],
        damage=stat_name_to_val["CareerDamage"],
        mmr=stat_name_to_val.get("MMR1", None),
        skill=stat_name_to_val.get("PlayerSkill", None)
    )
    print(f"statss: {stats}")
    return stats



##########################################
##########################################

def login_to_playfab():
    headers = {
        'Content-Type': 'application/json',
    }

    payload = {
        "TitleId": title_id,
        "Username": "devstooobe",  # Replace with the desired username
        "Email": "brianstube@gmail.com",  # Replace with the user's email
        "Password": config.playfab_pass # Replace with the user's password
    }

    response = run_request('LoginWithEmailAddress', payload, headers)
    response_data = response.json()
    global session_ticket
    session_ticket = response_data['data']['SessionTicket']
    print(f"session ticket {session_ticket}")

##########################################
##########################################

def get_leaderboard(start, count, stat_name="CareerWins"):
    headers = {
        'Content-Type': 'application/json',
        'X-Authorization': session_ticket
    }

    payload = {
        'MaxResultsCount': count,
        'StartPosition' : start,
        'StatisticName' : stat_name,
        'ProfileConstraints' : {
            'ShowLastLogin' : True,
            'ShowDisplayName' : True,
            'ShowCreated' : True,
        },
        # 'UseSpecificVersion' : True,
        # 'Version': 174 # <--- week number
    }

    response = run_request('GetLeaderboard', payload, headers)
    response_data = response.json()

    return response


##########################################
##########################################

def main():
        
    sqlite_file_name = "test.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    # sqlite_url = f"sqlite://" # in mem
    engine = create_engine(sqlite_url, echo=True)

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:

        login_to_playfab()

        start = 1700
        count = 100
        end = 10000
        while start<end:
            print("\n\n\n")
            print("======================================================")
            print(f"start {start}, end {end}, count {count}")
            print("======================================================")
            response = get_leaderboard(start=start, count=count)
            response_data = response.json()

            start += count

            for item in response_data["data"]["Leaderboard"]:
                print("\n")

                playfab_id = int(item["PlayFabId"],16) #playfabs are 16 digit Hex numbers (64 bit int)
                playfab_id -= 2**63
                print(f"Parsing {item['DisplayName']} with {item['StatValue']} career wins.")

                player = pf.Players(
                    playfab_id = playfab_id,
                    ign = item["DisplayName"],
                    account_created = parser.parse(item["Profile"]["Created"]),
                    last_login = parser.parse(item["Profile"]["LastLogin"])
                )

                print(player)
                statement = select(pf.Players).where(pf.Players.playfab_id == playfab_id)
                result = session.exec(statement).first()
                if result is not None:
                    print("Player already in DB")
                else:
                    session.add(player)
                    session.commit()
                
                statement = (
                    select(pf.IgnHistory)
                    .where(pf.IgnHistory.playfab_id == playfab_id)
                    .order_by(pf.IgnHistory.date_observed.desc())
                    .limit(1)
                )
                result = session.exec(statement).first()
                if result is not None and result.ign == player.ign:
                    print("IGN already is current one in IgnHistory")
                else:
                    ign_row = pf.IgnHistory(
                        playfab_id=playfab_id,
                        date_observed=datetime.now(),
                        ign=player.ign
                    )
                    session.add(ign_row)
                    session.commit()          

                statement = (
                    select(pf.CareerStats)
                    .where(pf.CareerStats.playfab_id == playfab_id)
                    .order_by(pf.CareerStats.date.desc())
                    .limit(1)
                )
                stats_row = session.exec(statement).first()
                now = datetime.now()
                if stats_row is not None and (now - stats_row.date) < timedelta(days=1):
                    # we already have pretty recent stats
                    print(f"recent stats: {stats_row}")
                    pass
                else:
                    stats = get_player_career_stats(playfab_id=playfab_id)
                    session.add(stats)
                    session.commit()          


        session.close()

if __name__=='__main__':
    main()