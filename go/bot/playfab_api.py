import json
import re
from datetime import datetime
from typing import List, Optional

import requests
from attr import define
from dateutil import parser

from config import _config 
from go.bot.logger import create_logger
from go.bot.models import PfCareerStats, PfPlayer

logger = create_logger(__name__)


def as_playfab_id(player_id: int) -> str:
    return hex(player_id + 2**63).upper()[2:]


def as_player_id(playfab_id: str) -> int:
    # playfabs are 16 digit Hex numbers (64 bit int)
    player_id = int(playfab_id, 16)
    player_id -= 2**63  # db is signed so make this range from -2^63 to + 2^63
    return player_id


playfab_pattern = re.compile(r"([0-9A-F]{16})")


def is_playfab_str(s):
    global playfab_pattern
    if s is None:
        return False
    m = re.fullmatch(playfab_pattern, s)
    if m:
        return True
    else:
        return False


class PlayfabApi:

    #
    def __init__(self):
        self.session_ticket = None

    #
    def login_to_playfab(self) -> None:
        payload = {
            "TitleId": _config.playfab_title_id,
            "Username": _config.playfab_user,
            "Email": _config.playfab_email,
            "Password": _config.playfab_pass,
        }

        response = self.run_request("LoginWithEmailAddress", payload)
        if response is None:
            raise Exception("Failed to login to Playfab")

        response_data = response.json()
        self.session_ticket = response_data["data"]["SessionTicket"]
        logger.info(f"login_to_playfab: session ticket set")

    #
    def run_request(self, command: str, payload: dict) -> Optional[requests.Response]:

        headers = {"Content-Type": "application/json"}
        if self.session_ticket:
            headers["X-Authorization"] = self.session_ticket

        api_url = f"https://{_config.playfab_title_id}.playfabapi.com/Client/{command}"
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"run_request for {command = } succeeded with response {json.dumps(response.json(),indent=3)}")
            return response
        else:
            logger.error(
                f"Error: run_request for {command = } failed with response {response.status_code} - {response.text}"
            )
            return None

    #
    def get_player_career_stats(self, player_id: int) -> PfCareerStats:

        payload = {
            "PlayFabId": as_playfab_id(player_id),
            "InfoRequestParameters": {
                "GetPlayerStatistics": True,
                "GetUserAccountInfo": False,
                "PlayerStatisticNames": [
                    "CareerGamesPlayed",
                    "CareerKills",
                    "CareerDamage",
                    "CareerWins",
                    "MMR1",
                    "PlayerSkill",
                ],
            },
        }

        response = self.run_request("GetPlayerCombinedInfo", payload)
        stat_name_to_val = {}

        if response:
            response_data = response.json()
            for stat_json in response_data["data"]["InfoResultPayload"]["PlayerStatistics"]:
                stat_name_to_val[stat_json["StatisticName"]] = stat_json["Value"]

        stats = PfCareerStats(
            date=datetime.now(),
            pf_player_id=player_id,
            games=stat_name_to_val.get("CareerGamesPlayed", 0),
            wins=stat_name_to_val.get("CareerWins", 0),
            kills=stat_name_to_val.get("CareerKills", 0),
            damage=stat_name_to_val.get("CareerDamage", 0),
            mmr=stat_name_to_val.get("MMR1", None),
            skill=stat_name_to_val.get("PlayerSkill", None),
        )
        return stats

    #
    def get_player_from_account_info(
        self, player_id: Optional[int] = None, playfab_id: Optional[str] = None
    ) -> Optional[PfPlayer]:

        if player_id is None:
            if playfab_id is None:
                # both None, no player to search for
                return None
            else:
                player_id = as_player_id(playfab_id)
        else:
            if playfab_id is None:
                playfab_id = as_playfab_id(player_id)
            else:
                # make sure playfab_id and player_id are the same player
                playfab_id2 = as_playfab_id(player_id)
                assert playfab_id == playfab_id2

        try:
            payload = {
                "PlayFabId": playfab_id,
                "InfoRequestParameters": {
                    "GetPlayerProfile": True,
                    "GetUserAccountInfo": False,
                    "ProfileConstraints": {
                        "ShowLastLogin": True,
                        "ShowDisplayName": True,
                        "ShowCreated": True,
                        "ShowAvatarUrl": True,
                    },
                },
            }

            response = self.run_request("GetPlayerCombinedInfo", payload)
            if not response:
                return None

            response_data = response.json()
            profile_info = response_data["data"]["InfoResultPayload"]["PlayerProfile"]

            pf_p = PfPlayer(
                id=player_id,
                ign=profile_info["DisplayName"],
                account_created=parser.parse(profile_info["Created"]),
                last_login=parser.parse(profile_info["LastLogin"]),
                avatar_url=profile_info["AvatarUrl"],
            )
            return pf_p

        except Exception as e:
            logger.error(e)
            return None

    #
    @define
    class LeaderboardRow:
        player_id: int
        ign: str
        stat_value: int
        stat_rank: int
        account_created: datetime
        last_login: datetime

    #
    # stat_name options = CareerWins, CareerKills, CareerDamage, WeeklyWinsTotal, WeeklyKillsTotal
    def get_leaderboard(self, start_rank: int, batchsize: int, stat_name: str = "CareerWins") -> List[LeaderboardRow]:
        payload = {
            "MaxResultsCount": batchsize,
            "StartPosition": start_rank,
            "StatisticName": stat_name,
            "ProfileConstraints": {
                "ShowLastLogin": True,
                "ShowDisplayName": True,
                "ShowCreated": True,
            },
            # 'UseSpecificVersion' : True,
            # 'Version': 174 # <--- week number
        }

        response = self.run_request("GetLeaderboard", payload)

        if response is None:
            return []

        response_data = response.json()
        leaderboard = []
        for item in response_data["data"]["Leaderboard"]:
            try:
                logger.info(
                    f"get_leaderboard() -- parsing entry for player {item['DisplayName']} with {item['StatValue']} {stat_name}."
                )

                lb_row = PlayfabApi.LeaderboardRow(
                    player_id=as_player_id(item["PlayFabId"]),
                    ign=item["DisplayName"],
                    stat_value=item["StatValue"],
                    stat_rank=item["Position"],
                    account_created=parser.parse(item["Profile"]["Created"]),
                    last_login=parser.parse(item["Profile"]["LastLogin"]),
                )

                logger.debug(f"get_leaderboard() -- row: {lb_row}")
                leaderboard.append(lb_row)
            except KeyError as err:
                logger.error(f"Skipping: KeyError {err} on {item = }")

        logger.info(f"get_leaderboard() -- returning {len(leaderboard)} items")
        return leaderboard


## how to get stats for past weeks
# headers = {
#     'Content-Type': 'application/json',
#     #'X-SecretKey': api_key,
#     'X-Authorization': session_ticket
# }
# payload = {
#     # 'PlayFabId': stooobe_playfabid,
#     # 'MaxResultsCount': 10,
#     'StatisticName' : "WeeklyKillsTotal",
#   }
# response = run_request('GetPlayerStatisticVersions', payload, headers)
# print(response)
