#!/bin/sh
# test_spreadsheet_xlsx.sh — Test script for perl-spreadsheet-xlsx 0.18
# Verifies that Spreadsheet::XLSX module files are correctly packaged.
# Called from test_package/conanfile.py test() method.
# Usage: sh test_spreadsheet_xlsx.sh <package_folder>
#
# Note: Full `use Spreadsheet::XLSX` test requires runtime dependencies
# (Spreadsheet::ParseExcel, Archive::Zip) which may not be available on
# all CI workers. This test follows the file-based verification pattern
# (same as perl-parallel-prefork) to ensure portability.

set -e

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "FAIL: package folder argument required"
    exit 1
fi

# Find Perl interpreter dynamically (R33: no hardcoded paths)
PERL=$(command -v perl 2>/dev/null || echo "")
if [ -z "$PERL" ]; then
    echo "FAIL: perl not found in PATH"
    exit 1
fi

# Find XLSX.pm in the package (avoid hardcoding Perl version)
XLSX_PM=$(find "$PKG_FOLDER" -name "XLSX.pm" -path "*/Spreadsheet/XLSX.pm" 2>/dev/null | head -1)
if [ -z "$XLSX_PM" ]; then
    echo "FAIL: Spreadsheet/XLSX.pm not found in package: $PKG_FOLDER"
    exit 1
fi

# Derive lib directory from .pm path (XLSX.pm is at <lib>/Spreadsheet/XLSX.pm)
SITE_LIB=$(dirname "$(dirname "$XLSX_PM")")

# Verify Fmt2007.pm exists
FMT2007_PM="${SITE_LIB}/Spreadsheet/XLSX/Fmt2007.pm"
if [ ! -f "$FMT2007_PM" ]; then
    echo "FAIL: Spreadsheet/XLSX/Fmt2007.pm not found: $FMT2007_PM"
    exit 1
fi

# Verify Utility2007.pm exists
UTIL2007_PM="${SITE_LIB}/Spreadsheet/XLSX/Utility2007.pm"
if [ ! -f "$UTIL2007_PM" ]; then
    echo "FAIL: Spreadsheet/XLSX/Utility2007.pm not found: $UTIL2007_PM"
    exit 1
fi

# Verify module version from XLSX.pm file content (no module loading required)
$PERL -e '
    my $file = $ARGV[0];
    open(my $fh, "<", $file) or die "Cannot open $file: $!";
    my $content = do { local $/; <$fh> };
    close($fh);
    die "version not found in XLSX.pm" unless $content =~ /\$VERSION\s*=\s*[\x27"]0\.18[\x27"]/;
    print "Spreadsheet::XLSX v0.18 verified OK\n";
' "$XLSX_PM"

# Verify Fmt2007.pm has content (not empty/sabotaged)
FMT_SIZE=$(wc -c < "$FMT2007_PM" 2>/dev/null || echo 0)
if [ "$FMT_SIZE" -lt 100 ]; then
    echo "FAIL: Fmt2007.pm is suspiciously small ($FMT_SIZE bytes)"
    exit 1
fi

# Verify Utility2007.pm has content (not empty/sabotaged)
UTIL_SIZE=$(wc -c < "$UTIL2007_PM" 2>/dev/null || echo 0)
if [ "$UTIL_SIZE" -lt 100 ]; then
    echo "FAIL: Utility2007.pm is suspiciously small ($UTIL_SIZE bytes)"
    exit 1
fi

# Verify XLSX.pm declares Spreadsheet::ParseExcel as base (dependency check)
if ! grep -q "Spreadsheet::ParseExcel" "$XLSX_PM" 2>/dev/null; then
    echo "FAIL: XLSX.pm does not reference Spreadsheet::ParseExcel"
    exit 1
fi

# Optionally run functional test if runtime dependencies are available
# Build PERL5LIB dynamically for the functional test
EXISTING_PERL5LIB="${PERL5LIB:-}"
SYSTEM_PERL5LIB=$($PERL -e 'print join(":", @INC)' 2>/dev/null || echo "")
PERL_VERSION=$($PERL -e 'print substr($^V, 1)' 2>/dev/null || echo "")
USER_SITE_PERL="$HOME/usr/local/lib/site_perl/${PERL_VERSION}"
USER_LIB_PERL="$HOME/usr/local/lib/perl5"
FUNC_PERL5LIB="${SITE_LIB}:${SYSTEM_PERL5LIB}"
if [ -n "$PERL_VERSION" ] && [ -d "$USER_SITE_PERL" ]; then
    FUNC_PERL5LIB="${FUNC_PERL5LIB}:${USER_SITE_PERL}"
fi
if [ -d "$USER_LIB_PERL" ]; then
    FUNC_PERL5LIB="${FUNC_PERL5LIB}:${USER_LIB_PERL}"
fi
if [ -n "$EXISTING_PERL5LIB" ]; then
    FUNC_PERL5LIB="${FUNC_PERL5LIB}:${EXISTING_PERL5LIB}"
fi

# Check if runtime dependencies are available (Spreadsheet::ParseExcel, Archive::Zip)
DEPS_AVAILABLE=no
if PERL5LIB="$FUNC_PERL5LIB" $PERL -e 'use Spreadsheet::ParseExcel; use Archive::Zip;' 2>/dev/null; then
    DEPS_AVAILABLE=yes
fi

if [ "$DEPS_AVAILABLE" = "yes" ]; then
    # Dependencies available — run functional smoke test
    echo "INFO: Runtime dependencies available, running functional test..."
    TMPDIR="${TMPDIR:-$HOME/tmp}"
    mkdir -p "$TMPDIR"
    TMPFILE="${TMPDIR}/test_xlsx_$$.xlsx"
    TEST_SCRIPT="${TMPDIR}/test_spreadsheet_xlsx_$$.pl"
    cat > "$TEST_SCRIPT" <<'PERLEOF'
use strict;
use warnings;
use Spreadsheet::XLSX;
my $version = $Spreadsheet::XLSX::VERSION;
die "Test failed: VERSION not defined" unless defined $version;
die "Test failed: expected version 0.18, got $version" unless $version eq '0.18';
use Archive::Zip;
my $tmpfile = shift @ARGV;
my $zip = Archive::Zip->new();
$zip->addString(<<'CT', '[Content_Types].xml');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
CT
$zip->addString(<<'RELS', '_rels/.rels');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
RELS
$zip->addString(<<'WB', 'xl/workbook.xml');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>
<sheet name="TestSheet" sheetId="1" r:id="rId1"/>
</sheets>
</workbook>
WB
$zip->addString(<<'WBRELS', 'xl/_rels/workbook.xml.rels');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
WBRELS
$zip->addString(<<'SHEET', 'xl/worksheets/sheet1.xml');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
<row r="1">
<c r="A1" t="str"><v>Hello</v></c>
<c r="B1" t="str"><v>World</v></c>
</row>
</sheetData>
</worksheet>
SHEET
unless ($zip->writeToFileNamed($tmpfile) == Archive::Zip::AZ_OK) {
    die "Failed to write test XLSX file";
}
my $excel = Spreadsheet::XLSX->new($tmpfile);
die "Test failed: no worksheets" unless $excel->{Worksheet} && @{$excel->{Worksheet}} > 0;
my $sheet = $excel->{Worksheet}[0];
die "Test failed: sheet name mismatch" unless $sheet->{Name} eq 'TestSheet';
unlink $tmpfile;
print "OK: Spreadsheet::XLSX functional smoke test passed\n";
PERLEOF
    # set -e will catch failures here (not inside &&/|| chain)
    PERL5LIB="$FUNC_PERL5LIB" $PERL "$TEST_SCRIPT" "$TMPFILE"
    rm -f "$TEST_SCRIPT" "$TMPFILE"
else
    echo "INFO: Runtime dependencies (Spreadsheet::ParseExcel, Archive::Zip) not available — skipping functional test"
fi

echo "test perl-spreadsheet-xlsx 0.18: OK"
