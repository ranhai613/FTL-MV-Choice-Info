from run import main
import subprocess
from shutil import make_archive

def package(name, config):
    #analyze info and write it to .po file.
    main(packageConfig=config)
    #generate xml files from .po files. I reuse the workflow of MV translation. If you want to learn more, visit MV translation project Github.
    subprocess.run('poetry run mvloc batch-apply choice-info-en', shell=True)
    make_archive(f'packages/{name}', 'zip', 'output-choice-info-en')

mvversion = '5.4.6'
version = 'beta0.1.2'

#{package name: config} the config defaults to the full version, so each setting is for restricting info.
packagedict = {
    #Ship Unlock + Crew Loss only version
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
    f'[MV{mvversion}]ChoiceInfo-Full-{version}': {}
}

for name, config in packagedict.items():
    package(name, config)