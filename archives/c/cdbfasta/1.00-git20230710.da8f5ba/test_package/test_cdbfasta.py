import os
import subprocess
import sys
import tempfile


def check(condition, message):
    if condition:
        print("PASS: " + message)
        return 0
    print("FAIL: " + message)
    return 1


def main():
    cdbfasta, cdbyank = sys.argv[1], sys.argv[2]
    failures = 0
    fasta = ">s1 description one\nACGTACGTAC\n>s2 description two\nTTTTGGGGCC\n"

    with tempfile.TemporaryDirectory() as tmp:
        fa = os.path.join(tmp, "t.fa")
        with open(fa, "w") as f:
            f.write(fasta)

        r = subprocess.run([cdbfasta, fa], capture_output=True, text=True)
        failures += check(r.returncode == 0,
                          "cdbfasta indexes a multi-FASTA file (exit 0)")

        cidx = fa + ".cidx"
        failures += check(os.path.exists(cidx),
                          "cdbfasta creates the .cidx index next to the database")

        r = subprocess.run([cdbyank, "-a", "s1", cidx], capture_output=True, text=True)
        ok = r.returncode == 0 and r.stdout.startswith(">s1") and "ACGTACGTAC" in r.stdout
        failures += check(ok, "cdbyank -a s1 retrieves the full record by key")

        r = subprocess.run([cdbyank, "-a", "s2", cidx], capture_output=True, text=True)
        ok = r.returncode == 0 and "TTTTGGGGCC" in r.stdout
        failures += check(ok, "cdbyank -a s2 retrieves the second record by key")

        r = subprocess.run([cdbyank, "-a", "absent", cidx], capture_output=True, text=True)
        ok = r.returncode == 0 and r.stdout.strip() == ""
        failures += check(ok, "cdbyank returns nothing for an absent key")

    if failures != 0:
        print("cdbfasta 1.00-git20230710.da8f5ba test failed")
        return 1

    print("cdbfasta 1.00-git20230710.da8f5ba: all 5 assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
