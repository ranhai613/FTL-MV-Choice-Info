from run import main
import subprocess
from shutil import make_archive

def package(name, config):
    lang = config.get('lang', 'en')
    command = ['poetry', 'run', 'mvloc', 'batch-apply', f'choice-info-{lang}']
    if config.get('machine', False):
        command.append('-m')
    #analyze info and write it to .po file.
    main(packageConfig=config)
    #generate xml files from .po files. I reuse the workflow of MV translation. If you want to learn more, visit MV translation project Github.
    subprocess.run(command)
    make_archive(f'packages/{name}', 'zip', f'output-choice-info-{lang}')

mvversion = '5.4.6'
version = 'beta0.1.3'

#{package name: config} the config defaults to the full version, so each setting is for restricting info.
packagedict = {
    Ship Unlock + Crew Loss only version
    f'[MV{mvversion}]ChoiceInfo-ShipUnlock+CrewLoss-{version}':
        {
         #default: all events in events.py. You can restrict to specific events by list event tag name.
         'events': ['unlockCustomShip', 'removeCrew'],
         #default: False. Wether ignore fixed events(i.g. Storage Check) or not.
         'ignoreFixedEvent' : True,
         #default: 10. How many times Event Analyzer searches info one step deeply if it cannot find any info.
         'maxDeeperRetry': 1,
        },
    #Full version
    f'[MV{mvversion}]ChoiceInfo-Full-{version}': {},
    f'[MV{mvversion}]ChoiceInfo_Ja-ShipUnlock+CrewLoss-{version}':
        {
         'lang': 'ja',
         'machine': True,
         'events': ['unlockCustomShip', 'removeCrew'],
         'ignoreFixedEvent' : True,
         'maxDeeperRetry': 1,
        },

}

for name, config in packagedict.items():
    package(name, config)