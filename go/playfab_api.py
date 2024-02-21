from typing import List
from attr import define
from icecream import ic

from datetime import datetime
from dateutil import parser
import requests
import json

import _config
from go.models import PfCareerStats


def as_playfab_id(player_id: int) -> str:
    return hex(player_id + 2**63).upper()[2:]


def as_player_id(playfab_id: str) -> int:
            player_id = int(playfab_id,16) #playfabs are 16 digit Hex numbers (64 bit int)
            player_id -= 2**63  # db is signed so make this range from -2^63 to + 2^63
            return player_id


class PlayfabApi:
    
    def __init__(self):
        self.session_ticket = None
        

    def run_request(self, command: str, payload: dict) -> requests.Response: 
        
        headers = {'Content-Type': 'application/json'}
        if self.session_ticket:
            headers['X-Authorization'] = self.session_ticket
        
        api_url = f'https://{_config.playfab_title_id}.playfabapi.com/Client/{command}'
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            print("Request succeeded.")
            return response
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None



    def get_player_career_stats(self, player_id: int) -> PfCareerStats:

        payload = {
            'PlayFabId': as_playfab_id(player_id),
            'InfoRequestParameters':{
                    'GetPlayerStatistics':True,
                    'GetUserAccountInfo':False,
                    'PlayerStatisticNames': ['CareerGamesPlayed','CareerKills','CareerDamage',
                                            'CareerWins','MMR1','PlayerSkill']
                    }
        }

        response = self.run_request('GetPlayerCombinedInfo', payload)
        response_data = response.json()
        stat_name_to_val = {}
        for stat_json in response_data["data"]["InfoResultPayload"]["PlayerStatistics"]:
            stat_name_to_val[stat_json["StatisticName"]] = stat_json["Value"]

        stats = PfCareerStats(
            date=datetime.now(),
            pf_player_id=player_id,
            games=stat_name_to_val["CareerGamesPlayed"],
            wins=stat_name_to_val["CareerWins"],
            kills=stat_name_to_val["CareerGamesPlayed"],
            damage=stat_name_to_val["CareerDamage"],
            mmr=stat_name_to_val.get("MMR1", None),
            skill=stat_name_to_val.get("PlayerSkill", None)
        )
        print(f"stats: {stats}")
        return stats


    def login_to_playfab(self) -> None:
        payload = {
            "TitleId": _config.playfab_title_id,
            "Username": _config.playfab_user,
            "Email": _config.playfab_email,
            "Password": _config.playfab_pass,
        }

        response = self.run_request('LoginWithEmailAddress', payload)
        response_data = response.json()
        self.session_ticket = response_data['data']['SessionTicket']
        print(f"session ticket set")


    @define
    class LeaderboardRow:
        player_id:int
        ign:str
        stat_value: int   
        stat_rank: int
        account_created: datetime
        last_login: datetime
        
        
    def get_leaderboard(self, start_rank:int, batchsize:int, stat_name:str="CareerWins") -> List[LeaderboardRow]:
        payload = {
            'MaxResultsCount': batchsize,
            'StartPosition' : start_rank,
            'StatisticName' : stat_name,
            'ProfileConstraints' : {
                'ShowLastLogin' : True,
                'ShowDisplayName' : True,
                'ShowCreated' : True,
            },
            # 'UseSpecificVersion' : True,
            # 'Version': 174 # <--- week number
        }

        response = self.run_request('GetLeaderboard', payload)
        response_data = response.json()

        leaderboard = []
        for item in response_data["data"]["Leaderboard"]:
            print(f"Parsing {item['DisplayName']} with {item['StatValue']}  {stat_name}.")

            lb_row = PlayfabApi.LeaderboardRow(
                player_id = as_player_id(item["PlayFabId"]),
                ign = item["DisplayName"],
                stat_value = item['StatValue'], 
                stat_rank = item['Position'],
                account_created = parser.parse(item["Profile"]["Created"]),
                last_login = parser.parse(item["Profile"]["LastLogin"])
                )
            
            ic(lb_row)
            leaderboard.append(lb_row)

        print(f"returning {len(leaderboard)} leaderboard items")
        return leaderboard
    
