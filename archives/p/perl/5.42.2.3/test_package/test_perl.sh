#!/usr/bin/env zsh
# Verify the packaged Perl runtime and native XS modules.
set -euo pipefail

: "${PERL:=perl}"

"$PERL" -e 'die "unexpected version $]" unless $] == 5.042002; print "perl $] ok\n"'
"$PERL" -MConfig -MFile::Spec -e 'print "os=$Config::Config{osname}; arch=$Config::Config{archname}; sep=", File::Spec->catfile(qw(a b)), "\n"'
"$PERL" -MFcntl -MPOSIX -e 'die "Fcntl constants unavailable" unless defined Fcntl::O_RDONLY(); die "POSIX floor unavailable" unless POSIX::floor(1.5) == 1; print "XS modules ok\n"'
"$PERL" -e 'use strict; use warnings; my $x = 21 * 2; die unless $x == 42; print "script ok\n"'
