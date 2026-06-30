use strict;
use warnings;
use Proc::ForkSafe;

# Test 1: module loads and has correct version
die 'VERSION mismatch' unless $Proc::ForkSafe::VERSION eq '0.001';
print "Test 1 PASS: module loaded, version 0.001\n";

# Test 2: wrap() creates a ForkSafe object
{
    package A;
    sub new { bless {}, shift }
    sub foo { 'foo' }
    sub bar { shift->{bar} //= 0; shift->{bar}++ }
}

my $a = Proc::ForkSafe->wrap(sub { A->new });
die 'wrap failed' unless ref($a) eq 'Proc::ForkSafe';
die 'missing pid' unless defined $a->{pid};
die 'missing obj' unless defined $a->{obj};
print "Test 2 PASS: wrap() creates ForkSafe object\n";

# Test 3: call() invokes methods on wrapped object
my $result = $a->call('foo');
die 'call returned wrong value' unless $result eq 'foo';
print "Test 3 PASS: call() invokes method correctly\n";

# Test 4: same PID, no reinitialization
my $pid_before = $a->{pid};
$a->call('foo');
die 'pid changed without fork' unless $a->{pid} == $pid_before;
print "Test 4 PASS: no reinit without fork\n";

# Test 5: fork-safe reinitialization
my $child = fork();
if (!defined $child) {
    print "Test 5 SKIP: fork() not available on this platform\n";
} elsif ($child == 0) {
    # In child: call() should detect PID change and reinitialize
    my $r = $a->call('foo');
    die 'call failed after fork' unless $r eq 'foo';
    die 'pid not updated after fork' unless $a->{pid} != $pid_before;
    print "Test 5 PASS: fork-safe reinit works\n";
    exit 0;
} else {
    waitpid($child, 0);
    die 'child failed' unless $? == 0;
    # Parent: pid should be unchanged
    die 'parent pid changed' unless $a->{pid} == $pid_before;
    print "Test 6 PASS: parent unchanged after fork\n";
}

# Test 7: destroy callback called after fork
my $destroy_called = 0;
my $b = Proc::ForkSafe->wrap(
    sub { A->new },
    sub { $destroy_called = 1 },
);
$b->call('foo');
die 'destroy called early' if $destroy_called;

my $child2 = fork();
if (!defined $child2) {
    print "Test 7 SKIP: fork() not available\n";
} elsif ($child2 == 0) {
    die 'destroy called before call' if $destroy_called;
    $b->call('foo');
    die 'destroy not called after fork' unless $destroy_called;
    print "Test 7 PASS: destroy callback works\n";
    exit 0;
} else {
    waitpid($child2, 0);
    die 'child2 failed' unless $? == 0;
}

print "ALL TESTS PASSED\n";
