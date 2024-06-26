from run import main
import subprocess
from shutil import make_archive

main()
subprocess.run('poetry run mvloc batch-apply choice-info-en', shell=True)
make_archive('packages/choice-info', 'zip', 'output-choice-info-en')