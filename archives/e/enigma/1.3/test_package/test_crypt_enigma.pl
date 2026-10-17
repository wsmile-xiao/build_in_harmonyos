#!/usr/bin/env perl
# test_crypt_enigma.pl — consumer test for enigma 1.3 (Crypt::Enigma).
#
# Calls the real Crypt::Enigma API (new/cipher/setSteckerBoard/setReflector/
# setRotor/getters) and checks exact vectors verified against the patched
# module with Git-for-Windows perl 5.42 (see notes.md), so an identity stub
# or a canned-answer stub cannot pass. TAP output plus a final
# ENIGMA_TEST_RESULT line consumed by test_enigma.py.
use strict;
use warnings;
use Crypt::Enigma;

my $TOTAL = 18;
print "1..$TOTAL\n";

my $n = 0;
my $pass = 0;

sub check {
    my ($cond, $desc) = @_;
    $n++;
    if ($cond) {
        $pass++;
        print "ok $n - $desc\n";
    }
    else {
        print "not ok $n - $desc\n";
    }
}

# 1: module identity.
check($Crypt::Enigma::VERSION eq '1.3', 'VERSION is 1.3');

# 2-5: fresh object semantics (constructor fills _settings only; no rotor
# objects are stored until cipher/setRotor populates them; _rotorObjects is
# initialised to [] by the portability patch so getters return empty here
# instead of crashing on undef).
my $e1 = Crypt::Enigma->new();
check($e1->getReflector() eq 'ReflectorB', 'default reflector is ReflectorB');
check(scalar($e1->getRotorNames()) == 0, 'fresh object stores no rotor objects');
check(scalar($e1->getStartLetters()) == 0, 'fresh object start letters empty');
check(scalar($e1->getRingSettings()) == 0, 'fresh object ring settings empty');

# 6-11: exact vectors with the default rotors (RotorI/Z/0, RotorII/A/0,
# RotorIII/A/0, ReflectorB), verified with perl 5.42 against the patched
# Enigma.pm: cipher rebuilds rotors from _settings each call, so every call
# starts from the same state and the reflector involution gives round-trip.
check($e1->cipher('HELLO') eq 'ZPEZR', "cipher('HELLO') eq 'ZPEZR'");
check($e1->cipher($e1->cipher('HELLO')) eq 'HELLO', 'reflector involution round-trip');
check($e1->cipher('AAAAA') eq 'UIZBM', "cipher('AAAAA') eq 'UIZBM'");
check($e1->cipher('A B-1C') eq 'UVW', 'non-alpha input is dropped');
check($e1->cipher('hello') eq 'ZPEZR', 'input is upper-cased before ciphering');
check($e1->cipher('') eq '', 'empty input gives empty output');

# 12-13: steckerboard takes effect immediately.
my $e2 = Crypt::Enigma->new();
$e2->setSteckerBoard(['A', 'B']);
check($e2->cipher('A') eq 'E', 'steckerboard A<->B changes cipher output');
check($e2->cipher($e2->cipher('AB')) eq 'AB', 'round-trip with steckerboard');

# 14-15: invalid reflector falls back to ReflectorB.
my $e3 = Crypt::Enigma->new();
$e3->setReflector('BogusReflector');
check($e3->getReflector() eq 'ReflectorB', 'invalid reflector falls back to ReflectorB');
check($e3->cipher('HELLO') eq 'ZPEZR', 'fallback reflector still ciphers');

# 16-18: setRotor return contract and stored-rotor visibility. Rotors must
# be installed in ascending number order: a lone setRotor(..., 2) leaves a
# hole at index 0 and getRotorNames would dereference undef.
my $e4 = Crypt::Enigma->new();
check($e4->setRotor('RotorI', 'A', '0', 1) == 1 && $e4->setRotor('RotorVII', 'A', '0', 2) == 1, 'setRotor accepts ordered definitions');
my @names = $e4->getRotorNames();
check(scalar(@names) == 2 && $names[0] eq 'RotorI' && $names[1] eq 'RotorVII', 'stored rotors visible via getRotorNames');
check($e4->setRotor('RotorI', 'A', '0', 0) == 0, 'setRotor rejects rotor number 0');

print "ENIGMA_TEST_RESULT passed=$pass total=$TOTAL\n";
exit($pass == $TOTAL ? 0 : 1);
