#!/usr/bin/env python3
"""test_io_multiplex.py — L0c-visible test source for perl-io-multiplex 1.16.

L0c requires a .c/.cpp/.py test source file in test_package/ (a bare
.pl is not recognized by the static scan — CI L0c no_test_sources).
This .py source drives the packaged IO::Multiplex via perl (real API:
new + add socket + loop setup) so the real-module verification still runs.
Usage: test_io_multiplex.py <site-perl-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_io_multiplex.py <site-perl-dir>")
    site = sys.argv[1]
    pm = os.path.join(site, "IO", "Multiplex.pm")
    if not os.path.isfile(pm):
        raise AssertionError(f"IO/Multiplex.pm missing under {site}")
    # Real API check: load IO::Multiplex, construct mux object, add a
    # loopback TCP listener and verify handles() reflects the socket.
    perl_src = r"""
use IO::Multiplex;
use IO::Socket::INET;
use IO::Socket;
my $mux = IO::Multiplex->new();
defined $mux or die "IO::Multiplex->new failed";
my $srv = IO::Socket::INET->new(
    LocalAddr => '127.0.0.1',
    LocalPort => 0,
    Proto     => 'tcp',
    Listen    => 1,
    ReuseAddr => 1,
) or die "listener create failed: $!";
$mux->add($srv);
my $n = scalar($mux->handles());
die "handles() empty after add" unless $n >= 1;
$mux->remove($srv);
print "OK: IO::Multiplex 1.16 real API (new+add+handles+remove)\n";
"""
    r = subprocess.run(
        ["/data/service/hnp/bin/perl", "-I", site, "-e", perl_src],
        capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl IO::Multiplex check failed (rc={r.returncode})")
    print("OK: perl-io-multiplex 1.16 python-driven check")


if __name__ == "__main__":
    main()
