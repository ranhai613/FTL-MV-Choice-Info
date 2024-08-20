from package import package
import subprocess

MODLIST = [
    'Multiverse 5.4.5 - Assets (Patch above Data).zip',
    'Multiverse 5.4.6 - Data.zip',
    'choiceInfo-test.zip',
    'Speed-UI_customized.zip',
    'Instant_Clone_and_Heal_after_Battle_v1.4.zip'
]

package('choiceInfo-test', 'SlipstreamModManager_1.9.1-Win/mods')
subprocess.run(['SlipstreamModManager_1.9.1-Win/modman.exe', '--runftl', '--patch'] + MODLIST)