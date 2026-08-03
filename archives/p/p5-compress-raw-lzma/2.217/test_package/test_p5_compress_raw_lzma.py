import subprocess
import sys


def main():
    command = [
        sys.argv[1],
        "-MCompress::Raw::Lzma",
        "-e",
        (
            "die $Compress::Raw::Lzma::VERSION "
            "unless $Compress::Raw::Lzma::VERSION eq q{2.217}; "
            "print qq{PASS: Compress::Raw::Lzma 2.217 loaded\\n}"
        ),
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
