import os
import shutil
import subprocess
import tempfile


def main():
    executable = shutil.which("minia")
    assert executable, "Conan run environment did not expose the packaged minia command"

    here = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory(prefix="minia-consumer-") as work:
        reads = os.path.join(here, "X.fa")
        subprocess.run(
            [executable, "-in", reads, "-kmer-size", "5", "-abundance-min", "1",
             "-traversal", "unitig", "-minimizer-size", "3"],
            cwd=work,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        contigs = os.path.join(work, "X.contigs.fa")
        assert os.path.isfile(contigs), "minia did not emit the expected contig file"
        with open(contigs, encoding="utf-8") as output:
            count = sum(line.startswith(">") for line in output)
        assert count == 6, f"expected six contigs for the upstream X fixture, got {count}"


if __name__ == "__main__":
    main()
