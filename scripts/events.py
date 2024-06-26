from mvlocscript.xmltools import xpath
from enum import Enum

CUSTOM_FONT = {
    'fuel': '{',
    'droneparts': '|',
    'drones': '|',
    'missiles': '}',
    'scrap': '~',
    'repair': '$',
    'elite': '€',
    'fire': '‰',
    'power': '†',
    'cooldown': '‡',
    'upgraded': '™'
}

class EventBaseClass():
    def __init__(self, element, priority) -> None:
        self._element = element
        self._priority = priority
        self._infoText = None
    
    def setInfo(self):
        self._infoText = None
    
    def getInfo(self):
        self.setInfo()
        return self._infoText

def ajustText(text, use_custom_font = True):
    if text is None:
        return None
    
    if use_custom_font:
        text = text.lower()
        for key, custom_font in CUSTOM_FONT.items():
            text = text.replace(key, custom_font)
    return text.replace('_', ' ').title()


#----------------Evnets--------------------------


class UnlockCustomShip(EventBaseClass):
    def __init__(self, element, priority=3) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        text = ajustText(self._element.text.replace('PLAYER_SHIP_', ''), False)
        self._infoText = f'<#>Unlock Ship({text})'

class RemoveCrew(EventBaseClass):
    def __init__(self, element, priority=2) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        clonetags = xpath(self._element, './clone')
        if len(clonetags) != 1:
            self._infoText = '<!>Lose your crew(?)'
            return
        if clonetags[0].text == 'true':
            self._infoText = '<!>Lose your crew(clonable)'
        elif clonetags[0].text == 'false':
            self._infoText = '<!>Lose your crew(UNCLONABLE)'
        else:
            self._infoText = '<!>Lose your crew(?)'

class CrewMember(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        race = ajustText(self._element.get('class', '?').replace('LIST_CREW_', ''), False)
        self._infoText = f'Gain a crew({race})'

class RevealMap(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        self._infoText = 'Map Reveal'

class AutoReward(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        level = self._element.get('level', '?')[0]
        stuff_type = ajustText(self._element.text)
        self._infoText = f'Reward {stuff_type}({level})'

class ItemModify(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        itemtags = xpath(self._element, './item')
        if len(itemtags) == 0:
            return
        
        itemlist = []
        for itemtag in itemtags:
            item = ajustText(itemtag.get('type'))
            amount_min = itemtag.get('min')
            amount_max = itemtag.get('max')
            try:
                amount_min = int(amount_min)
                amount_max = int(amount_max)
            except TypeError:
                continue
            
            if amount_min == amount_max:
                itemlist.append(f'{item}{amount_min}')
            else:
                itemlist.append(f'{amount_min}≤{item}≤{amount_max}')
        self._infoText = ' '.join(itemlist)

class ModifyPursuit(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        amount = self._element.get('amount')
        if amount is None:
            return
        try:
            amount = int(amount)
        except TypeError:
            return
        
        if amount < 0:
            self._infoText = f'Fleet Delay({str(amount * -1)})'
        elif amount > 0:
            self._infoText = f'<!>Fleet Advance({str(amount)})'

class Reward(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        name = ajustText(self._element.get('name', '?'), False)
        if self._element.tag[0] in ('a', 'e', 'i', 'o', 'u'):
            self._infoText = f'Gain an {self._element.tag}({name})'
        else:
            self._infoText = f'Gain a {self._element.tag}({name})'

class Damage(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        amount = self._element.get('damage')
        if amount is None:
            return
        try:
            amount = int(amount)
        except TypeError:
            return
        
        if amount < 0:
            self._infoText = f'Repair Hull({str(amount * -1)}$)'
        elif amount > 0:
            self._infoText = f'<!>Damage Hull({str(amount)})'

class Upgrade(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        system = ajustText(self._element.get('system'))
        amount = self._element.get('amount')
        if system is None or amount is None:
            return
        
        self._infoText = f'System Upgrade({system} {amount}™)'

class Boarders(EventBaseClass):
    def __init__(self, element, priority=1) -> None:
        super().__init__(element, priority)
    
    def setInfo(self):
        race = ajustText(self._element.get('class', '?').replace('LIST_CREW_', ''), False)
        amount_min = self._element.get('min')
        amount_max = self._element.get('max')
        try:
            amount_min = int(amount_min)
            amount_max = int(amount_max)
        except TypeError:
            self._infoText = f'<!>Enemy Boarding({race})'
            return
        
        if amount_min == amount_max:
            self._infoText = f'<!>Enemy Boarding(x{str(amount_min)} {race})'
        else:
            self._infoText = f'<!>Enemy Boarding(x{str(amount_min)}-x{str(amount_max)} {race})'


#not done(or not planned to inplement): 'environment', 'recallBoarders', 'achievement', 'choiceRequiresCrew', 'instantEscape'
class EventClasses(Enum):
    unlockCustomShip = UnlockCustomShip
    removeCrew = RemoveCrew
    crewMember = CrewMember
    reveal_map = RevealMap
    autoReward = AutoReward
    item_modify = ItemModify
    modifyPursuit = ModifyPursuit
    weapon = Reward
    drone = Reward
    augment = Reward
    damage = Damage
    upgrade = Upgrade
    boarders = Boarders
