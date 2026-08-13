#!/usr/bin/env perl
use strict;
use warnings;
use Package::Anon;

# Basic test: create an anonymous package
my $stash = Package::Anon->new;
$stash->add_method(get_answer => sub { return 42; });

my $obj = $stash->bless({});
my $answer = $obj->get_answer();

die "Test failed: expected 42, got $answer" unless $answer == 42;
print "test perl-package-anon 0.05-r16: OK (answer=$answer)\n";
