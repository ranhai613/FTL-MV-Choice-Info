from mvlocscript.ftl import parse_ftlxml, ftl_xpath_matchers
from mvlocscript.xmltools import xpath, UniqueXPathGenerator
from mvlocscript.potools import readpo, writepo, StringEntry
from mvlocscript.fstools import glob_posix
from events import EventClasses, NameReturn
from json5 import load
import re
from functools import singledispatch
from treelib import Tree
from pprint import pprint

FIXED_EVENT_MAP = {
    'STORAGE_CHECK': 'Storage Check',
    'COMBAT_CHECK': 'Fight',
    'ATLAS_MENU': 'HyperSpeed Menu',
    'ATLAS_MENU_NOEQUIPMENT': 'HyperSpeed Menu',
}

class ElementBaseClass():
    def __init__(self, element=None, xmlpath='', uniqueXPathGenerator=None):
        self._element = element
        self._xmlpath = xmlpath.replace('src-en/', '')
        self._uniqueXPathGenerator = uniqueXPathGenerator
    
    def get_uniqueXPath(self):
        return self._uniqueXPathGenerator.getpath(self._element)
    

class EventAnalizer():
    '''A component of Choice class, containing child events of Choice and analizing them.
    '''
    def __init__(self, childEvents) -> None:
        self._childEvents = childEvents
        self.is_ensured = False
    
    @property
    def childEvents(self):
        assert self.is_ensured
        return self._childEvents
    
    def ensureChildEvents(self, ship=None):
        while True:
            new_events = []
            is_changed = False
            for event in self._childEvents:
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
                
                if load_event_name == 'COMBAT_CHECK' and ship is not None:
                    fightEvent = FightEvent(ship)
                    new_events.append(fightEvent)
                    continue
                
                load_event = global_event_map.get(load_event_name)
                if not load_event:
                    new_events.append(event)
                    continue
                
                if isinstance(load_event, Event):
                    new_events.append(load_event)
                elif isinstance(load_event, EventList):
                    new_events.extend(load_event.childEvents)
                elif isinstance(load_event, FixedEvent):
                    new_events.append(load_event)
                    continue
                is_changed = True
            
            self._childEvents = new_events
            if not is_changed:
                for event in self._childEvents:
                    event.init_childChoiceTags()
                self.is_ensured = True
                return
    
    def getInfoList(self):
        assert self.is_ensured
        
        class EventNodeElement():
            def __init__(self, event, prob) -> None:
                self._event = event
                self._prob = prob

        class EventNode():
            def __init__(self, events, prob) -> None:
                self._events = [EventNodeElement(event, ((1 / len(events)) * prob)) for event in events]
                self._prob = prob

        
        def growTree(parent_node, parent_eventNode: EventNode):
            for eventNodeElement in parent_eventNode._events:
                if eventNodeElement._event._childChoices is None:
                    continue
                for i, choice in enumerate(eventNodeElement._event._childChoices):
                    new_eventNode = EventNode(choice.childEvents, eventNodeElement._prob)
                    new_node = tree.create_node(parent=parent_node, data=new_eventNode)
                    if isinstance(eventNodeElement._event, FightEvent):
                        if i == 0:
                            eventNodeElement._event._hullKillNode = new_node
                        elif i == 1:
                            eventNodeElement._event._crewKillNode = new_node
                        elif i == 2:
                            eventNodeElement._event._surrenderNode = new_node
                        else:
                            raise IndexError
                    growTree(new_node, new_eventNode)
                
        @singledispatch
        def eventAnalize(event, tree):
            raise TypeError
        
        @eventAnalize.register
        def _(event: FixedEvent, tree):
            return [NameReturn(event.eventText)], None
        
        @eventAnalize.register
        def _(event: FightEvent, tree):
            hkInfo = None
            ckInfo = None
            srInfo = None
            if event._hullKillNode is not None and event.is_HKexist:
                hkInfo = treeAnalize(tree.subtree(event._hullKillNode.identifier))
            if event._crewKillNode is not None and event.is_CKexist:
                ckInfo = treeAnalize(tree.subtree(event._crewKillNode.identifier))
            if event._surrenderNode is not None and event.is_SRexist:
                ckInfo = treeAnalize(tree.subtree(event._surrenderNode.identifier))
            
            return None, {'HK': hkInfo, 'CK': ckInfo, 'SR': srInfo}
        
        @eventAnalize.register
        def _(event: Event, tree):
            eventlist = []
            for element in event._element.iterchildren():
                try:
                    eventclass = EventClasses[element.tag].value(element)
                except KeyError:
                    continue
                eventlist.append(eventclass)
            return eventlist, None

        def treeAnalize(tree, tune=0):
            for  i in range(10):
                nece_info = []
                for node in tree.all_nodes_itr():
                    info = []
                    for eventNodeElement in node.data._events:
                        if eventNodeElement._event is None:
                            continue
                        info.append(eventAnalize(eventNodeElement._event, tree) + (eventNodeElement._prob,))
                    depth = tree.depth(node) + tune + (i * -1)
                    for eventlist, fightDict, prob in info:
                        if eventlist is not None:
                            for eventclass in eventlist:
                                if eventclass._priority > depth:
                                    textInfo = eventclass.getInfo()
                                    if textInfo:
                                        nece_info.append(f'{prob:.0%} {textInfo}' if prob < 1 else textInfo)
                        
                        if fightDict is not None:
                            fightDict = {key: ' '.join(value) for key, value in fightDict.items() if value is not None}
                            length = len(fightDict)
                            if length == 3:
                                if fightDict['HK'] == fightDict['CK'] and fightDict['CK'] == fightDict['SR']:
                                    nece_info.append(f'Fight(CK=HK=SR: {fightDict["HK"]})')
                                elif fightDict['HK'] == fightDict['CK']:
                                    nece_info.append(f'Fight(CK=HK: {fightDict["HK"]})(SR: {fightDict["SR"]})')
                                elif fightDict['HK'] == fightDict['SR']:
                                    nece_info.append(f'Fight(CK: {fightDict["CK"]})(HK=SR: {fightDict["HK"]})')
                                elif fightDict['CK'] == fightDict['SR']:
                                    nece_info.append(f'Fight(CK=SR: {fightDict["CK"]})(HK: {fightDict["HK"]})')
                                else:
                                    nece_info.append(f'Fight(CK: {fightDict["CK"]})(HK: {fightDict["HK"]})(SR: {fightDict["SR"]})')
                            elif length == 2:
                                keyList = list(fightDict.keys())
                                infoList = list(fightDict.values())
                                if infoList[0] == infoList[1]:
                                    nece_info.append(f'Fight({keyList[0]}={keyList[1]}: {infoList[0]})')
                                else:
                                    nece_info.append(f'Fight({keyList[0]}: {infoList[0]})({keyList[1]}: {infoList[1]})')
                            elif length == 1:
                                for key, value in fightDict.items():
                                    nece_info.append(f'Fight({key}: {value})')
                
                if len(nece_info) > 0:
                    return nece_info
            else:
                return []
                    
        tree = Tree()
        rootEventNode = EventNode(self._childEvents, 1)
        root = tree.create_node(data=rootEventNode)
        growTree(root, rootEventNode)
        
        return treeAnalize(tree)


#-------------------XML Tag Wrapper Classes-------------------

class Choice(ElementBaseClass):
    def __init__(self, element=None, xmlpath='', uniqueXPathGenerator=None):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._ship = None
        self._evetnAnalizer = None
        self._additional_info = None
    
    @property
    def childEvents(self):
        return self._evetnAnalizer.childEvents

    @childEvents.setter
    def childEvents(self, value):
        self._evetnAnalizer = EventAnalizer(value)
        self._evetnAnalizer.ensureChildEvents(self._ship)

    def init_childEventTags(self):
        self._evetnAnalizer = EventAnalizer([Event(element, self._xmlpath, self._uniqueXPathGenerator) for element in xpath(self._element, './event')])
        self._evetnAnalizer.ensureChildEvents(self._ship)
    
    def init_shipTag(self):
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
        
    def set_additional_info(self):
        self._additional_info = '\n'.join(self._evetnAnalizer.getInfoList())
    
    def get_formatted_additional_info(self):
        return self._additional_info
    
class Event(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childChoices = None
    
    def init_childChoiceTags(self):
        self._childChoices = [global_choice_map.get(f'{self._xmlpath}${self._uniqueXPathGenerator.getpath(element)}') for element in xpath(self._element, './choice')]
        
class EventList():
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        self.childEvents = [Event(eventElement, xmlpath, uniqueXPathGenerator) for eventElement in xpath(element, './event')]
    
    def init_childChoiceTags(self):
        return
    
class FixedEvent():
    def __init__(self, eventText):
        self.eventText = eventText
        self._childChoices = None
    
    def init_childChoiceTags(self):
        return
        
class Ship(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        
class FightEvent():
    def __init__(self, ship: Ship):
        self._ship = ship
        self._hullKillChoice = Choice()
        self._hullKillChoice.childEvents = [Event(element, ship._xmlpath, ship._uniqueXPathGenerator) for element in xpath(ship._element, './destroyed')]
        self._crewKillChoice = Choice()
        self._crewKillChoice.childEvents = [Event(element, ship._xmlpath, ship._uniqueXPathGenerator) for element in xpath(ship._element, './deadCrew')]
        self._surrenderChoice = Choice()
        self._surrenderChoice.childEvents = [Event(element, ship._xmlpath, ship._uniqueXPathGenerator) for element in xpath(ship._element, './surrender')]
        self._childChoices = [self._hullKillChoice, self._crewKillChoice, self._surrenderChoice]
        self._hullKillNode = None
        self._crewKillNode = None
        self._surrenderNode = None
        self.is_HKexist = True if len(xpath(ship._element, './destroyed')) > 0 else False
        self.is_CKexist = True if len(xpath(ship._element, './deadCrew')) > 0 else False
        self.is_SRexist = True if len(xpath(ship._element, './surrender')) > 0 else False

    def init_childChoiceTags(self):
        return
            
#------------------------main------------------------

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
        tag.init_shipTag()
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