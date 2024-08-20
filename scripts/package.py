from run import main
import re
from shutil import make_archive, rmtree, copytree, copy
from tempfile import TemporaryDirectory
from mvlocscript.fstools import glob_posix, ensureparent
from mvlocscript.ftl import parse_ftlxml, write_ftlxml

def package(name, dist_dir):
    with TemporaryDirectory() as tmp_root:
        tmp_root += '/working/'
        copytree('output', tmp_root)
        output_files = {file for file in glob_posix('**', root_dir='output')}
        for auxfile_path in glob_posix('**', root_dir='auxfiles'):
            if auxfile_path not in output_files:
                print('copying file: ',  auxfile_path)
                ensureparent(tmp_root + auxfile_path)
                copy('auxfiles/' + auxfile_path, tmp_root + auxfile_path)
                continue
            
            if not re.match(r'.+\.xml\.append$', auxfile_path):
                print('unhandlable file found: ', auxfile_path)
                continue
            
            print('merging xml file: ', auxfile_path)
            output_tree = parse_ftlxml('output/' + auxfile_path)
            auxfile_tree = parse_ftlxml('auxfiles/' + auxfile_path)
            
            output_tree.getroot().extend([element for element in auxfile_tree.getroot().iterchildren()])
            write_ftlxml(tmp_root + auxfile_path, output_tree)
                    
        #make zip file.
        make_archive(f'{dist_dir}/{name}', 'zip', tmp_root)

MV_VERSION = '5.4.6'
CHOICE_INFO_VERSION = '2.1'

#{package name: config} the config defaults to the full version, so each setting is for restricting info.
packagedict = {
    #Full version
    f'[MV{MV_VERSION}]ChoiceInfo-{CHOICE_INFO_VERSION}': {},
}

if __name__ == '__main__':
    for name, config in packagedict.items():
        rmtree('output')
        main(packageConfig=config)
        package(name, 'packages')