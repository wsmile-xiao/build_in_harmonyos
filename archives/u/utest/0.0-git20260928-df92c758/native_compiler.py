"""Native OHOS compiler driver: sign ELF executables, including try_run probes."""
import os
from pathlib import Path
import subprocess
import sys

def main():
    args=sys.argv[1:]
    compiler=os.environ['UTEST_REAL_CXX' if 'cxx' in Path(sys.argv[0]).name else 'UTEST_REAL_CC']
    result=subprocess.run([compiler]+args)
    if result.returncode:return result.returncode
    if '-o' not in args or '-c' in args:return 0
    output=Path(args[args.index('-o')+1])
    if not output.is_file():return 0
    with output.open('rb') as f:header=f.read(18)
    if header[:4]!=b'\x7fELF' or int.from_bytes(header[16:18],'little') not in (2,3):return 0
    signed=Path(str(output)+'.utest-signed')
    subprocess.run([os.environ['UTEST_NATIVE_SIGNER'],'sign','-selfSign','1',
                    '-inFile',str(output),'-outFile',str(signed)],check=True,
                   stdout=sys.stderr,timeout=30)
    os.chmod(signed,0o700)
    os.replace(signed,output)
    return 0

if __name__=='__main__':sys.exit(main())
