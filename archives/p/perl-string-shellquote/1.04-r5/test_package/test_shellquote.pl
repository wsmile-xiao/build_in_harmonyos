#!/usr/bin/env perl
# test_package/test_shellquote.pl — Functional tests for String::ShellQuote
# Run via: perl -I<lib_dir> test_shellquote.pl
use strict;
use warnings;
use String::ShellQuote qw(shell_quote shell_quote_best_effort shell_comment_quote);

my $pass = 0;
my $fail = 0;

sub check {
    my ($desc, $got, $expected) = @_;
    if ($got eq $expected) {
        $pass++;
    } else {
        print "FAIL: $desc\n  expected: [$expected]\n  got:      [$got]\n";
        $fail++;
    }
}

# Module loaded successfully
$pass++;

# shell_quote basic
check('shell_quote(hello world)', shell_quote('hello', 'world'), 'hello world');
check('shell_quote(empty list)', shell_quote(), '');
check('shell_quote(empty string)', shell_quote(''), "''");
check('shell_quote(undef)', shell_quote(undef), "''");

# shell_quote special chars
check('shell_quote(foo*)', shell_quote('foo*'), "'foo*'");
check('shell_quote(foo bar)', shell_quote('foo bar'), "'foo bar'");
check('shell_quote(single quote)', shell_quote("'"), "\\'");

# shell_quote_best_effort
check('best_effort(empty)', shell_quote_best_effort(), '');
check('best_effort(foo*)', shell_quote_best_effort('foo*'), "'foo*'");

# shell_comment_quote
check('comment_quote(empty)', shell_comment_quote(''), '');
check('comment_quote(foo)', shell_comment_quote('foo'), 'foo');
check('comment_quote(newlines)', shell_comment_quote("foo\nbar"), "foo\n#bar");

# null byte handling
eval { shell_quote("t\x00") };
if ($@) {
    $pass++;
} else {
    print "FAIL: shell_quote should croak on null byte\n";
    $fail++;
}
my $r = shell_quote_best_effort("foo*", "as\x00df");
if ($r =~ /foo\*/) {
    $pass++;
} else {
    print "FAIL: shell_quote_best_effort should include foo* in output\n";
    $fail++;
}

print "$pass tests passed, $fail failed\n";
exit($fail > 0 ? 1 : 0);
