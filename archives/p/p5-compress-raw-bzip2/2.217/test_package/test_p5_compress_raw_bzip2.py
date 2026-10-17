import subprocess
import sys


def main():
    command = [
        sys.argv[1],
        "-MCompress::Raw::Bzip2",
        "-e",
        (
            "die $Compress::Raw::Bzip2::VERSION "
            "unless $Compress::Raw::Bzip2::VERSION eq q{2.217}; "
            "print qq{PASS: Compress::Raw::Bzip2 2.217 loaded\\n}"
        ),
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
