#!/usr/bin/env perl
# test_package/test.pl — Functional test for String::RewritePrefix
# Tests the core rewrite functionality on OHOS platform
use strict;
use warnings;

# Set pure-Perl mode for Params::Util (bypasses XS .so SELinux restriction)
# PERL5LIB is set by test_package/conanfile.py to include all dependency paths
$ENV{PERL_PARAMS_UTIL_PP} = 1;

use String::RewritePrefix;

my $tests_passed = 0;
my $tests_total = 0;

# Test 1: Basic prefix rewriting (from synopsis)
$tests_total++;
my @result1 = String::RewritePrefix->rewrite(
    { '' => 'MyApp::', '+' => '' },
    qw(Plugin Mixin Addon +Corporate::Thinger),
);
my @expected1 = qw(MyApp::Plugin MyApp::Mixin MyApp::Addon Corporate::Thinger);
if (@result1 == @expected1 && !grep { $result1[$_] ne $expected1[$_] } 0..$#result1) {
    print "ok 1 - synopsis rewrite\n";
    $tests_passed++;
} else {
    print "not ok 1 - synopsis rewrite: got [", join(", ", @result1), "]\n";
}

# Test 2: Multiple prefix types
$tests_total++;
my @result2 = String::RewritePrefix->rewrite(
    { '-' => 'Tet::', '@' => 'KaTet::', '+' => sub { $_[0] . '::Foo::' }, '!' => sub { undef } },
    qw(-Corporation @Roller Plinko +Bar !None),
);
my @expected2 = qw(Tet::Corporation KaTet::Roller Plinko Bar::Foo::Bar None);
if (@result2 == @expected2 && !grep { $result2[$_] ne $expected2[$_] } 0..$#result2) {
    print "ok 2 - multi-prefix rewrite\n";
    $tests_passed++;
} else {
    print "not ok 2 - multi-prefix rewrite: got [", join(", ", @result2), "]\n";
}

# Test 3: Scalar context
$tests_total++;
my $scalar = String::RewritePrefix->rewrite(
    { '' => 'MyApp::', '+' => '' },
    'Plugin',
);
if ($scalar eq 'MyApp::Plugin') {
    print "ok 3 - scalar context\n";
    $tests_passed++;
} else {
    print "not ok 3 - scalar context: got '$scalar'\n";
}

# Test 4: No matching prefix (passthrough)
$tests_total++;
my @result4 = String::RewritePrefix->rewrite(
    { '+' => '' },
    qw(NoPrefix Here),
);
my @expected4 = qw(NoPrefix Here);
if (@result4 == @expected4 && !grep { $result4[$_] ne $expected4[$_] } 0..$#result4) {
    print "ok 4 - passthrough\n";
    $tests_passed++;
} else {
    print "not ok 4 - passthrough: got [", join(", ", @result4), "]\n";
}

# Test 5: Import-based rewrite
$tests_total++;
{
    String::RewritePrefix->import(
        rewrite => { -as => 'pfx_rw', prefixes => {
            '-' => 'minus ',
            '+' => 'plus ',
            ''  => 'plus ',
        }}
    );
    my @r = pfx_rw(qw(+10 10 -10 0));
    my @exp = ('plus 10', 'plus 10', 'minus 10', 'plus 0');
    if (@r == @exp && !grep { $r[$_] ne $exp[$_] } 0..$#r) {
        print "ok 5 - import-based rewrite\n";
        $tests_passed++;
    } else {
        print "not ok 5 - import-based rewrite: got [", join(", ", @r), "]\n";
    }
}

# Test 6: Longest-prefix-first ordering
$tests_total++;
my @result6 = String::RewritePrefix->rewrite(
    { 'ab' => 'AB_', 'a' => 'A_' },
    qw(abc abd ae),
);
my @expected6 = qw(AB_c AB_d A_e);
if (@result6 == @expected6 && !grep { $result6[$_] ne $expected6[$_] } 0..$#result6) {
    print "ok 6 - longest-prefix-first\n";
    $tests_passed++;
} else {
    print "not ok 6 - longest-prefix-first: got [", join(", ", @result6), "]\n";
}

print "\n$tests_passed/$tests_total tests passed\n";
exit($tests_passed == $tests_total ? 0 : 1);
