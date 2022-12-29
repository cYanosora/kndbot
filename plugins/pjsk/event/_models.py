import datetime
import pytz
from plugins.pjsk._config import data_path
try:
    import ujson as json
except:
    import json


class EventInfo(object):

    def __init__(self):
        self.id = 0
        self.eventType = ''
        self.name = ''
        self.assetbundleName = ''
        self.startAt = ''
        self.aggregateAtorin = 0
        self.aggregateAt = ''
        self.unit = ''
        self.bonusechara = []
        self.bonuseattr = ''
        self.music = 0
        self.cards = []

    def getevent(self, eventid):
        with open(data_path / 'events.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        with open(data_path / 'eventCards.json', 'r', encoding='utf-8') as f:
            eventCards = json.load(f)
        with open(data_path / 'eventDeckBonuses.json', 'r', encoding='utf-8') as f:
            eventDeckBonuses = json.load(f)
        for events in data:
            if eventid == events['id']:
                self.id = events['id']
                self.eventType = events['eventType']
                self.name = events['name']
                self.assetbundleName = events['assetbundleName']
                self.startAt = datetime.datetime.fromtimestamp(
                    events['startAt'] / 1000, pytz.timezone('Asia/Shanghai')
                ).strftime('%Y/%m/%d %H:%M:%S')
                self.aggregateAtorin = events['aggregateAt']
                self.aggregateAt = datetime.datetime.fromtimestamp(
                    events['aggregateAt'] / 1000 + 1, pytz.timezone('Asia/Shanghai')
                ).strftime('%Y/%m/%d %H:%M:%S')
                try:
                    self.unit = events['unit']
                except:
                    pass
                break
        if self.id == 0:
            return False
        for cards in eventCards:
            if cards['eventId'] == self.id:
                self.cards.append(cards['cardId'])
        for bonuse in eventDeckBonuses:
            if bonuse['eventId'] == self.id:
                try:
                    self.bonuseattr = bonuse['cardAttr']
                    self.bonusechara.append(bonuse['gameCharacterUnitId'])
                except:
                    pass
        return True