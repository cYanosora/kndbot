from plugins.pjsk._config import MAINTAIN_ERROR, USER_BAN_ERROR, NOT_SERVER_ERROR, TIMEOUT_ERROR, QUERY_BAN_ERROR


class maintenanceIn(Exception):
    def __init__(self, error=MAINTAIN_ERROR):
        self.e = error

    def __str__(self):
        return self.e


class userIdBan(Exception):
    def __init__(self, error=USER_BAN_ERROR):
        self.e = error

    def __str__(self):
        return self.e


class apiCallError(Exception):
    def __init__(self, error=TIMEOUT_ERROR):
        self.e = error

    def __str__(self):
        return self.e


class serverNotSupported(Exception):
    def __init__(self, error=NOT_SERVER_ERROR):
        self.e = error

    def __str__(self):
        return self.e


class QueryBanned(Exception):
    def __init__(self, error=QUERY_BAN_ERROR):
        self.e = error

    def __str__(self):
        return self.e
