#!/usr/bin/env python3
"""Optional PARI integration: requires a working GP and official base sea0."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gp", required=True)
    parser.add_argument("--datadir", type=Path, required=True)
    parser.add_argument("--base-sea0", type=Path, required=True)
    args = parser.parse_args()
    expected = json.loads((Path(__file__).parent / "expected.json").read_text(encoding="utf-8"))
    levels = [record["level"] for name, record in expected.items() if name.endswith(".gz")]
    residues = [expected[f"sea{level}.gz"]["evaluation_mod_1000003"] for level in levels]
    if not args.base_sea0.is_file():
        raise RuntimeError("PARI requires the official base seadata/sea0 in addition to big data")
    with tempfile.TemporaryDirectory(prefix="pari-integration-") as temporary:
        root = Path(temporary)
        shutil.copytree(args.datadir / "seadata", root / "seadata")
        shutil.copyfile(args.base_sea0, root / "seadata" / "sea0")
        script = root / "test.gp"
        script.write_text(
            'default(datadir,getenv("PARI_SEADATA_BIG_DATADIR"));\n'
            f'levels={levels};\nexpected={residues};\n'
            'iferr(for(i=1,#levels, p=levels[i]; e=ellmodulareqn(p); '
            'if(e[2]!=1 || poldegree(e[1],x)!=p+1,error("type or degree mismatch")); '
            'r=lift(subst(subst(Mod(e[1],1000003),x,2),y,3)); '
            'if(r!=expected[i],error("modular evaluation mismatch")); '
            'print("[ok] PARI ellmodulareqn ",p)),E,print(E);quit(1));\n'
            'print("__PARI_44_PASSED__");quit(0);\n', encoding="utf-8")
        result = subprocess.run([args.gp, "-fq", "-s", "256M", str(script)],
                                env={**os.environ, "PARI_SEADATA_BIG_DATADIR": str(root)},
                                capture_output=True, text=True, timeout=900)
        print(result.stdout, end="")
        print(result.stderr, end="")
        if (result.returncode != 0 or "__PARI_44_PASSED__" not in result.stdout
                or result.stdout.count("[ok] PARI ellmodulareqn ") != 44):
            raise RuntimeError("PARI integration failed (GP can return zero after a script error)")


if __name__ == "__main__":
    main()
