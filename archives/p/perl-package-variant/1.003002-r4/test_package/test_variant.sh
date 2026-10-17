#!/bin/sh
# test_package/test_variant.sh — smoke test for Package::Variant (Perl module)
# Defines a variable package, creates variants via API, and verifies methods.
set -eu

PERL_LOCAL="$HOME/.cpan-deps"
mkdir -p "$PERL_LOCAL/src"
export PERL5LIB="${PERL5LIB:-}:${PERL_LOCAL}/lib/perl5"

# Install Perl runtime dependencies for Package::Variant with SHA256 verification
install_cpan_mod() {
    mod_test="$1" url="$2" dir="$3" sha256="$4"
    perl -M"$mod_test" -e 'exit 0' 2>/dev/null && return 0
    echo "[setup] installing $mod_test from CPAN..."
    cd "$PERL_LOCAL/src"
    python3 -c "import urllib.request; urllib.request.urlretrieve('$url', '$dir.tar.gz')"
    echo "$sha256  $dir.tar.gz" | sha256sum -c
    tar xzf "$dir.tar.gz"
    cd "$dir"
    perl Makefile.PL INSTALL_BASE="$PERL_LOCAL" && make && make install 2>&1
}

install_cpan_mod "Module::Runtime" \
    "https://cpan.metacpan.org/authors/id/Z/ZE/ZEFRAM/Module-Runtime-0.016.tar.gz" \
    "Module-Runtime-0.016" \
    "68302ec646833547d410be28e09676db75006f4aa58a11f3bdb44ffe99f0f024"

install_cpan_mod "Import::Into" \
    "https://cpan.metacpan.org/authors/id/H/HA/HAARG/Import-Into-1.002005.tar.gz" \
    "Import-Into-1.002005" \
    "bd9e77a3fb662b40b43b18d3280cd352edf9fad8d94283e518181cc1ce9f0567"

install_cpan_mod "strictures" \
    "https://cpan.metacpan.org/authors/id/H/HA/HAARG/strictures-2.000006.tar.gz" \
    "strictures-2.000006" \
    "09d57974a6d1b2380c802870fed471108f51170da81458e2751859f2714f8d57"

# Define a variable package and exercise Package::Variant API
perl -e '
package MyTestVariant;
use Package::Variant;

sub make_variant {
    my ($class, $target) = @_;
    install("hello", sub { return "hello from $target" });
}

package main;

my $ver = $Package::Variant::VERSION;
print "version: $ver\n";
die "version mismatch" unless $ver eq "1.003002";

my $variant = MyTestVariant->build_variant();
print "build_variant: $variant\n";
die "unexpected variant name" unless $variant =~ /^MyTestVariant::_Variant_/;

my $result = $variant->hello();
print "hello(): $result\n";
die "unexpected result" unless $result eq "hello from $variant";

my $variant2 = MyTestVariant->build_variant();
print "variant2: $variant2\n";
die "variants should differ" unless $variant ne $variant2;

print "ALL_TESTS_PASS\n";
'
