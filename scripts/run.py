from mvlocscript.ftl import parse_ftlxml, ftl_xpath_matchers
from mvlocscript.xmltools import xpath, UniqueXPathGenerator
from mvlocscript.potools import readpo, writepo, StringEntry
from mvlocscript.fstools import glob_posix
from events import EVENTCLASSMAP, NameReturn
from loadevent import sanitize_loadEvent
from json5 import load
import re
from functools import singledispatch
from collections import defaultdict
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
    

class EventAnalyzer():
    '''A component of Choice class, containing child events of Choice and analyzing them.
    '''
    def __init__(self, childEvents) -> None:
        self._childEvents = childEvents
        self.is_ensured = False
    
    @property
    def childEvents(self):
        assert self.is_ensured
        return self._childEvents
    
    def ensureChildEvents(self, ship=None):
        '''Loop until following processes done.
        1. If an event has load attribute, find the loaded event and add it to child events list.
        2. If an event is <EventList>, add events in it to child evnets list.
        3. If loaded event name is 'COMBAT_CHECK' and ship is given, add fight event to child evetns list.
        '''
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
                        loadEventName = loadEventTags[0].text
                        if loadEventName:
                            loadEvent_stat.add(loadEventName)
                            # loadEvent = global_event_map.get(loadEventName)
                            # if loadEvent is not None:
                            #     new_events.append(loadEvent)
                            #     is_changed = True
                    else:
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
        '''find the target info by making an event tree data structure and analyzing it. Beforehand, The child evnets must be ensured.'''
        assert self.is_ensured
        
        class EventNodeElement():
            def __init__(self, event, prob, increment) -> None:
                self._event = event
                self._prob = prob
                self._increment = increment

        class EventNode():
            def __init__(self, events, prob, increment) -> None:
                self._events = [EventNodeElement(event, ((1 / len(events)) * prob), increment) for event in events]
                self._prob = prob
                self._increment = increment
        
        def growTree(parent_node, parent_eventNode: EventNode):
            '''first given a root, this find child events and wrap them into EventNode, and link it to the parent. This does the process recursively unitl the whole tree is completed.'''
            for eventNodeElement in parent_eventNode._events:
                if eventNodeElement._event._childChoices is None:
                    continue
                length = len(eventNodeElement._event._childChoices)
                for i, choice in enumerate(eventNodeElement._event._childChoices):
                    new_eventNode = EventNode(choice.childEvents, eventNodeElement._prob, (eventNodeElement._increment + 1) if length == 1 else 0)
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
        def eventAnalyze(event, tree):
            raise TypeError
        
        @eventAnalyze.register
        def _(event: FixedEvent, tree):
            global PackageConfig
            if PackageConfig.get('ignoreFixedEvent'):
                return None, None
            return [NameReturn(event.eventText)], None
        
        @eventAnalyze.register
        def _(event: FightEvent, tree):
            hkInfo = None
            ckInfo = None
            srInfo = None
            if event._hullKillNode is not None and event.is_HKexist:
                hkInfo = treeAnalyze(tree.subtree(event._hullKillNode.identifier))
            if event._crewKillNode is not None and event.is_CKexist:
                ckInfo = treeAnalyze(tree.subtree(event._crewKillNode.identifier))
            if event._surrenderNode is not None and event.is_SRexist:
                ckInfo = treeAnalyze(tree.subtree(event._surrenderNode.identifier))
            
            return None, {'HK': hkInfo, 'CK': ckInfo, 'SR': srInfo}
        
        @eventAnalyze.register
        def _(event: Event, tree):
            global PackageConfig
            eventlist = []
            eventTypes = PackageConfig.get('events', EVENTCLASSMAP.keys())
            for element in event._element.iterchildren(*eventTypes):
                try:
                    eventclass = EVENTCLASSMAP[element.tag](element)
                except KeyError:
                    continue
                eventlist.append(eventclass)
            return eventlist, None

        def treeAnalyze(tree, tune=0):
            '''iterate all nodes in a given tree, picking up necessary info. an info is picked up when following formula is true.
            
            - eventclass._priority + increment > tree.depth(node) + tune + (i * -1)
            
            params:
            - eventclass._priority: param for each event. Important event should be bigger on this param. You can edit it in events.py
            - increment: default to 0. If a parent node has only one child, the child node's increment += 1. If a parent node has multiple children, the value reset to 0.
            - tree.depth(node): how deep the node locates from the root.
            - tune: default to 0. You can change the base value by editing this. For now it isn't used.
            - (i * -1): default to range(10). If treeAnalyze cannot find any info, increment i and retry. You can change max retry value by PackageConfig['maxDeeperRetry'].
            '''
            global PackageConfig
            for i in range(PackageConfig.get('maxDeeperRetry') or 10):
                nece_info = []
                for node in tree.all_nodes_itr():
                    info = []
                    for eventNodeElement in node.data._events:
                        if eventNodeElement._event is None:
                            continue
                        info.append(eventAnalyze(eventNodeElement._event, tree) + (eventNodeElement._prob, eventNodeElement._increment))
                    depth = tree.depth(node) + tune + (i * -1)
                    for eventlist, fightDict, prob, increment in info:
                        if eventlist is not None:
                            #diagram is used for unifying the same info and summing the prob.
                            diagram = defaultdict(float)
                            for eventclass in eventlist:
                                if eventclass._priority + increment > depth:
                                    textInfo = eventclass.getInfo()
                                    if textInfo:
                                        diagram[textInfo] += prob
                            nece_info.extend([f'{prob:.0%} {textInfo}' if prob < 1 else textInfo for textInfo, prob in diagram.items()])
                        
                        if fightDict is not None:
                            fightDict = {key: ' '.join(value) for key, value in fightDict.items() if value}
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
                    #remove duplicated info before return list. I don't like to use set() to remove them because it doesn't care the order, that makes hard to see diff under dev.
                    return list(dict.fromkeys(nece_info))
            else:
                return []
                    
        tree = Tree()
        rootEventNode = EventNode(self._childEvents, 1, 0)
        root = tree.create_node(data=rootEventNode)
        growTree(root, rootEventNode)
        
        return treeAnalyze(tree)


#-------------------XML Tag Wrapper Classes-------------------

class Choice(ElementBaseClass):
    def __init__(self, element=None, xmlpath='', uniqueXPathGenerator=None):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._ship = None
        self._evetnAnalyzer = None
        self._additional_info = None
    
    @property
    def childEvents(self):
        return self._evetnAnalyzer.childEvents

    @childEvents.setter
    def childEvents(self, value):
        self._evetnAnalyzer = EventAnalyzer(value)
        self._evetnAnalyzer.ensureChildEvents(self._ship)

    def init_childEventTags(self):
        self._evetnAnalyzer = EventAnalyzer([Event(element, self._xmlpath, self._uniqueXPathGenerator) for element in xpath(self._element, './event')])
        self._evetnAnalyzer.ensureChildEvents(self._ship)
    
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
        self._additional_info = '\n'.join(self._evetnAnalyzer.getInfoList())
    
    def get_formatted_additional_info(self):
        return self._additional_info
    
class Event(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childChoices = None
    
    def init_childChoiceTags(self):
        self._childChoices = [global_choice_map.get(f'{self._xmlpath}${self._uniqueXPathGenerator.getpath(element)}') for element in xpath(self._element, './choice')]
        
class EventList(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
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

PackageConfig = None

with open('mvloc.config.jsonc', 'tr', encoding='utf8') as f:
    config = load(f)

def main(stat=False, packageConfig: dict={}):
    '''analyze events in xml and write info to .po files in locale/. po file is used for MV translation, and you need one more step to generate xml from po files.
    
    stat: if true, the script does not generate po files. Instead it returns stat of events that are invoked by <loadEvent>, that the script cannot handle with by default. The stat is used for additional process to sanitize <loadEvent>
    '''
    global PackageConfig
    PackageConfig = packageConfig
    for xmlpath in glob_posix('src-en/data/*'):
        #find xml
        if not re.match(r'.+\.(xml|xml.append)$', xmlpath):
            continue
        
        if xmlpath.replace('src-en/', '') in config['filePatterns']:
            tree = parse_ftlxml(xmlpath)
        else:
            tree = parse_ftlxml(xmlpath, True)
        
        #UniqueXPathGenerator can generate unique xpath of an element within the xml. I use the unique xpath as an id.
        uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
        global_event_map.update({element.get('name'): Event(sanitize_loadEvent(element), xmlpath, uniqueXPathGenerator) for element in xpath(tree, '//event')})
        global_event_map.update({element.get('name'): EventList(sanitize_loadEvent(element), xmlpath, uniqueXPathGenerator) for element in xpath(tree, '//eventList')})
        global_ship_map.update({element.get('name'): Ship(element, xmlpath, uniqueXPathGenerator) for element in xpath(tree, '//ship')})

    if not stat:
        global_event_map.update({name: FixedEvent(value) for name, value in FIXED_EVENT_MAP.items()})

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
    
    if not stat:
        textTag_map = {f'{choice._xmlpath}${choice.get_textTag_uniqueXPath()}': choice for choice in global_choice_map.values()}

        for xmlpath in config['filePatterns']:
            #dict_original = {id(the form of {xml path}${unique xpath}): StrignEntry('id', 'value', 'lineno', 'fuzzy', 'obsolete')} taken from MV translation.
            dict_original, _, _ = readpo(f'locale/{xmlpath}/en.po')
            new_entries = []
            for key, entry in dict_original.items():
                value = entry.value
                target_choice = textTag_map.get(key)
                if target_choice is not None:
                    additional_info = target_choice.get_formatted_additional_info()
                    if additional_info:
                        value += '\n' + target_choice.get_formatted_additional_info()
                else:
                    pass
                
                new_entries.append(StringEntry(key, value, entry.lineno, False, False))
            writepo(f'locale/{xmlpath}/choice-info-en.po', new_entries, f'src-en/{xmlpath}')
    else:
        return {name: global_event_map[name] for name in loadEvent_stat}

if __name__ == '__main__':
    main()