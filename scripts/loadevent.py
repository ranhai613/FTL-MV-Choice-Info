from mvlocscript.xmltools import xpath
from mvlocscript.ftl import parse_ftlxml, write_ftlxml
from lxml.etree import ElementTree, Element
from pathlib import Path
from pprint import pprint

TEXT_RETURN_MAP = {
    'STORAGE_CHECK_REAL': 'Storage Check'
}

def sanitize_loadEvent(element):
    baseName = element.get('name')
    assert baseName
    
    loadEvents = xpath(element, '//loadEvent')
    for loadEvent in loadEvents:
        if loadEvent.text == baseName:     
            loadEvent.tag = 'textReturn'
            loadEvent.text = '<='
        else:
            fixedText = TEXT_RETURN_MAP.get(loadEvent.text, None)
            if fixedText is not None:
                loadEvent.tag = 'textReturn'
                loadEvent.text = fixedText
    
    return element

def makeLoadEventXML():
    from run import main
    
    XML_PATH = 'scripts/loadEvent/5.4.6.xml'
    #assert not Path(XML_PATH).exists()
    
    stat = main(True)
    root = Element('FTL')
    root.extend([sanitize_loadEvent(event._element) for event in stat.values()])
    tree = ElementTree(root)
    write_ftlxml(XML_PATH, tree)
    #tree.write(XML_PATH, encoding='utf8', pretty_print=True)

if __name__ == '__main__':
    makeLoadEventXML()
    