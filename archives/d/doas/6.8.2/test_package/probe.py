"""Three real installed CLI/parser consumers. No authentication bypass or PASS skip."""
import hashlib,json,os,re,shutil,subprocess,tempfile
from pathlib import Path

def verdict(name, rc, message):
 account_block='no passwd entry' in message.lower()
 syntax_error=bool(re.search(r'doas: syntax error at line \d+',message))
 parser_reached=not account_block and ((name=='valid-parser' and rc==0) or (name=='invalid-parser' and syntax_error))
 ok=(parser_reached and rc==0) if name=='valid-parser' else (parser_reached and rc==1) if name=='invalid-parser' else (rc==1 and 'usage: doas' in message and not account_block)
 return bool(ok),bool(parser_reached)

def main():
 binary=shutil.which('doas')
 if not binary:raise SystemExit('FAIL: installed doas unavailable in conanrun PATH')
 exe=Path(binary).resolve(strict=True)
 print(json.dumps(dict(actual_binary=str(exe),sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),uid=os.getuid(),euid=os.geteuid(),authentication_and_privilege_proven=False)))
 passed=0
 with tempfile.TemporaryDirectory(prefix='doas-consumer-',dir=os.environ.get('TMPDIR',os.getcwd())) as folder:
  root=Path(folder);good=root/'good.conf';bad=root/'bad.conf'
  # Parser-only fixture; never disable password authentication, nor execute it.
  good.write_text('permit 0\n',encoding='utf8');bad.write_text('frobnicate all\n',encoding='utf8')
  for name,args in [('valid-parser',['-C',str(good)]),('invalid-parser',['-C',str(bad)]),('usage',[])]:
   result=subprocess.run([str(exe),*args],stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
   message=(result.stdout+result.stderr).decode('utf8',errors='replace')
   ok,parser_reached=verdict(name,result.returncode,message)
   print(json.dumps(dict(case=name,argv=[str(exe),*args],rc=result.returncode,stdout=result.stdout.decode('utf8',errors='replace'),stderr=result.stderr.decode('utf8',errors='replace'),parser_reached=parser_reached,passed=ok)))
   passed+=int(ok)
 print(f'CONSUMER_TEST_PASS={passed}/3; AUTHENTICATION_NOT_PROVEN; PRIVILEGE_NOT_PROVEN')
 raise SystemExit(0 if passed==3 else 1)

if __name__=='__main__':main()
