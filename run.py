from mvlocscript.ftl import parse_ftlxml, ftl_xpath_matchers
from mvlocscript.xmltools import xpath, UniqueXPathGenerator
from mvlocscript.potools import readpo, writepo, StringEntry, parsekey
from mvlocscript.fstools import glob_posix
from json5 import load
import re
from pprint import pprint

#'removeCrew', 'autoReward', 'crewMember', 'reveal_map', 'modifyPursuit', 'item_modify', 'ship'
class Choice():
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        self._element = element
        self._xmlpath = xmlpath
        self._uniqueXPathGenerator = uniqueXPathGenerator
        self._childEventTag = None
        self._additional_info = None
        

    def init_childEventTag(self):
        childEventTags = xpath(self._element, './event')
        if len(childEventTags) == 1:
            self._childEventTag = Event(childEventTags[0], self._xmlpath, self._uniqueXPathGenerator)

    def get_uniqueXPath(self):
        return self._uniqueXPathGenerator.getpath(self._element)
    
    def get_textTag_uniqueXPath(self):
        texttags = xpath(self._element, './text')
        if len(texttags) != 1:
            return None
        
        return self._uniqueXPathGenerator.getpath(texttags[0])
    
    def _event_analize(self):
        if self._childEventTag is None:
            return None
        
        event = self._childEventTag._element
        load_event_name = event.attrib.get('load', None)
        if load_event_name:
            load_event = global_event_map.get(load_event_name, None)
            if load_event is not None:
                event = load_event._element
        
        info = []
        for tag in event.iterchildren('removeCrew', 'crewMember', 'reveal_map', 'autoReward'):
            if tag.tag == 'removeCrew':
                clonetag = xpath(tag, './clone')
                if len(clonetag) != 1:
                    info.append('Lose your crew(?)')
                    continue
                if clonetag[0].text == 'true':
                    info.append('Lose your crew(clonable)')
                elif clonetag[0].text == 'false':
                    info.append('Lose your crew(UNCLONABLE)')
                else:
                    info.append('Lose your crew(?)')
            
            elif tag.tag == 'crewMember':
                race = tag.attrib.get('class', '?').replace('_', ' ').title()
                info.append(f'Gain a crew({race})')
                
            elif tag.tag == 'reveal_map':
                info.append('Map Reveal')
            
            elif tag.tag == 'autoReward':
                info.append('Reward')

        return info
                
    
    def _get_recursive_info(self):
        child_info = []
        try:
            if len(self._childEventTag._childChoiceTags) > 0:
                child_info = [childChoiceTag._get_recursive_info() for childChoiceTag in self._childEventTag._childChoiceTags]
        except Exception:
            pass
        
        info = self._event_analize()
        if info is None:
            return [] + child_info
        return info + child_info
    
    def set_additional_info(self):
        self._additional_info = self._get_recursive_info()
    
    def get_formatted_additional_info(self):
        choices = [str(obj) for obj in self._additional_info]
        choices = '\n'.join(choices)
        return choices
    
class Event():
    def __init__(self, element, xmlpath, uniqueXPathGenerator):
        self._element = element
        self._xmlpath = xmlpath.replace('src-en/', '')
        self._uniqueXPathGenerator = uniqueXPathGenerator
        self._childChoiceTags = None
    
    
    def init_childChoiceTags(self):
        childChoiceTags = xpath(self._element, './choice')
        self._childChoiceTags = [global_choice_map.get(f'{self._xmlpath}${self._uniqueXPathGenerator.getpath(childChoiceTag)}') for childChoiceTag in childChoiceTags]


global_event_map = {}
for xmlpath in glob_posix('src-en/data/*'):
    if not re.match(r'.+\.(xml|xml.append)$', xmlpath):
        continue
    tree = parse_ftlxml(xmlpath)
    root = tree.getroot()
    if root.tag != 'FTL':
        continue
    events = xpath(tree, '//event')
    uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
    global_event_map.update({element.attrib.get('name'): Event(element, xmlpath, uniqueXPathGenerator) for element in events})


with open('mvloc.config.jsonc', 'tr', encoding='utf8') as f:
    config = load(f)

global_choice_map = {}
for xmlpath in config['filePatterns']:
    tree = parse_ftlxml('src-en/' + xmlpath)
    uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
    elements = xpath(tree, '//choice')

    global_choice_map.update({f'{xmlpath}${uniqueXPathGenerator.getpath(element)}': Choice(element, xmlpath, uniqueXPathGenerator) for element in elements})

for tag in global_choice_map.values():
    tag.init_childEventTag()
for tag in global_event_map.values():
    tag.init_childChoiceTags()
for tag in global_choice_map.values():
    tag.set_additional_info()
# textTag_map = {choicetag.get_textTag_uniqueXPath(): choicetag for choicetag in choiceTag_map.values()}

# dict_original, _, _ = readpo(f'locale/{xmlpath}/en.po')
# new_entries = []
# for key, entry in dict_original.items():
#     value = entry.value
#     _, xpath_key = parsekey(key)
#     target_choicetag = textTag_map.get(xpath_key)
#     if target_choicetag is not None:
#         value += '\n' + target_choicetag.get_formatted_additional_info()
#     else:
#         pass
    
#     new_entries.append(StringEntry(key, value, entry.lineno, False, False))
#     #writepo(f'locale/{xmlpath}/choice-info-en.po', new_entries, f'src-en/{xmlpath}')
