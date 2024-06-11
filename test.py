from mvlocscript.ftl import parse_ftlxml, ftl_xpath_matchers
from mvlocscript.xmltools import xpath, UniqueXPathGenerator
from mvlocscript.potools import readpo, writepo, StringEntry, parsekey
from json5 import load

#'removeCrew', 'autoReward', 'crewMember', 'reveal_map', 'modifyPursuit', 'item_modify', 'ship'
class ChoiceTag():
    def __init__(self, element):
        self._element = element
        self._childEventTags = xpath(element, './event')
        self._childChoiceTags = None
        self._additional_info = None
        

    def init_childChoiceTags(self):
        childChoiceTags = xpath(self._element, './event/choice')
        self._childChoiceTags = [choiceTag_map[uniqueXPathGenerator.getpath(childChoiceTag)] for childChoiceTag in childChoiceTags]

    def get_uniqueXPath(self):
        return uniqueXPathGenerator.getpath(self._element)
    
    def get_textTag_uniqueXPath(self):
        texttags = xpath(self._element, './text')
        if len(texttags) != 1:
            return None
        
        return uniqueXPathGenerator.getpath(texttags[0])
    
    def _event_analize(self):
        if len(self._childEventTags) != 1:
            return None
        
        info = []
        for tag in self._childEventTags[0].iterchildren('removeCrew', 'crewMember', 'reveal_map', 'autoReward'):
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
        if len(self._childChoiceTags) > 0:
            child_info = [childChoiceTag._get_recursive_info() for childChoiceTag in self._childChoiceTags]
        
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
    

with open('mvloc.config.jsonc', 'tr', encoding='utf8') as f:
    config = load(f)

for xmlpath in config['filePatterns']:
        
    tree = parse_ftlxml('src-en/' + xmlpath)
    uniqueXPathGenerator = UniqueXPathGenerator(tree, ftl_xpath_matchers())
    elements = xpath(tree, '//choice')

    choiceTag_map = {uniqueXPathGenerator.getpath(element): ChoiceTag(element) for element in elements}
    for tag in choiceTag_map.values():
        tag.init_childChoiceTags()
    for tag in choiceTag_map.values():
        tag.set_additional_info()
    textTag_map = {choicetag.get_textTag_uniqueXPath(): choicetag for choicetag in choiceTag_map.values()}
    
    dict_original, _, _ = readpo(f'locale/{xmlpath}/en.po')
    new_entries = []
    for key, entry in dict_original.items():
        value = entry.value
        _, xpath_key = parsekey(key)
        target_choicetag = textTag_map.get(xpath_key)
        if target_choicetag is not None:
            value += '\n' + target_choicetag.get_formatted_additional_info()
        else:
            pass
        
        new_entries.append(StringEntry(key, value, entry.lineno, False, False))
    writepo(f'locale/{xmlpath}/choice-info-en.po', new_entries, f'src-en/{xmlpath}')
