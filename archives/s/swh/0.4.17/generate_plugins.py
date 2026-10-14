"""Run the upstream integrity check and generator with a standard-library XML bridge."""
import json
import os
import pathlib
import re
import subprocess
import sys
from xml_tree import parse_tree

root = pathlib.Path.cwd()
perl = pathlib.Path(sys.argv[1])
perl_core = pathlib.Path(sys.argv[2])
assert perl.is_file()
assert (perl_core / 'strict.pm').is_file(), 'published Perl core missing'
# The module package uses Environment.append rather than append_path.
# Rebuild only this subprocess's typed module path, after Conan activation.
env = os.environ.copy()
architecture = sorted(p for p in perl_core.iterdir() if p.is_dir() and (p / 'auto').is_dir())
env['PERL5LIB'] = os.pathsep.join(map(str, [perl_core, *architecture]))
subprocess.run([str(perl), '-Mstrict', '-MJSON::PP', '-e', 'print qq(SWH_PERL_IMPORTS_PASS\\n)'],
               check=True, env=env, timeout=60)
make = (root / 'Makefile.am').read_text()
names = re.findall(r'\b([a-z][a-z0-9_]+)\.la\b', make.split('SUBDIRS')[0])
assert len(names) == len(set(names)) == 96, 'upstream plugin manifest drift'
xmls = sorted(root.glob('*.xml'))
assert len(xmls) == 100, 'upstream XML inventory drift'
result = subprocess.run([str(perl), str(root / 'bozosoity-checker.pl'), *map(str, xmls)],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60, env=env)
print(result.stdout, end='', flush=True)
result.check_returncode()
if '*** Warning:' in result.stdout:
    raise RuntimeError('Upstream release integrity check found invalid IDs')
print('SWH_UPSTREAM_RESULT=1/1 PASS (bozo: all 100 XML files)', flush=True)
generated = root / 'generated'
generated.mkdir()
for name in names:
    tree_path = generated / (name + '.tree.json')
    with tree_path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(parse_tree(root / (name + '.xml')), out, ensure_ascii=True)
    with (generated / (name + '.c')).open('xb') as out:
        subprocess.run([str(perl), str(root / 'makestub.pl'), str(root / (name + '.xml')), str(tree_path)],
                       stdout=out, check=True, timeout=60, env=env)
(generated / 'plugins.cmake').write_text('set(SWH_PLUGINS\n' + '\n'.join(names) + '\n)\n')
print('SWH_GENERATED_PLUGINS=96', flush=True)
