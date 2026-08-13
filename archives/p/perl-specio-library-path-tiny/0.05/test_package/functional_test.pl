#!/usr/bin/env perl
# -*- perl -*-
#
# Functional Test: Specio::Library::Path::Tiny 0.05 on HarmonyOS
# Coverage: module loading, type constraints, coercion, error handling,
#           filesystem operations, HarmonyOS-specific scenarios
#
use strict;
use warnings;
use utf8;
binmode(STDOUT, ':utf8');
binmode(STDERR, ':utf8');
BEGIN { $ENV{SPECIO_IMPLEMENTATION} = 'PP' unless $ENV{SPECIO_IMPLEMENTATION}; }
use Specio::Library::Path::Tiny;
use Path::Tiny qw(path);
use Scalar::Util qw(blessed);

my $pass = 0;
my $fail = 0;
my $test_num = 0;

sub ok_test {
    my ($cond, $desc) = @_;
    $test_num++;
    if ($cond) {
        print "  ok: $desc\n";
        $pass++;
    } else {
        print "  FAIL: $desc\n";
        $fail++;
    }
}

sub section {
    my ($name) = @_;
    print "\n--- $name ---\n";
}

# ============================================================
# 1. Module loading and environment verification
# ============================================================
section("1. Module loading and environment verification");

ok_test(eval { require Specio::Library::Path::Tiny; 1 },
    "Specio::Library::Path::Tiny module loads successfully");
ok_test(defined $Specio::Library::Path::Tiny::VERSION,
    "Module version is defined");
ok_test($Specio::Library::Path::Tiny::VERSION eq '0.05',
    "Module version = 0.05 (got: $Specio::Library::Path::Tiny::VERSION)");

# Verify SPECIO_IMPLEMENTATION=PP
my $specio_impl = $ENV{SPECIO_IMPLEMENTATION} || '';
ok_test($specio_impl eq 'PP',
    "SPECIO_IMPLEMENTATION=PP is set (got: '$specio_impl')");

# Verify Path::Tiny is available
ok_test(eval { require Path::Tiny; 1 }, "Path::Tiny module is available");
ok_test($Path::Tiny::VERSION >= 0.087,
    "Path::Tiny version >= 0.087 (got: $Path::Tiny::VERSION)");

# ============================================================
# 2. All 9 type constraint object creation
# ============================================================
section("2. Type constraint object creation");

my @types = qw(Path AbsPath RealPath File AbsFile RealFile Dir AbsDir RealDir);
for my $name (@types) {
    my $type = eval { t($name) };
    ok_test(defined $type, "t('$name') returns type object");
    ok_test($type && ref($type) && blessed($type),
        "t('$name') returns blessed Specio type object");
}

# ============================================================
# 3. Type validation: accept valid values
# ============================================================
section("3. Type validation - accept valid values");

# Prepare test files and directories
my $tmpdir = $ENV{TMPDIR} || ($ENV{HOME} ? "$ENV{HOME}/tmp" : '.');
mkdir $tmpdir unless -d $tmpdir;
my $test_base = Path::Tiny->new("$tmpdir/func_test_$$");
$test_base->remove_tree if -d $test_base;
$test_base->mkpath;

my $test_file = $test_base->child('testfile.txt');
$test_file->spew("test content\n");

my $test_dir = $test_base->child('testdir');
$test_dir->mkpath;

my $symlink_file = $test_base->child('symlinkfile.txt');
eval { symlink $test_file, $symlink_file };
my $has_symlink = !$@ && -l $symlink_file;

# Path: accept any Path::Tiny object
ok_test(t('Path')->value_is_valid(path("foo")),
    "Path accepts relative path object");
ok_test(t('Path')->value_is_valid(path("/data/service")),
    "Path accepts absolute path object");
ok_test(t('Path')->value_is_valid($test_file),
    "Path accepts file object");
ok_test(t('Path')->value_is_valid($test_dir),
    "Path accepts directory object");

# AbsPath: accept absolute path
ok_test(t('AbsPath')->value_is_valid(path("/data/service")),
    "AbsPath accepts absolute path");
ok_test(t('AbsPath')->value_is_valid($test_file),
    "AbsPath accepts absolute file path");

# RealPath: accept real path (no symlinks)
ok_test(t('RealPath')->value_is_valid($test_file),
    "RealPath accepts real file path");
ok_test(t('RealPath')->value_is_valid($test_dir),
    "RealPath accepts real directory path");

# File: accept existing file
ok_test(t('File')->value_is_valid($test_file),
    "File accepts existing file");
ok_test(!t('File')->value_is_valid($test_dir),
    "File rejects directory");

# AbsFile: accept absolute file
ok_test(t('AbsFile')->value_is_valid($test_file),
    "AbsFile accepts absolute file path");
ok_test(!t('AbsFile')->value_is_valid(path("foo")),
    "AbsFile rejects relative file path");

# RealFile: accept real file
ok_test(t('RealFile')->value_is_valid($test_file),
    "RealFile accepts real file");

# Dir: accept existing directory
ok_test(t('Dir')->value_is_valid($test_dir),
    "Dir accepts existing directory");
ok_test(!t('Dir')->value_is_valid($test_file),
    "Dir rejects file");

# AbsDir: accept absolute directory
ok_test(t('AbsDir')->value_is_valid($test_dir),
    "AbsDir accepts absolute directory path");

# RealDir: accept real directory
ok_test(t('RealDir')->value_is_valid($test_dir),
    "RealDir accepts real directory");

# ============================================================
# 4. Type validation: reject invalid values
# ============================================================
section("4. Type validation - reject invalid values");

# Reject non-Path::Tiny objects
for my $type_name (@types) {
    my $type = t($type_name);
    ok_test(!$type->value_is_valid("plain string"),
        "$type_name rejects plain string");
    ok_test(!$type->value_is_valid(42),
        "$type_name rejects integer");
    ok_test(!$type->value_is_valid(undef),
        "$type_name rejects undef");
    ok_test(!$type->value_is_valid({}),
        "$type_name rejects hashref");
    ok_test(!$type->value_is_valid([]),
        "$type_name rejects arrayref");
}

# AbsPath rejects relative path
ok_test(!t('AbsPath')->value_is_valid(path("foo")),
    "AbsPath rejects relative path");

# AbsDir rejects relative directory
ok_test(!t('AbsDir')->value_is_valid(path("foo")),
    "AbsDir rejects relative directory");

# AbsFile rejects relative file
ok_test(!t('AbsFile')->value_is_valid(path("foo")),
    "AbsFile rejects relative file");

# ============================================================
# 5. Coercion
# ============================================================
section("5. Coercion");

# String -> Path
my $coerced;
eval { $coerced = t('Path')->coerce_value("foo/bar") };
ok_test(!$@ && defined $coerced, "Path coerces string successfully");
ok_test($coerced && ref($coerced) eq 'Path::Tiny', "Coerced value is Path::Tiny object");
ok_test($coerced && "$coerced" eq "foo/bar", "Coerced path value is correct");

# Arrayref -> Path
eval { $coerced = t('Path')->coerce_value([qw(foo bar baz)]) };
ok_test(!$@ && defined $coerced, "Path coerces arrayref successfully");
ok_test($coerced && ref($coerced) eq 'Path::Tiny', "Arrayref coerced to Path::Tiny");
ok_test($coerced && "$coerced" =~ m{foo.*bar.*baz}, "Arrayref coerced path is correct");

# String -> AbsPath (auto-absolute)
eval { $coerced = t('AbsPath')->coerce_value("foo") };
ok_test(!$@ && defined $coerced, "AbsPath coerces string successfully");
ok_test($coerced && $coerced->is_absolute, "AbsPath coerced to absolute path");

# String -> RealPath
eval { $coerced = t('RealPath')->coerce_value($test_file) };
ok_test(!$@ && defined $coerced, "RealPath coerces string successfully");
ok_test($coerced && $coerced->realpath eq $coerced, "RealPath coerced to real path");

# String -> File
eval { $coerced = t('File')->coerce_value("$test_file") };
ok_test(!$@ && defined $coerced, "File coerces string successfully");
ok_test($coerced && ref($coerced) eq 'Path::Tiny', "File coerced to Path::Tiny");

# String -> Dir
eval { $coerced = t('Dir')->coerce_value("$test_dir") };
ok_test(!$@ && defined $coerced, "Dir coerces string successfully");
ok_test($coerced && ref($coerced) eq 'Path::Tiny', "Dir coerced to Path::Tiny");

# ============================================================
# 6. Error message generation
# ============================================================
section("6. Error message generation");

# Path error message for integer
eval {
    my $type = t('Path');
    $type->validate_or_die(42);
};
ok_test($@ && $@ =~ /not an object/i,
    "Path error message contains 'not an object'");

# AbsPath error message for relative path
eval {
    my $type = t('AbsPath');
    $type->validate_or_die(path("foo"));
};
ok_test($@ && $@ =~ /not an absolute path/i,
    "AbsPath error message contains 'not absolute'");

# File error for directory
eval {
    my $type = t('File');
    $type->validate_or_die($test_dir);
};
ok_test($@, "File throws exception for directory");

# Dir error for file
eval {
    my $type = t('Dir');
    $type->validate_or_die($test_file);
};
ok_test($@, "Dir throws exception for file");

# ============================================================
# 7. HarmonyOS platform specific scenarios
# ============================================================
section("7. HarmonyOS platform specific scenarios");

# 7.1 HMDFS path
my $hmdfs_path = path("/storage/Users/currentUser");
ok_test(t('AbsPath')->value_is_valid($hmdfs_path),
    "AbsPath accepts HMDFS path /storage/Users/currentUser");
ok_test(t('AbsDir')->value_is_valid($hmdfs_path),
    "AbsDir accepts HMDFS user directory");
ok_test(t('RealDir')->value_is_valid($hmdfs_path),
    "RealDir accepts HMDFS real directory");

# 7.2 System service path
my $svc_path = path("/data/service/hnp");
ok_test(t('AbsDir')->value_is_valid($svc_path),
    "AbsDir accepts system service path /data/service/hnp");

# 7.3 Perl installation path
my $perl_path = path("/data/service/hnp/perl.org/perl_5.42.0");
ok_test(t('AbsDir')->value_is_valid($perl_path),
    "AbsDir accepts Perl installation path");

# 7.4 Read-only filesystem path (/tmp is read-only on OHOS)
my $ro_path = path("/tmp");
ok_test(t('AbsDir')->value_is_valid($ro_path),
    "Read-only /tmp path passes AbsDir validation");

# 7.5 Deep nested path (8 levels)
my $deep_path = $test_base->child(qw(a b c d e f g h));
$deep_path->mkpath;
ok_test(t('Dir')->value_is_valid($deep_path),
    "Dir accepts deep nested directory (8 levels)");
ok_test(t('AbsDir')->value_is_valid($deep_path),
    "AbsDir accepts deep nested absolute directory");

# 7.6 Unicode filename
my $unicode_file = $test_base->child("\x{6d4b}\x{8bd5}\x{6587}\x{4ef6}.txt");
$unicode_file->spew("unicode test\n");
ok_test(t('File')->value_is_valid($unicode_file),
    "File accepts Unicode filename");
ok_test(t('AbsFile')->value_is_valid($unicode_file),
    "AbsFile accepts Unicode filename");

# 7.7 Symlink handling (if supported)
if ($has_symlink) {
    ok_test(t('Path')->value_is_valid($symlink_file),
        "Path accepts symlink file");
    ok_test(!t('RealPath')->value_is_valid($symlink_file),
        "RealPath rejects symlink (realpath != self)");
} else {
    print "  (skip) Symlinks not available\n";
}

# ============================================================
# 8. Real-world application scenario simulation
# ============================================================
section("8. Real-world application scenario simulation");

# Simulate: subroutine with type constraint
sub process_file {
    my ($file_arg) = @_;
    my $type = t('File');
    my $file = $type->coerce_value($file_arg);
    return $file->slurp;
}

my $content = eval { process_file("$test_file") };
ok_test(!$@ && defined $content && $content =~ /test content/,
    "Type-constrained subroutine processes file argument correctly");

# Simulate: path concatenation
my $base = t('AbsDir')->coerce_value($test_dir);
my $child = $base->child('subdir', 'file.txt');
ok_test($child->is_absolute, "Path concatenation preserves absolute path");
ok_test("$child" =~ m{subdir.*file\.txt}, "Path concatenation result is correct");

# Simulate: directory iteration
my $iter = $test_base->iterator;
my @children;
while (my $f = $iter->()) {
    push @children, $f;
}
ok_test(scalar(@children) > 0, "Directory iteration returns children");
my @dir_children = grep { $_->is_dir } @children;
my @file_children = grep { $_->is_file } @children;
ok_test(scalar(@dir_children) > 0, "Directory iteration identifies subdirectories");
ok_test(scalar(@file_children) > 0, "Directory iteration identifies subfiles");

# Simulate: file read/write operations
my $rw_file = $test_base->child('readwrite.txt');
$rw_file->spew("line1\nline2\nline3\n");
my @lines = $rw_file->lines;
ok_test(scalar(@lines) == 3, "File write then read returns correct line count");
ok_test($lines[0] eq "line1\n", "File content first line is correct");

# Simulate: temp directory creation
my $temp = Path::Tiny->tempdir("funcXXXX", DIR => $tmpdir);
ok_test(-d $temp, "Temp directory creation succeeds");
ok_test(t('RealDir')->value_is_valid($temp),
    "Temp directory passes RealDir validation");

# ============================================================
# 9. Inline constraint verification
# ============================================================
section("9. Inline constraint verification");

for my $name (@types) {
    my $type = t($name);
    my $inline_code = eval { $type->inline_check('$value') };
    ok_test(defined $inline_code,
        "$name inline_check generates inline code");
}

# ============================================================
# 10. Type relationship verification
# ============================================================
section("10. Type relationship verification");

# All 8 types are direct subtypes of Path (flat hierarchy per source code)
ok_test(t('AbsPath')->is_a_type_of(t('Path')),
    "AbsPath is a subtype of Path");
ok_test(t('RealPath')->is_a_type_of(t('Path')),
    "RealPath is a subtype of Path");
ok_test(t('File')->is_a_type_of(t('Path')),
    "File is a subtype of Path");
ok_test(t('Dir')->is_a_type_of(t('Path')),
    "Dir is a subtype of Path");
ok_test(t('AbsFile')->is_a_type_of(t('Path')),
    "AbsFile is a subtype of Path");
ok_test(t('AbsDir')->is_a_type_of(t('Path')),
    "AbsDir is a subtype of Path");
ok_test(t('RealFile')->is_a_type_of(t('Path')),
    "RealFile is a subtype of Path");
ok_test(t('RealDir')->is_a_type_of(t('Path')),
    "RealDir is a subtype of Path");

# ============================================================
# Cleanup
# ============================================================
$test_base->remove_tree if -d $test_base;
$temp->remove_tree if -d $temp;

# ============================================================
# Summary
# ============================================================
print "\n=== Functional Test Summary ===\n";
print "Total: $test_num\n";
print "Pass:  $pass\n";
print "Fail:  $fail\n";
if ($fail == 0) {
    print "Result: ALL TESTS PASSED\n";
    exit 0;
} else {
    print "Result: $fail TEST(S) FAILED\n";
    exit 1;
}
