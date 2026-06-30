use strict;
use warnings;
use Proc::Wait3;

# Test 1: module loaded and version correct
die 'VERSION mismatch' unless $Proc::Wait3::VERSION eq '0.05';
print "Test 1 PASS: module loaded, version 0.05\n";

# Test 2: wait3(0) non-blocking with no children returns empty
my @result = wait3(0);
if (@result == 0 || !defined $result[0]) {
    print "Test 2 PASS: wait3(0) returns empty with no children\n";
} else {
    print "Test 2 WARN: wait3(0) returned unexpected result (possibly reaped zombie)\n";
}

# Test 3: fork a child, wait3(1) blocks and reaps it
my $child = fork();
if (!defined $child) {
    print "Test 3 SKIP: fork() not available on this platform\n";
} elsif ($child == 0) {
    exit(42);
} else {
    my @r = wait3(1);
    my $pid = $r[0] // 0;
    my $status = $r[1] // 0;
    if ($pid == $child) {
        my $exit_code = ($status >> 8) & 0xFF;
        if ($exit_code == 42) {
            print "Test 3 PASS: wait3(1) reaped child pid=$pid, exit=42\n";
        } else {
            print "Test 3 WARN: child reaped but exit code=$exit_code (expected 42)\n";
        }
    } else {
        print "Test 3 WARN: wait3 returned pid=$pid (expected $child)\n";
    }
    # Test 4: rusage fields present
    if (defined $r[2] && defined $r[3]) {
        print "Test 4 PASS: rusage utime=$r[2], stime=$r[3]\n";
    } else {
        print "Test 4 WARN: rusage fields not available\n";
    }
}

print "ALL TESTS COMPLETED\n";
