from run import main
import subprocess
from shutil import make_archive

def package(name, config):
    main(packageConfig=config)
    subprocess.run('poetry run mvloc batch-apply choice-info-en', shell=True)
    make_archive(f'packages/{name}', 'zip', 'output-choice-info-en')

mvversion = '5.4.6'
version = 'beta0.1.2'

packagedict = {
    f'[MV{mvversion}]ChoiceInfo-ShipUnlock+CrewLoss-{version}':
        {'events': ['unlockCustomShip', 'removeCrew'],
         'ignoreFixedEvent' : True
        },
    f'[MV{mvversion}]ChoiceInfo-Full-{version}': {}
}

for name, config in packagedict.items():
    package(name, config)