"""Consumer tests execute only the installed package binary, offline."""
import pathlib, re, subprocess, sys, tempfile

binary = str(pathlib.Path(sys.argv[1]).resolve(strict=True))
labels = []
def check(label, condition):
    if not condition:
        raise AssertionError(label)
    labels.append(label)
    print('ok - '+label, flush=True)

with tempfile.TemporaryDirectory(prefix='mptp-consumer-') as temp:
    root = pathlib.Path(temp)
    def run(*args):
        return subprocess.run([binary,*map(str,args)],cwd=root,text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    version = run('--version')
    check('installed version', version.returncode==0 and '0.2.5' in version.stdout)
    help_ = run('--help')
    check('installed help', help_.returncode==0 and '--tree_file' in help_.stdout)
    tree = root/'tree.nwk'
    tree.write_text('((A:0.01,B:0.01):1,((C:0.01,D:0.01):1,(E:0.01,F:0.01):1):1);\n')
    reports = {}
    for method in ('single','multi'):
        result = run('--ml','--'+method,'--tree_file',tree,'--output_file',root/method,'--seed','42')
        report=root/(method+'.txt')
        text=report.read_text() if report.exists() else ''
        check('ML '+method, result.returncode==0 and 'Number of delimited species:' in text
              and all(x in text for x in ('A','B','C','D','E','F')))
        reports[method]=text
    check('SVG output', all('<svg' in p.read_text() for p in root.glob('*.svg'))
          and len(list(root.glob('*.svg')))>=2)
    repeat=run('--ml','--multi','--tree_file',tree,'--output_file',root/'repeat','--seed','42')
    match=lambda text: re.search(r'Number of delimited species: (\d+)',text).group(1)
    check('repeatable delimitation', repeat.returncode==0
          and match((root/'repeat.txt').read_text())==match(reports['multi']))
    mcmc=run('--multi','--mcmc','100','--mcmc_sample','10','--mcmc_burnin','10',
             '--mcmc_startml','--tree_file',tree,'--output_file',root/'mcmc','--seed','42')
    check('MCMC run', mcmc.returncode==0 and any(root.glob('mcmc*.txt')))
    bad=root/'invalid.nwk'
    bad.write_text('(invalid newick;\n')
    invalid=run('--ml','--multi','--tree_file',bad,'--output_file',root/'bad')
    check('invalid Newick rejected', invalid.returncode!=0)
assert len(labels)==8
