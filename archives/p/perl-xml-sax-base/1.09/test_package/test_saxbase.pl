#!/usr/bin/env perl
# test_saxbase.pl — consumer test source for perl-xml-sax-base 1.09.
#
# REAL API check (R34) on the packaged XML::SAX::Base:
#   load + subclass (use base) + SAX event methods exist (can) +
#   construction. Events are dispatched via the Handler-callback /
#   SUPER:: chain (Base.pm _handle), so we verify the API surface
#   rather than driving the dispatch directly (upstream t/02simplefilter
#   uses $self->SUPER::start_element chaining).
# Usage: test_saxbase.pl <site-perl-dir>
use strict;
use warnings;

# @INC injection at compile time (use XML::SAX::Base is compile-time)
BEGIN {
    my $site = shift @ARGV
        or die "usage: test_saxbase.pl <site-perl-dir>\n";
    die "site-perl dir missing: $site\n" unless -d $site;
    unshift @INC, $site;
}

use XML::SAX::Base;

# subclass via the documented base mechanism (upstream usage)
{
    package MyHandler;
    use base 'XML::SAX::Base';
}

my $h = MyHandler->new;
die "MyHandler->new failed\n" unless $h;

# SAX event methods must be available (API surface — upstream events)
for my $m (qw(start_element end_element characters start_document
              end_document)) {
    die "XML::SAX::Base missing event method: $m\n"
        unless $h->can($m);
}

print "OK: perl-xml-sax-base 1.09 real API ok "
      . "(subclass + SAX event methods)\n";
exit 0;
