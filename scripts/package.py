from run import main
from shutil import make_archive, rmtree
from os import mkdir
from events import EVENTCLASSMAPS

def package(name, config):
    #analyze info and write it to xml.append.
    main(packageConfig=config)
    #make zip file.
    make_archive(f'packages/{name}', 'zip', 'output-en')

MV_VERSION = '5.4.6'
CHOICE_INFO_VERSION = 'beta0.1.5'

#{package name: config} the config defaults to the full version, so each setting is for restricting info.
packagedict = {
    #Ship Unlock + Crew Loss only version
    f'[MV{MV_VERSION}]ChoiceInfo-ShipUnlock+CrewLoss-{CHOICE_INFO_VERSION}':
        {
         'eventMap': EVENTCLASSMAPS['ShipUnlock+CrewLoss'], #default: all events in events.py. You can restrict to specific events by set an event class map.
         'ignoreFixedEvent' : True, #default: False. Wether ignore fixed events(i.g. Storage Check) or not.
         'maxDeeperRetry': 1, #default: 10. How many times Event Analyzer searches info one step deeply if it cannot find any info.
        },
    #Full version
    f'[MV{MV_VERSION}]ChoiceInfo-Full-{CHOICE_INFO_VERSION}': {},
}

if __name__ == '__main__':
    for name, config in packagedict.items():
        rmtree('output-en/data')
        mkdir('output-en/data')
        package(name, config)