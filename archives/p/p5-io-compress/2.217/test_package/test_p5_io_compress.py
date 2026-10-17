import subprocess
import sys


def main():
    command = [
        sys.argv[1],
        "-MIO::Compress::Gzip=gzip,$GzipError",
        "-MIO::Uncompress::Gunzip=gunzip,$GunzipError",
        "-e",
        (
            "my $in=q{harmonyos}; my $z=q{}; "
            "gzip(\\$in => \\$z) or die $GzipError; "
            "my $out=q{}; gunzip(\\$z => \\$out) or die $GunzipError; "
            "die $out unless $out eq $in; "
            "die $IO::Compress::Base::VERSION "
            "unless $IO::Compress::Base::VERSION eq q{2.217}; "
            "print qq{PASS: IO::Compress gzip roundtrip ok\\n}"
        ),
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
