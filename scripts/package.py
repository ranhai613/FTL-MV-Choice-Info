from run import main
import subprocess
from shutil import make_archive

def package(name, eventTypes):
    main(eventTypes=eventTypes)
    subprocess.run('poetry run mvloc batch-apply choice-info-en', shell=True)
    make_archive(f'packages/{name}', 'zip', 'output-choice-info-en')

version = 'beta0.1.1'

packagedict = {
    f'ChoiceInfo-ShipUnlock+CrewLoss-{version}': ['unlockCustomShip', 'removeCrew'],
    f'ChoiceInfo-Full-{version}': None
}

for name, eventTypes in packagedict.items():
    package(name, eventTypes)