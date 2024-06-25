from mvlocscript.ftl import parse_ftlxml, ftl_xpath_matchers
from mvlocscript.xmltools import xpath, UniqueXPathGenerator
from mvlocscript.potools import readpo, writepo, StringEntry
from mvlocscript.fstools import glob_posix
from json5 import load
import re
from pprint import pprint

FIXED_EVENT_MAP = {
    'STORAGE_CHECK': 'Storage Check',
    'COMBAT_CHECK': 'Fight',
    'ATLAS_MENU': 'HyperSpeed Menu',
    'ATLAS_MENU_NOEQUIPMENT': 'HyperSpeed Menu',
}

CUSTOM_FONT = {
    'fuel': '{',
    'drones': '|',
    'droneparts': '|',
    'missiles': '}',
    'scrap': '~',
    'repair': '$',
    'elite': '€',
    'fire': '‰',
    'power': '†',
    'cooldown': '‡',
    'upgraded': '™'
}

class ElementBaseClass():
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        self._element = element
        self._xmlpath = xmlpath.replace('src-en/', '')
        self._uniqueXPathGenerator = uniqueXPathGenerator
        self._childEvents = None
    
    def get_uniqueXPath(self):
        return self._uniqueXPathGenerator.getpath(self._element)
    
    def _ensure_childEvents(self, childEvents):
        while True:
            new_events = []
            is_changed = False
            for event in childEvents:
                if isinstance(event, (FixedEvent, FightEvent)):
                    new_events.append(event)
                    continue
                
                load_event_name = event._element.get('load')
                if not load_event_name:
                    loadEventTags = xpath(event._element, './loadEvent')
                    if len(loadEventTags) == 1:
                        loadEvent = loadEventTags[0].text
                        if loadEvent:
                            loadEvent_stat.add(loadEvent)
                    
                    new_events.append(event)
                    continue
                
                if load_event_name == 'COMBAT_CHECK' and self._ship is not None:
                    fightEvent = FightEvent(self._ship)
                    fightEvent.init_childEventTags()
                    new_events.append(fightEvent)
                    is_changed = True
                    continue
                
                load_event = global_event_map.get(load_event_name)
                if not load_event:
                    new_events.append(event)
                    continue
                
                if isinstance(load_event, Event):
                    new_events.append(load_event)
                elif isinstance(load_event, EventList):
                    new_events.extend(load_event._childEvents)
                elif isinstance(load_event, FixedEvent):
                    new_events.append(load_event)
                    continue
                is_changed = True
            
            childEvents = new_events
            if not is_changed:
                return childEvents
    
    def init_childChoiceTags(self):
        return
    
#not done(or not planned to inplement): 'environment', 'recallBoarders', 'achievement', 'choiceRequiresCrew', 'instantEscape', '', ''
class Choice(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childEvents = []
        self._ship = None
        self._additional_info = None


    def init_childEventTags(self):
        self._childEvents = [Event(element, self._xmlpath, self._uniqueXPathGenerator) for element in xpath(self._element, './event')]
        self._childEvents = self._ensure_childEvents(self._childEvents)
        for event in self._childEvents:
            event.init_childChoiceTags()
    
    def init_ShipTag(self):
        for parent in self._element.iterancestors():
            ships = [ship.get('load') for ship in xpath(parent, './ship') if ship.get('load')]
            if len(ships) > 0:
                break
        else:
            return None
        if len(ships) > 1:
            return None
        
        self._ship = global_ship_map.get(ships[0])
        
    
    def get_textTag_uniqueXPath(self):
        texttags = xpath(self._element, './text')
        if len(texttags) != 1:
            return None
        
        return self._uniqueXPathGenerator.getpath(texttags[0])
    
    def _event_analize(self, event):
        info = []
        for tag in event._element.iterchildren():
            if tag.tag == 'unlockCustomShip':
                text = ajustText(tag.text.replace('PLAYER_SHIP_', ''), False)
                info.append(f'<#>Unlock Ship({text})')
            
            elif tag.tag == 'removeCrew':
                clonetag = xpath(tag, './clone')
                if len(clonetag) != 1:
                    info.append('<!>Lose your crew(?)')
                    continue
                if clonetag[0].text == 'true':
                    info.append('<!>Lose your crew(clonable)')
                elif clonetag[0].text == 'false':
                    info.append('<!>Lose your crew(UNCLONABLE)')
                else:
                    info.append('<!>Lose your crew(?)')
            
            elif tag.tag == 'crewMember':
                race = ajustText(tag.get('class', '?').replace('LIST_CREW_', ''), False)
                info.append(f'Gain a crew({race})')
                
            elif tag.tag == 'reveal_map':
                info.append('Map Reveal')
            
            elif tag.tag == 'autoReward':
                level = tag.get('level', '?')[0]
                stuff_type = ajustText(tag.text)
                info.append(f'Reward {stuff_type}({level})')
            
            elif tag.tag == 'item_modify':
                itemtags = xpath(tag, './item')
                if len(itemtags) == 0:
                    continue
                
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
                info.append(' '.join(itemlist))
            
            elif tag.tag == 'modifyPursuit':
                amount = tag.get('amount')
                if amount is None:
                    continue
                amount = int(amount)
                
                if amount < 0:
                    info.append(f'Fleet Delay({str(amount * -1)})')
                elif amount > 0:
                    info.append(f'<!>Fleet Advance({str(amount)})')
            
            elif tag.tag == 'weapon' or tag.tag == 'drone':
                name = ajustText(tag.get('name', '?'), False)
                info.append(f'Gain a {tag.tag}({name})')
            
            elif tag.tag == 'augment':
                name = ajustText(tag.get('name', '?'), False)
                info.append(f'Gain an augment({name})')
            
            elif tag.tag == 'damage':
                amount = tag.get('damage')
                if amount is None:
                    continue
                amount = int(amount)
                
                if amount < 0:
                    info.append(f'Repair Hull({str(amount * -1)}$)')
                elif amount > 0:
                    info.append(f'<!>Damage Hull({str(amount)})')
            
            elif tag.tag == 'upgrade':
                system = ajustText(tag.get('system'))
                amount = tag.get('amount')
                if system is None or amount is None:
                    continue
                
                info.append(f'System Upgrade({system} {amount}™)')
            
            elif tag.tag == 'boarders':
                race = ajustText(tag.get('class', '?').replace('LIST_CREW_', ''), False)
                amount_min = tag.get('min')
                amount_max = tag.get('max')
                try:
                    amount_min = int(amount_min)
                    amount_max = int(amount_max)
                except TypeError:
                    info.append(f'<!>Enemy Boarding({race})')
                    continue
                
                if amount_min == amount_max:
                    info.append(f'<!>Enemy Boarding(x{str(amount_min)} {race})')
                else:
                    info.append(f'<!>Enemy Boarding(x{str(amount_min)}-x{str(amount_max)} {race})')

        return info
                
    
    def _get_recursive_info(self):
        all_info = []
        for childEvent in self._childEvents:
            if isinstance(childEvent, Event):
                child_info = []
                if childEvent._childChoices is not None and len(childEvent._childChoices) > 0:
                    child_info = [childChoice._get_recursive_info() for childChoice in childEvent._childChoices]
                
                all_info.append('\n'.join(self._event_analize(childEvent)) + re.sub(r'[\\\'"]+', '', str(child_info).replace('\\n', '')))
            elif isinstance(childEvent, FightEvent):
                HK_child_info = []
                try:
                    if len(childEvent._hullKillEvents[0]._childChoices) > 0:
                        HK_child_info = [childEvent._hullKillChoice._get_recursive_info()]
                    HK_format = re.sub(r'[\\\'"]+', '', str(HK_child_info).replace('\\n', ''))
                except Exception:
                    HK_format = ''
                CK_child_info = []
                try:
                    if len(childEvent._crewKillEvents[0]._childChoices) > 0:
                        CK_child_info = [childEvent._crewKillChoice._get_recursive_info()]
                    CK_format = re.sub(r'[\\\'"]+', '', str(CK_child_info).replace('\\n', ''))
                except Exception:
                    CK_format = ''
                if HK_format == CK_format:
                    all_info.append(f'Fight(CK=HK: {CK_format})')
                else:
                    all_info.append(f'Fight(CK: {CK_format})(HK: {HK_format})')
            elif isinstance(childEvent, FixedEvent):
                all_info.append(childEvent._event)
        return ' \nor '.join(all_info)
    
    def set_additional_info(self):
        self._additional_info = self._get_recursive_info()
    
    def get_formatted_additional_info(self):
        return self._additional_info
    
class Event(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childChoices = None
        self._childShips = None
    
    def init_childChoiceTags(self):
        self._childChoices = [global_choice_map.get(f'{self._xmlpath}${self._uniqueXPathGenerator.getpath(element)}') for element in xpath(self._element, './choice')]
    
    def init_childShipTags(self):
        self._childShips = [global_ship_map.get(element.get('name')) for element in xpath(self._element, './ship')]
    
class EventList(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childEvents = [Event(element, xmlpath, uniqueXPathGenerator) for element in xpath(self._element, './event')]
    
class FixedEvent(ElementBaseClass):
    def __init__(self, eventText, element=None, xmlpath='', uniqueXPathGenerator=None):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._event = eventText
        self._childChoices = None
        
class Ship(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        
class FightEvent(ElementBaseClass):
    def __init__(self, ship: Ship, element=None, xmlpath='', uniqueXPathGenerator=None):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._ship = ship
        self._hullKillEvents = [Event(element, ship._xmlpath, ship._uniqueXPathGenerator) for element in xpath(ship._element, './destroyed')]
        self._crewKillEvents = [Event(element, ship._xmlpath, ship._uniqueXPathGenerator) for element in xpath(ship._element, './deadCrew')]
        self._hullKillChoice = Choice(element, xmlpath, uniqueXPathGenerator)
        self._crewKillChoice = Choice(element, xmlpath, uniqueXPathGenerator)
        
    def init_childEventTags(self):
        self._hullKillEvents = self._ensure_childEvents(self._hullKillEvents)
        self._crewKillEvents = self._ensure_childEvents(self._crewKillEvents)
        for event in self._hullKillEvents:
            event.init_childChoiceTags()
        for event in self._crewKillEvents:
            event.init_childChoiceTags()
        
        self._hullKillChoice._childEvents = self._hullKillEvents
        self._crewKillChoice._childEvents = self._crewKillEvents
        

def ajustText(text, use_custom_font = True):
    if text is None:
        return None
    
    if use_custom_font:
        text = text.lower()
        for key, custom_font in CUSTOM_FONT.items():
            text = text.replace(key, custom_font)
    return text.replace('_', ' ').title()

loadEvent_stat = set()

global_event_map = {}
global_choice_map = {}
global_ship_map = {}

def main():
    for xmlpath in glob_posix('src-en/data/*'):
        if not re.match(r'.+\.(xml|xml.append)$', xmlpath):
            continue
        tree = parse_ftlxml(xmlpath)
        root = tree.getroot()
        if root.tag != 'FTL':
            tree = parse_ftlxml(xmlpath, True)
        
        uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
        global_event_map.update({element.get('name'): Event(element, xmlpath, uniqueXPathGenerator) for element in xpath(tree, '//event')})
        global_event_map.update({element.get('name'): EventList(element, xmlpath, uniqueXPathGenerator) for element in xpath(tree, '//eventList')})
        global_ship_map.update({element.get('name'): Ship(element, xmlpath, uniqueXPathGenerator) for element in xpath(tree, '//ship')})

    global_event_map.update({name: FixedEvent(value) for name, value in FIXED_EVENT_MAP.items()})

    with open('mvloc.config.jsonc', 'tr', encoding='utf8') as f:
        config = load(f)

    for xmlpath in config['filePatterns']:
        tree = parse_ftlxml('src-en/' + xmlpath)
        uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
        elements = xpath(tree, '//choice')

        global_choice_map.update({f'{xmlpath}${uniqueXPathGenerator.getpath(element)}': Choice(element, xmlpath, uniqueXPathGenerator) for element in elements})

    print('initializing choices...')
    for tag in global_choice_map.values():
        tag.init_ShipTag()
        tag.init_childEventTags()
    print('initializing events...')
    for tag in global_event_map.values():
        tag.init_childChoiceTags()
    print('setting additional info...')
    for tag in global_choice_map.values():
        tag.set_additional_info()

    textTag_map = {f'{choice._xmlpath}${choice.get_textTag_uniqueXPath()}': choice for choice in global_choice_map.values()}

    for xmlpath in config['filePatterns']:
        dict_original, _, _ = readpo(f'locale/{xmlpath}/en.po')
        new_entries = []
        for key, entry in dict_original.items():
            value = entry.value
            target_choice = textTag_map.get(key)
            if target_choice is not None:
                value += '\n' + target_choice.get_formatted_additional_info()
            else:
                pass
            
            new_entries.append(StringEntry(key, value, entry.lineno, False, False))
        writepo(f'locale/{xmlpath}/choice-info-en.po', new_entries, f'src-en/{xmlpath}')
    #print(len(loadEvent_stat))

if __name__ == '__main__':
    main()