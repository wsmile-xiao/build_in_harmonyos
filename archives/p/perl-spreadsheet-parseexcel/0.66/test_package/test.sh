#!/bin/sh
# test_package/test.sh — smoke test for perl-spreadsheet-parseexcel
# Usage: test.sh <perl_lib_path>
#
# Tests Spreadsheet::ParseExcel::Utility module which has no external
# dependencies (unlike the main ParseExcel module which requires
# OLE::Storage_Lite, Crypt::RC4, Digest::Perl::MD5).
set -eu

PERL_LIB="${1:?Usage: test.sh <perl_lib_path>}"

echo "[test] Loading Spreadsheet::ParseExcel::Utility (no external deps)..."
perl -I "$PERL_LIB" -MSpreadsheet::ParseExcel::Utility -e '
    # Test 1: col2int — convert column name to number (0-indexed)
    my $col = Spreadsheet::ParseExcel::Utility::col2int("AB");
    print "  col2int(\"AB\") = $col\n";
    die "Expected 27, got $col" unless $col == 27;

    # Test 2: int2col — convert number to column name
    my $name = Spreadsheet::ParseExcel::Utility::int2col(27);
    print "  int2col(27) = $name\n";
    die "Expected AB, got $name" unless $name eq "AB";

    # Test 3: Round-trip verification
    my $rt = Spreadsheet::ParseExcel::Utility::col2int(
        Spreadsheet::ParseExcel::Utility::int2col(52)
    );
    print "  round-trip(52) = $rt\n";
    die "Expected 52, got $rt" unless $rt == 52;

    print "  Utility functions: PASS\n";
'

echo "[test] Checking main module file integrity..."
perl -I "$PERL_LIB" -e '
    # Extract VERSION from ParseExcel.pm without loading it
    # (loading requires OLE::Storage_Lite which is a runtime dep)
    my $pm_file;
    for my $dir (@INC) {
        my $path = "$dir/Spreadsheet/ParseExcel.pm";
        if (-f $path) { $pm_file = $path; last; }
    }
    die "ParseExcel.pm not found in \@INC" unless $pm_file;
    open(my $fh, "<", $pm_file) or die "Cannot open $pm_file: $!";
    my $content = do { local $/; <$fh> };
    close($fh);
    my ($version) = $content =~ /our\s+\$VERSION\s*=\s*[\x27"]([0-9.]+)/;
    print "  ParseExcel VERSION: $version\n";
    die "VERSION not found or wrong" unless $version && $version eq "0.66";
    print "  Module integrity: PASS\n";
'

echo "✅ All smoke tests passed"
