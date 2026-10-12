#!/usr/bin/perl
# Functional consumer check for perl-regexp-common 2017060201.
# Loads the *installed* Regexp::Common (via PERL5LIB) and verifies core
# pattern behaviour. Run with: perl test_regexp_common.pl
use strict;
use warnings;

use Test::More;
use Regexp::Common;

# balanced
like('(a(b)c)', qr/^$RE{balanced}{-parens=>'()'}$/, 'balanced parens match');
unlike('(a(b)c', qr/^$RE{balanced}{-parens=>'()'}$/, 'unbalanced parens reject');

# numbers
like('3.14159',  qr/^$RE{num}{real}$/, 'real number match');
unlike('3.14.15', qr/^$RE{num}{real}$/, 'malformed real reject');
like('-42',      qr/^$RE{num}{int}$/,  'integer match');
like('DEADBEEF', qr/^$RE{num}{hex}$/,  'hex number match');

# comma-separated list (2017060201 default pattern allows empty elements)
like('a,b,c', qr/^$RE{list}$/, 'list match');

# delimited string
like('"hello, world"', qr/^$RE{delimited}{-delim=>'"'}$/, 'double-quoted delimited match');

# URI
like('http://example.com/path', qr/^$RE{URI}{HTTP}$/, 'HTTP URI match');
unlike('not a uri', qr/^$RE{URI}{HTTP}$/, 'non-URI reject');

# zip codes (2017060201 registers the US pattern as {zip}{US})
like('12345', qr/^$RE{zip}{US}$/, 'US zip5 match');

# IP addresses
like('192.168.0.1', qr/^$RE{net}{IPv4}$/, 'IPv4 match');
unlike('999.1.1.1', qr/^$RE{net}{IPv4}$/, 'bad IPv4 reject');

# pattern registry sanity: %RE is a tied hash whose EXISTS is not
# implemented on perl 5.42 — verify usability via eval instead.
ok(eval { $RE{num}{int}; 1 }, '%RE{num} usable');
ok(eval { $RE{URI}{HTTP}; 1 }, '%RE{URI} usable');

done_testing();
