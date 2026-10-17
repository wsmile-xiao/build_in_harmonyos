#!/usr/bin/env perl
# test_parsewords.pl — consumer test source for perl-text-parsewords 3.31 (L0c).
#
# REAL API check (R34) on the packaged Text::ParseWords:
#   quotewords/shellwords parse — core API (upstream t/ParseWords.t usage).
# Usage: test_parsewords.pl <site-perl-dir>
use strict;
use warnings;

# @INC injection must happen at compile time (use Text::ParseWords is
# compile-time) — shift @ARGV inside BEGIN so $site is available before
# `use Text::ParseWords` (AI review: runtime unshift → core-module false pass)
BEGIN {
    my $site = shift @ARGV
        or die "usage: test_parsewords.pl <site-perl-dir>\n";
    die "site-perl dir missing: $site\n" unless -d $site;
    unshift @INC, $site;
}

use Text::ParseWords;

# quotewords: parse tokens honoring quotes
my @words = quotewords('\s+', 0, 'this "is a" test');
die "quotewords parse mismatch: @words\n"
    unless @words == 3 && $words[0] eq 'this'
        && $words[1] eq 'is a' && $words[2] eq 'test';

# shellwords: classic shell tokenization
my @sw = shellwords("one two 'three four'");
die "shellwords parse mismatch: @sw\n"
    unless @sw == 3 && $sw[0] eq 'one' && $sw[1] eq 'two'
        && $sw[2] eq 'three four';

print "OK: perl-text-parsewords 3.31 real API ok (quotewords/shellwords)\n";
exit 0;
