#!/bin/sh
set -eu

fail() {
    echo "test_flamethrower.sh: $*" >&2
    exit 1
}

expect_failure() {
    label=$1
    shift
    log_file="$PWD/${label}.log"
    set +e
    "$@" >"$log_file" 2>&1
    rc=$?
    set -e
    if [ "$rc" -eq 0 ] || [ "$rc" -ge 126 ]; then
        cat "$log_file" >&2
        fail "$label returned invalid failure status $rc"
    fi
}

pkg_folder=${1:?package folder required}

flamethrower="$pkg_folder/bin/flamethrower"
flamethrowerd="$pkg_folder/bin/flamethrowerd"
libdir="$pkg_folder/lib/flamethrower"
libexec_bindir="$pkg_folder/libexec/flamethrower/bin"
etcdir="$pkg_folder/etc/flamethrower"
init_script="$pkg_folder/etc/init.d/flamethrower-server"
module_file="$libdir/Flamethrower.pm"
real_flamethrower="$libexec_bindir/flamethrower"
real_flamethrowerd="$libexec_bindir/flamethrowerd"
runtime_dir="$PWD/flamethrower-runtime"
conf_file="$runtime_dir/flamethrower-smoke.conf"
debug_conf_file="$runtime_dir/flamethrower-debug.conf"
bad_conf_file="$runtime_dir/flamethrower-bad-interface.conf"
daemon_log="$runtime_dir/flamethrowerd-smoke.log"
debug_daemon_log="$runtime_dir/flamethrowerd-debug.log"
unknown_accessor_stdout="$runtime_dir/unknown-accessor.stdout"
unknown_accessor_stderr="$runtime_dir/unknown-accessor.stderr"
test_shell=${FLAMETHROWER_TEST_SHELL:-sh}

run_flamethrower() {
    "$test_shell" "$flamethrower" "$@"
}

run_flamethrowerd() {
    "$test_shell" "$flamethrowerd" "$@"
}

test -x "$flamethrower"
test -x "$flamethrowerd"
test -x "$real_flamethrower"
test -x "$real_flamethrowerd"
test -x "$init_script"
test -r "$module_file"
test -r "$etcdir/flamethrower.conf"

sh -n "$0"
grep -F 'FLAMETHROWER_LIBDIR' "$flamethrower" >/dev/null
grep -F 'PERL5LIB' "$flamethrower" >/dev/null
grep -F 'libexec/flamethrower/bin/flamethrower' "$flamethrower" >/dev/null
grep -F 'libexec/flamethrower/bin/flamethrowerd' "$flamethrowerd" >/dev/null
grep -F '0.1.8' "$module_file" >/dev/null
! grep -F 'INS_VERSION' "$module_file" >/dev/null || fail "module version placeholder was not replaced"
grep -F "'debug' => { ARGCOUNT => ARGCOUNT_ONE }" "$module_file" >/dev/null
! grep -F 'use File::Which' "$real_flamethrowerd" >/dev/null || fail "unexpected File::Which runtime dependency"
! grep -F '" --ttl"' "$real_flamethrowerd" >/dev/null || fail "global TTL argv still contains a leading space"
grep -F 'FLAMETHROWER_LIBDIR' "$real_flamethrower" >/dev/null
grep -F 'FLAMETHROWER_LIBDIR' "$real_flamethrowerd" >/dev/null
grep -F 'defined $debug_config' "$real_flamethrowerd" >/dev/null
! grep -F 'lc $ft_config->debug()' "$real_flamethrowerd" >/dev/null || fail "optional debug value remains unguarded"
! grep -F '/usr/lib/flamethrower' "$real_flamethrower" >/dev/null || fail "hard-coded system Flamethrower path remains"
! grep -F '/usr/lib/flamethrower' "$real_flamethrowerd" >/dev/null || fail "hard-coded system Flamethrower path remains"

run_flamethrower --version | grep 'version 0.1.8'
run_flamethrowerd --version | grep 'version 0.1.8'

command -v udp-receiver >/dev/null
command -v udp-sender >/dev/null

mkdir -p "$runtime_dir/directory" "$runtime_dir/state" "$runtime_dir/sample"

heredoc_marker=$(printf '%s%s' '<' '<')
! grep -F "$heredoc_marker" "$0" >/dev/null || fail "target shell heredoc remains"

printf '%s\n' \
    'START_FLAMETHROWER_DAEMON = no' \
    'FLAMETHROWER_DIRECTORY_PORTBASE = 9000' \
    "FLAMETHROWER_DIRECTORY_DIR = $runtime_dir/directory" \
    "FLAMETHROWER_STATE_DIR = $runtime_dir/state" \
    'INTERFACE = lo' \
    'MIN_CLIENTS = 1' \
    'MAX_WAIT = 1' \
    'MIN_WAIT = 1' \
    'NOSYNC = on' \
    '[sample]' \
    "DIR = $runtime_dir/sample" >"$conf_file"

printf '%s\n' \
    'START_FLAMETHROWER_DAEMON = no' \
    'FLAMETHROWER_DIRECTORY_PORTBASE = 9000' \
    "FLAMETHROWER_DIRECTORY_DIR = $runtime_dir/directory" \
    "FLAMETHROWER_STATE_DIR = $runtime_dir/state" \
    'INTERFACE = lo' \
    'MIN_CLIENTS = 1' \
    'MAX_WAIT = 1' \
    'MIN_WAIT = 1' \
    'DEBUG = on' \
    'NOSYNC = on' \
    '[sample]' \
    "DIR = $runtime_dir/sample" >"$debug_conf_file"

printf '%s\n' \
    'START_FLAMETHROWER_DAEMON = yes' \
    'FLAMETHROWER_DIRECTORY_PORTBASE = 9000' \
    "FLAMETHROWER_DIRECTORY_DIR = $runtime_dir/directory" \
    "FLAMETHROWER_STATE_DIR = $runtime_dir/state" \
    'INTERFACE = __flamethrower_missing_interface__' \
    'MIN_CLIENTS = 1' \
    'MAX_WAIT = 1' \
    'MIN_WAIT = 1' \
    'NOSYNC = on' \
    '[sample]' \
    "DIR = $runtime_dir/sample" >"$bad_conf_file"

perl -Mstrict -Mwarnings -MFlamethrower -MAppConfig=:argcount -e '
Flamethrower->read_config($ARGV[0]);
my $module_value = $::main::ft_config->modules();
my @modules = ref($module_value) eq "ARRAY" ? @{$module_value} : ($module_value);
die "sample module missing\n" unless grep { $_ eq "sample" } @modules;
die "directory module missing\n" unless grep { $_ eq "flamethrower_directory" } @modules;
die "interface parse failed\n" unless $::main::ft_config->interface() eq "lo";
print "Flamethrower module parse OK\n";
' "$conf_file"

perl -Mstrict -Mwarnings -MFlamethrower -e '
Flamethrower->read_config($ARGV[0]);
my $debug = $::main::ft_config->debug();
die "explicit debug value missing\n" unless defined($debug) && lc($debug) eq "on";
print "Flamethrower explicit debug parse OK\n";
' "$debug_conf_file"

set +e
perl -Mstrict -Mwarnings -MFlamethrower -e '
Flamethrower->read_config($ARGV[0]);
my $value = $::main::ft_config->definitely_unknown();
exit(defined($value) ? 2 : 0);
' "$conf_file" >"$unknown_accessor_stdout" 2>"$unknown_accessor_stderr"
unknown_accessor_rc=$?
set -e
test "$unknown_accessor_rc" -eq 0 || fail "unknown accessor returned $unknown_accessor_rc"
test ! -s "$unknown_accessor_stdout" || fail "unknown accessor emitted stdout"
grep -Fx 'definitely_unknown: no such variable' "$unknown_accessor_stderr" >/dev/null
test "$(wc -l <"$unknown_accessor_stderr" | tr -d '[:space:]')" -eq 1 \
    || fail "unknown accessor diagnostic was not unique"
echo "AppConfig unknown accessor diagnostic OK"

run_flamethrowerd --config-file "$conf_file" >"$daemon_log" 2>&1
if [ -s "$daemon_log" ]; then
    cat "$daemon_log" >&2
    fail "daemon emitted output for a valid non-debug configuration"
fi
run_flamethrowerd --config-file "$debug_conf_file" >"$debug_daemon_log" 2>&1
grep -Fx 'Flamethrower debug output turned on' "$debug_daemon_log" >/dev/null
test "$(wc -l <"$debug_daemon_log" | tr -d '[:space:]')" -eq 1 \
    || fail "explicit debug output was not unique"
expect_failure missing-client-config run_flamethrower --config-file "$runtime_dir/missing.conf" --list
expect_failure missing-daemon-config run_flamethrowerd --config-file "$runtime_dir/missing.conf"
expect_failure bad-daemon-interface run_flamethrowerd --config-file "$bad_conf_file"

echo "Flamethrower consumer smoke test OK"
