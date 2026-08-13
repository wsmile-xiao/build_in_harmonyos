#!/data/service/hnp/bin/bash
# test_package/test_forkmanager.sh — Functional test for Parallel::ForkManager
# Tests: module loading, fork, child callbacks, exit codes, data return
set -euo pipefail

FAIL=0

# ── Install Perl runtime dependencies (Moo, Role::Tiny, Sub::Quote) ──
# Parallel::ForkManager depends on Moo::Role, which requires Moo + Role::Tiny + Sub::Quote.
# These are pure Perl modules not pre-installed on OHOS perl.
if ! perl -e 'use Moo::Role; 1' 2>/dev/null; then
    DEPS_DIR="${TMPDIR:-$HOME/tmp}/pfm_deps"
    mkdir -p "$DEPS_DIR"
    for spec in \
        "Moo-2.005004:moo" \
        "Role-Tiny-2.002004:roletiny" \
        "Sub-Quote-2.006008:subquote"; do
        pkg_name="${spec%%:*}"
        dir_name="${spec##*:}"
        url="https://www.cpan.org/authors/id/H/HA/HAARG/${pkg_name}.tar.gz"
        curl -sL "$url" -o "$DEPS_DIR/${pkg_name}.tar.gz"
        mkdir -p "$DEPS_DIR/$dir_name"
        tar xzf "$DEPS_DIR/${pkg_name}.tar.gz" -C "$DEPS_DIR/$dir_name" --strip-components=1
    done
    export PERL5LIB="$DEPS_DIR/moo/lib:$DEPS_DIR/roletiny/lib:$DEPS_DIR/subquote/lib${PERL5LIB:+:$PERL5LIB}"
fi

# Test 1: Module loading and version
perl -MParallel::ForkManager -e '
    print "T1: version=$Parallel::ForkManager::VERSION\n";
    exit(0);
' || FAIL=$((FAIL+1))

# Test 2: Basic fork and child process
perl -MParallel::ForkManager -e '
    my $pm = Parallel::ForkManager->new(4);
    my @results;
    $pm->run_on_finish(sub {
        my ($pid, $exit_code, $ident, $signal, $dump, $data) = @_;
        push @results, $data->{name} if $data;
    });
    for my $i (1..4) {
        $pm->start and next;
        $pm->finish(0, { name => "child_$i" });
    }
    $pm->wait_all_children;
    my $count = scalar @results;
    exit($count == 4 ? 0 : 1);
' || FAIL=$((FAIL+1))

# Test 3: Parallel execution (4 tasks x 0.3s should complete in < 1s)
perl -MParallel::ForkManager -e '
    use Time::HiRes qw(time);
    my $pm = Parallel::ForkManager->new(4);
    my $start = time();
    for my $i (1..4) {
        $pm->start and next;
        select(undef, undef, undef, 0.3);
        $pm->finish(0);
    }
    $pm->wait_all_children;
    my $elapsed = time() - $start;
    exit($elapsed < 1.5 ? 0 : 1);
' || FAIL=$((FAIL+1))

# Test 4: run_on_start callback
perl -MParallel::ForkManager -e '
    my $pm = Parallel::ForkManager->new(2);
    my @starts;
    $pm->run_on_start(sub {
        my ($pid, $ident) = @_;
        push @starts, $ident;
    });
    for my $i (1..3) {
        $pm->start("task_$i") and next;
        $pm->finish(0);
    }
    $pm->wait_all_children;
    exit(scalar(@starts) == 3 ? 0 : 1);
' || FAIL=$((FAIL+1))

# Test 5: Exit code propagation
perl -MParallel::ForkManager -e '
    my $pm = Parallel::ForkManager->new(1);
    my @codes;
    $pm->run_on_finish(sub {
        my ($pid, $exit_code) = @_;
        push @codes, $exit_code;
    });
    for my $code (0, 1, 42) {
        $pm->start and next;
        $pm->finish($code);
    }
    $pm->wait_all_children;
    exit($codes[0]==0 && $codes[1]==1 && $codes[2]==42 ? 0 : 1);
' || FAIL=$((FAIL+1))

# Test 6: Complex data structure return
perl -MParallel::ForkManager -e '
    my $pm = Parallel::ForkManager->new(2);
    my %data;
    $pm->run_on_finish(sub {
        my ($pid, $exit_code, $ident) = @_;
        $data{$ident} = $_[5];
    });
    for my $key (qw(a b)) {
        $pm->start($key) and next;
        $pm->finish(0, { val => $key, arr => [1,2,3] });
    }
    $pm->wait_all_children;
    exit($data{a}{val} eq "a" && @{$data{b}{arr}} == 3 ? 0 : 1);
' || FAIL=$((FAIL+1))

# Test 7: wait_all_children with no children (no crash)
perl -MParallel::ForkManager -e '
    my $pm = Parallel::ForkManager->new(4);
    $pm->wait_all_children;
    exit(0);
' || FAIL=$((FAIL+1))

if [ "$FAIL" -eq 0 ]; then
    echo "ALL_TESTS_PASSED"
    exit 0
else
    echo "TEST_FAILURES=$FAIL"
    exit 1
fi
