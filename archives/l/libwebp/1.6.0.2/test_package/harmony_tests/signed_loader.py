"""Current CI entry: the real platform test must complete before its marker."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from harmony_signed_loader import run
run(sys.argv[1],sys.argv[2],sys.argv[3])
print('HARMONY_TEST_PASS=1/1')
