#!/usr/bin/env perl
# test_xmllibxml.pl — consumer test source for perl-xml-libxml 2.0213 (L0c).
#
# REAL API check (R34) on the packaged XML::LibXML:
#   load_xml + findnodes (upstream t/ tests usage).
# Usage: test_xmllibxml.pl <site-perl-dir>
use strict;
use warnings;

# @INC injection at compile time (use XML::LibXML is compile-time)
BEGIN {
    my $site = shift @ARGV
        or die "usage: test_xmllibxml.pl <site-perl-dir>\n";
    die "site-perl dir missing: $site\n" unless -d $site;
    unshift @INC, $site;
}

use XML::LibXML;

# load_xml: parse XML from string
my $doc = XML::LibXML->load_xml(string => '<root><item id="1">a</item><item id="2">b</item></root>');
die "load_xml failed\n" unless $doc;

# findnodes: XPath query (upstream core usage)
my @items = $doc->findnodes('/root/item');
die "findnodes count mismatch: " . scalar(@items) . "\n" unless @items == 2;
die "findnodes text mismatch: " . $items[0]->textContent . "\n"
    unless $items[0]->textContent eq 'a';
my @ids = $doc->findnodes('/root/item/@id');
die "attribute query mismatch\n"
    unless @ids == 2 && $ids[1]->value eq '2';

print "OK: perl-xml-libxml 2.0213 real API ok (load_xml/findnodes)\n";
exit 0;
