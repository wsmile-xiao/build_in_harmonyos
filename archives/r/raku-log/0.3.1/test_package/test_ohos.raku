use v6.d;
use Test;

# HarmonyOS-specific consumer test.
#
# On Linux MoarVM reports $*KERNEL.name as "linux"; the HarmonyOS port reports
# "harmonyos" and exposes the HongMeng kernel release. These assertions therefore
# fail on a generic Linux host and only pass on the OHOS target, which is what
# makes this a platform-specific (not generic POSIX) test.

plan 5;

is $*KERNEL.name, 'harmonyos', 'Raku runtime identifies the HarmonyOS kernel';
ok $*KERNEL.release.contains('HongMeng'),
    'HarmonyOS kernel release reports the HongMeng kernel';
is $*KERNEL.hardware, 'aarch64', 'HarmonyOS PC target is aarch64';

my $tmp = %*ENV<TMPDIR> // %*ENV<HOME>;
ok $tmp.IO.d, 'HarmonyOS temporary/cache directory exists';

my $path = $tmp.IO.add("raku-log-ohos-test-{$*PID}.txt");
LEAVE $path.unlink if $path.e;
my $text = 'HarmonyOS HMDFS UTF-8 ✓';
spurt $path, $text, :enc<utf8>;
is slurp($path, :enc<utf8>), $text, 'UTF-8 data survives a HarmonyOS filesystem round trip';

done-testing;
