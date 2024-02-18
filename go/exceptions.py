from enum import Enum

class PlayerNotFoundError(Exception):
    pass

class GoDbError(Exception):
    pass

class DataNotDeletedError(Exception):
    pass


class ErrorCode(Enum):
    DB_FAIL = 0
    MISC_ERROR = 1
    IGN_NOT_FOUND = 2
    

class DiscordUserError(Exception):
    def __init__(self, message: str, code: ErrorCode = ErrorCode.MISC_ERROR):
        self.code = code
        self.message = message