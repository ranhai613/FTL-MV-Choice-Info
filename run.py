from mvlocscript.ftl import parse_ftlxml, ftl_xpath_matchers
from mvlocscript.xmltools import xpath, UniqueXPathGenerator
from mvlocscript.potools import readpo, writepo, StringEntry, parsekey
from mvlocscript.fstools import glob_posix
from json5 import load
import re
from pprint import pprint

class ElementBaseClass():
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        self._element = element
        self._xmlpath = xmlpath.replace('src-en/', '')
        self._uniqueXPathGenerator = uniqueXPathGenerator
    
    def get_uniqueXPath(self):
        return self._uniqueXPathGenerator.getpath(self._element)
        
#'removeCrew', 'autoReward', 'crewMember', 'reveal_map', 'modifyPursuit', 'item_modify', 'ship'
class Choice(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childEvents = []
        self._additional_info = None

    def _ensure_childEvents(self):
        new_events = []
        is_changeed = False
        for event in self._childEvents:
            load_event_name = event._element.attrib.get('load')
            if not load_event_name:
                new_events.append(event)
                continue
            
            load_event = global_event_map.get(load_event_name)
            if not load_event:
                new_events.append(event)
                continue
            
            if isinstance(load_event, Event):
                new_events.append(load_event)
            elif isinstance(load_event, EventList):
                new_events.extend(load_event._childEvents)
            is_changeed = True
        
        self._childEvents = new_events
        return is_changeed

    def init_childEventTags(self):
        self._childEvents = [Event(element, self._xmlpath, self._uniqueXPathGenerator) for element in xpath(self._element, './event')]
        while self._ensure_childEvents():
            pass
        for event in self._childEvents:
            event.init_childChoiceTags()
    
    def get_textTag_uniqueXPath(self):
        texttags = xpath(self._element, './text')
        if len(texttags) != 1:
            return None
        
        return self._uniqueXPathGenerator.getpath(texttags[0])
    
    def _event_analize(self, event):
        info = []
        for tag in event._element.iterchildren('removeCrew', 'crewMember', 'reveal_map', 'autoReward'):
            if tag.tag == 'removeCrew':
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
                race = tag.attrib.get('class', '?').replace('_', ' ').title()
                info.append(f'Gain a crew({race})')
                
            elif tag.tag == 'reveal_map':
                info.append('Map Reveal')
            
            elif tag.tag == 'autoReward':
                info.append('Reward')

        return info
                
    
    def _get_recursive_info(self):
        all_info = []
        for childEvent in self._childEvents:
            child_info = []
            if childEvent._childChoices is not None and len(childEvent._childChoices) > 0:
                child_info = [childChoice._get_recursive_info() for childChoice in childEvent._childChoices]
            
            all_info.append(', '.join(self._event_analize(childEvent)) + re.sub(r'[\n\\\'"]+', '', str(child_info)))
        return ' \nor '.join(all_info)
    
    def set_additional_info(self):
        self._additional_info = self._get_recursive_info()
    
    def get_formatted_additional_info(self):
        return self._additional_info
    
class Event(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childChoices = None
    
    
    def init_childChoiceTags(self):
        childChoiceElements = xpath(self._element, './choice')
        self._childChoices = [global_choice_map.get(f'{self._xmlpath}${self._uniqueXPathGenerator.getpath(element)}') for element in childChoiceElements]
    
class EventList(ElementBaseClass):
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        super().__init__(element, xmlpath, uniqueXPathGenerator)
        self._childEvents = [Event(element, xmlpath, uniqueXPathGenerator) for element in xpath(self._element, './event')]
    
    def init_childChoiceTags(self):
        return

global_event_map = {}
global_choice_map = {}

for xmlpath in glob_posix('src-en/data/*'):
    if not re.match(r'.+\.(xml|xml.append)$', xmlpath):
        continue
    tree = parse_ftlxml(xmlpath)
    root = tree.getroot()
    if root.tag != 'FTL':
        continue
    
    uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
    events = xpath(tree, '//event')
    global_event_map.update({element.attrib.get('name'): Event(element, xmlpath, uniqueXPathGenerator) for element in events})

    eventlists = xpath(tree, '//eventList')
    global_event_map.update({element.attrib.get('name'): EventList(element, xmlpath, uniqueXPathGenerator) for element in eventlists})


with open('mvloc.config.jsonc', 'tr', encoding='utf8') as f:
    config = load(f)

for xmlpath in config['filePatterns']:
    tree = parse_ftlxml('src-en/' + xmlpath)
    uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
    elements = xpath(tree, '//choice')

    global_choice_map.update({f'{xmlpath}${uniqueXPathGenerator.getpath(element)}': Choice(element, xmlpath, uniqueXPathGenerator) for element in elements})

for tag in global_choice_map.values():
    tag.init_childEventTags()
for tag in global_event_map.values():
    tag.init_childChoiceTags()
for tag in global_choice_map.values():
    tag.set_additional_info()
textTag_map = {f'{choice._xmlpath}${choice.get_textTag_uniqueXPath()}': choice for choice in global_choice_map.values()}

count = 0
for xmlpath in config['filePatterns']:
    dict_original, _, _ = readpo(f'locale/{xmlpath}/en.po')
    new_entries = []
    for key, entry in dict_original.items():
        value = entry.value
        target_choice = textTag_map.get(key)
        if target_choice is not None:
            value += '\n' + target_choice.get_formatted_additional_info()
            count += 1
        else:
            pass
        
        new_entries.append(StringEntry(key, value, entry.lineno, False, False))
    writepo(f'locale/{xmlpath}/choice-info-en.po', new_entries, f'src-en/{xmlpath}')
    print(f'replaced {count} texts in total!')
