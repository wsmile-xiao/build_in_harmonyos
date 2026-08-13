#!/usr/bin/env perl
# test_specio_library_path_tiny.pl — Consumer perspective test
# for Specio::Library::Path::Tiny 0.05
# Tests: module loading, version, Path::Tiny type constraints,
#   coercions, type validation
use strict;
use warnings;

BEGIN {
    $ENV{SPECIO_IMPLEMENTATION} = 'PP';
}

my $pass = 0;
my $fail = 0;

sub ok_test {
    my ($cond, $desc) = @_;
    if ($cond) {
        print "  ok: $desc\n";
        $pass++;
    } else {
        print "  NOT OK: $desc\n";
        $fail++;
    }
}

# --- Test 1: Module loading ---
eval { require Specio::Library::Path::Tiny; Specio::Library::Path::Tiny->import };
ok_test(!$@, "Specio::Library::Path::Tiny module loads without error");
if ($@) {
    print "FATAL: Cannot load Specio::Library::Path::Tiny: $@\n";
    die "Module load failed";
}

# --- Test 2: Version check ---
my $version = $Specio::Library::Path::Tiny::VERSION;
ok_test(defined $version, "Module has a version defined");
ok_test($version eq '0.05', "Module version is 0.05 (got: $version)");

# --- Test 3: Path::Tiny availability ---
eval { require Path::Tiny };
ok_test(!$@, "Path::Tiny is available");
if ($@) {
    print "FATAL: Path::Tiny not available: $@\n";
    die "Path::Tiny required";
}

# --- Test 4: Type constraints available ---
# Import Specio::Declare to get t() function
eval { require Specio::Declare; Specio::Declare->import };
ok_test(!$@, "Specio::Declare loads (provides t() function)");

# Test Path type
my $path_type;
eval { $path_type = t('Path') };
ok_test(!$@ && defined $path_type, "t('Path') returns a type object");

# Test AbsPath type
my $abs_path_type;
eval { $abs_path_type = t('AbsPath') };
ok_test(!$@ && defined $abs_path_type, "t('AbsPath') returns a type object");

# Test RealPath type
my $real_path_type;
eval { $real_path_type = t('RealPath') };
ok_test(!$@ && defined $real_path_type, "t('RealPath') returns a type object");

# Test File type
my $file_type;
eval { $file_type = t('File') };
ok_test(!$@ && defined $file_type, "t('File') returns a type object");

# Test AbsFile type
my $abs_file_type;
eval { $abs_file_type = t('AbsFile') };
ok_test(!$@ && defined $abs_file_type, "t('AbsFile') returns a type object");

# Test RealFile type
my $real_file_type;
eval { $real_file_type = t('RealFile') };
ok_test(!$@ && defined $real_file_type, "t('RealFile') returns a type object");

# Test Dir type
my $dir_type;
eval { $dir_type = t('Dir') };
ok_test(!$@ && defined $dir_type, "t('Dir') returns a type object");

# Test AbsDir type
my $abs_dir_type;
eval { $abs_dir_type = t('AbsDir') };
ok_test(!$@ && defined $abs_dir_type, "t('AbsDir') returns a type object");

# Test RealDir type
my $real_dir_type;
eval { $real_dir_type = t('RealDir') };
ok_test(!$@ && defined $real_dir_type, "t('RealDir') returns a type object");

# --- Test 5: Type validation with Path::Tiny objects ---
use Path::Tiny qw(path);

# Create a test file and dir (E002: /tmp is read-only on OHOS, use $TMPDIR or $HOME)
my $tmpdir = $ENV{TMPDIR} || ($ENV{HOME} ? "$ENV{HOME}/tmp" : '.');
mkdir $tmpdir unless -d $tmpdir;
my $test_file = path("$tmpdir/specio_test_file_$$");
my $test_dir = path("$tmpdir/specio_test_dir_$$");

# Create the file
$test_file->touch;
# Create the dir
$test_dir->mkpath;

# Path type accepts Path::Tiny objects
ok_test($path_type->value_is_valid(path("foo")), "Path accepts relative Path::Tiny object");
ok_test($path_type->value_is_valid(path("/tmp")), "Path accepts absolute Path::Tiny object");
ok_test(!$path_type->value_is_valid("foo"), "Path rejects plain string");
ok_test(!$path_type->value_is_valid(42), "Path rejects integer");
ok_test(!$path_type->value_is_valid(undef), "Path rejects undef");
ok_test(!$path_type->value_is_valid({}), "Path rejects hashref");

# AbsPath type
ok_test($abs_path_type->value_is_valid(path("/tmp")), "AbsPath accepts absolute Path::Tiny");
ok_test(!$abs_path_type->value_is_valid(path("foo")), "AbsPath rejects relative Path::Tiny");
ok_test(!$abs_path_type->value_is_valid("foo"), "AbsPath rejects string");

# File type - needs actual file on disk
ok_test($file_type->value_is_valid($test_file), "File accepts existing file");
ok_test(!$file_type->value_is_valid($test_dir), "File rejects directory");
ok_test(!$file_type->value_is_valid(path("/nonexistent_file")), "File rejects non-existent file");

# Dir type - needs actual dir on disk
ok_test($dir_type->value_is_valid($test_dir), "Dir accepts existing directory");
ok_test(!$dir_type->value_is_valid($test_file), "Dir rejects file");
ok_test(!$dir_type->value_is_valid(path("/nonexistent_dir")), "Dir rejects non-existent dir");

# AbsDir type
ok_test($abs_dir_type->value_is_valid(path("/tmp")), "AbsDir accepts /tmp");
ok_test(!$abs_dir_type->value_is_valid(path("foo")), "AbsDir rejects relative path");

# AbsFile type
ok_test($abs_file_type->value_is_valid($test_file), "AbsFile accepts absolute existing file");
ok_test(!$abs_file_type->value_is_valid(path("foo")), "AbsFile rejects relative path");

# --- Test 6: Coercions ---
# Coerce string to Path
my $coerced;
eval { $coerced = $path_type->coerce_value("foo") };
ok_test(!$@ && defined $coerced, "Path coerces string to Path::Tiny");
ok_test($coerced && ref($coerced) eq 'Path::Tiny', "Coerced value is Path::Tiny object");
ok_test($coerced && "$coerced" eq "foo", "Coerced path value is 'foo'");

# Coerce arrayref to Path
eval { $coerced = $path_type->coerce_value([qw/foo bar/]) };
ok_test(!$@ && defined $coerced, "Path coerces arrayref to Path::Tiny");
ok_test($coerced && ref($coerced) eq 'Path::Tiny', "Coerced arrayref is Path::Tiny object");

# Coerce string to AbsPath
eval { $coerced = $abs_path_type->coerce_value("foo") };
ok_test(!$@ && defined $coerced, "AbsPath coerces string to absolute Path::Tiny");
ok_test($coerced && $coerced->is_absolute, "Coerced AbsPath is absolute");

# Coerce string to RealPath
eval { $coerced = $real_path_type->coerce_value($ENV{HOME}) };
ok_test(!$@ && defined $coerced, "RealPath coerces string to real Path::Tiny");
ok_test($coerced && $coerced->realpath eq $coerced, "Coerced RealPath is real path");

# --- Test 7: Message generators ---
eval {
    my $type = t('Path');
    $type->validate_or_die(42);
};
ok_test($@ && $@ =~ /is not an object/i, "Path message for integer mentions 'not an object'");

eval {
    my $type = t('AbsPath');
    $type->validate_or_die(path("foo"));
};
ok_test($@ && $@ =~ /not an absolute path/i, "AbsPath message for relative path mentions 'not absolute'");

# --- Cleanup ---
$test_file->remove if -f $test_file;
$test_dir->remove_tree if -d $test_dir;

# --- Summary ---
print "\n=== Test Summary ===\n";
print "Pass: $pass\n";
print "Fail: $fail\n";
if ($fail == 0) {
    print "Result: ALL TESTS PASSED\n";
    exit 0;
} else {
    print "Result: $fail TEST(S) FAILED\n";
    exit 1;
}
