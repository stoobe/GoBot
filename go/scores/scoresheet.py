from __future__ import annotations

import pprint
from datetime import datetime

import gspread
import gspread.utils
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

CREDENTIALS_FILE = "../_google_sheets_credentials.json"


def number_to_column_letter(n):
    """Convert a column number to a spreadsheet column letter."""
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


# checks column A for non-empty values
def get_record_count(worksheet):
    column_a_values = worksheet.col_values(1)  # Column A is the 1st column
    non_empty_values = [value for value in column_a_values if value]
    return len(non_empty_values) - 1  # Subtract 1 to exclude the header row


def read_new_statbot_scores(sheet_name, tab_name, start_row=2) -> list[dict]:
    """
    start_row is a 1-based index to be consistent with Google Sheets.
    row 2 is the first row with data, row 1 is the header row.
    """

    assert start_row >= 2

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)  # type: ignore
    client = gspread.authorize(credentials)  # type: ignore

    # Open the Google Sheet and the specified tab
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(tab_name)

    # if worksheet.row_count < start_row:
    #     print(f'No new records found in tab "{tab_name}" in "{sheet_name}"')
    #     return []

    header_row = worksheet.row_values(1)

    column_count = len(header_row)
    ending_col = number_to_column_letter(column_count)

    # different than worksheet.row_count because row_count includes empty rows
    # +1 for 1-based indexing
    ending_row = get_record_count(worksheet) + 1

    data_range = f"A{start_row}:{ending_col}{ending_row}"

    scores = []
    if start_row <= ending_row:
        data_rows = worksheet.get_values(data_range)
        scores = [dict(zip(header_row, gspread.utils.numericise_all(row))) for row in data_rows]

    print(f'Read {len(scores)} scores from "{sheet_name}" in tab "{tab_name}" over range {data_range}')

    return scores


def convert_to_nested_dicts(df):

    def convert_row_to_nested_dicts(record: dict) -> dict:
        nested_record = {}
        for key, value in record.items():
            keys = key.split(".")
            d = nested_record
            for subkey in keys[:-1]:
                if subkey not in d:
                    d[subkey] = {}
                d = d[subkey]
            d[keys[-1]] = value
        return nested_record

    data_dicts = df.to_dict("records")
    nested_dicts = []

    for row in data_dicts:
        cleaned_row = {k: v for k, v in row.items() if v not in [None, ""]}
        nested_row = convert_row_to_nested_dicts(cleaned_row)
        nested_dicts.append(nested_row)

    return nested_dicts


def processs_statbot_scores(season, tab, scores):
    # Convert records to DataFrame
    df = pd.DataFrame(scores)

    df["date"] = df["date"].apply(lambda x: datetime.strptime(x, "%Y/%m/%d %H:%M:%S"))

    # Add to the front
    df.insert(0, "season", season["season"])
    df.insert(0, "league", season["league"])

    # rename match to game
    df.rename(columns={"match": "game"}, inplace=True)

    # split up column names so they can be nested in the mongo document
    # sub-dicts are separated by '.'
    def fix_col_name(col):
        for word in "Firearm Buff Sniper Shotgun SMG RocketLauncher Pistol Assault".split():
            col = col.replace(word, word + "_")
        col = col.replace("__", "_")
        col = col.replace("_", ".")
        return col

    df.columns = [fix_col_name(col) for col in df.columns]

    # move these columns ahead of the Firearm columns
    insert_position = df.columns.get_loc("damage") + 1  # type: ignore
    for col in "assists botkills botdamage".split():
        if col in df:
            column = df.pop(col)
            df.insert(insert_position, col, column)  # type: ignore

    df["loadedfrom.sheet"] = season["sheetname"]
    df["loadedfrom.tab"] = tab["name"]

    # verify all the columns we need are present
    for col in "league season date code game team player playfabid placement kills damage".split():
        assert col in df

    processed_scores = convert_to_nested_dicts(df)

    return processed_scores
