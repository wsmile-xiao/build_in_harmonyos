use strict;
use warnings;
use POSIX qw(:sys_wait_h);
use Proc::WaitStat qw(waitstat waitstat_reuse waitstat_die close_die);

# Test 1: module loaded and version correct
die 'VERSION mismatch' unless $Proc::WaitStat::VERSION eq '1.00';
print "Test 1 PASS: module loaded, version 1.00\n";

# Test 2: waitstat() with normal exit status
# Construct a wait status for exit code 0 (WIFEXITED=1, WEXITSTATUS=0)
my $status_0 = 0;  # exit 0 => status 0
my $desc_0 = waitstat($status_0);
die "waitstat(0) should return '0', got '$desc_0'" unless $desc_0 eq '0';
print "Test 2 PASS: waitstat(0) = '$desc_0'\n";

# Test 3: waitstat() with non-zero exit status
my $status_42 = 42 << 8;  # WEXITSTATUS=42 => status = 42*256
my $desc_42 = waitstat($status_42);
die "waitstat(42<<8) should return '42', got '$desc_42'" unless $desc_42 eq '42';
print "Test 3 PASS: waitstat(42<<8) = '$desc_42'\n";

# Test 4: waitstat_reuse() with normal exit
my $reuse_0 = waitstat_reuse($status_0);
die "waitstat_reuse(0) should return 0, got $reuse_0" unless $reuse_0 == 0;
print "Test 4 PASS: waitstat_reuse(0) = $reuse_0\n";

# Test 5: waitstat_reuse() with non-zero exit
my $reuse_42 = waitstat_reuse($status_42);
die "waitstat_reuse(42<<8) should return 42, got $reuse_42" unless $reuse_42 == 42;
print "Test 5 PASS: waitstat_reuse(42<<8) = $reuse_42\n";

# Test 6: waitstat_die() with zero status (should not die)
eval { waitstat_die($status_0, 'test-program'); };
die "waitstat_die(0) should not die: $@" if $@;
print "Test 6 PASS: waitstat_die(0) did not die\n";

# Test 7: waitstat_die() with non-zero status (should die)
eval { waitstat_die($status_42, 'test-program'); };
die "waitstat_die(42<<8) should die" unless $@;
print "Test 7 PASS: waitstat_die(42<<8) died as expected: $@";

# Test 8: fork + waitpid + waitstat integration test
my $child = fork();
if (!defined $child) {
    print "Test 8 SKIP: fork() not available on this platform\n";
} elsif ($child == 0) {
    exit(7);
} else {
    my $pid = waitpid($child, 0);
    my $desc = waitstat($?);
    my $reuse = waitstat_reuse($?);
    if ($pid == $child && $desc eq '7' && $reuse == 7) {
        print "Test 8 PASS: fork+waitpid+waitstat integration: exit=7, desc='$desc', reuse=$reuse\n";
    } else {
        die "Test 8 FAIL: pid=$pid (expected $child), desc='$desc', reuse=$reuse";
    }
}

# Test 9: close_die() with a pipe to a successful command
my $fh;
my $opened = open($fh, '-|', 'echo', 'hello');
if ($opened) {
    my $line = <$fh>;
    eval { close_die($fh, 'echo'); };
    die "close_die should not die for successful command: $@" if $@;
    print "Test 9 PASS: close_die(echo) did not die\n";
} else {
    print "Test 9 SKIP: cannot open pipe to echo\n";
}

print "ALL TESTS PASSED\n";
