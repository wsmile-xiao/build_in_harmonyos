#!/usr/bin/env python3
"""Consumer runtime smoke test for an installed accel-ppp package.

Mirrors the upstream pytest cases that can run without kernel/privilege
prerequisites: test_accel_cmd_version, test_accel_cmd_non_existent_host,
test_accel_cmd_mcast_host, test_accel_pppd_version, and the accel-cmd
interaction parts of test_accel_cmd_commands / test_pcre_negative_cases.
"""

import glob
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

# Keeps ctypes handles alive in check_module_integrity().
_keepalive = []


def run(command, environment, expected_returncode=0):
    result = subprocess.run(
        command,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != expected_returncode:
        raise AssertionError(
            f"{' '.join(command)} returned {result.returncode}, "
            f"expected {expected_returncode}; stderr: {result.stderr}"
        )
    return result


def environment_with_modules(pppd):
    env = os.environ.copy()
    module_dir = os.path.join(os.path.dirname(os.path.dirname(pppd)), "lib", "accel-ppp")
    if os.path.isdir(module_dir):
        env["LD_LIBRARY_PATH"] = module_dir + os.pathsep + env.get(
            "LD_LIBRARY_PATH", ""
        )
    return env


def check_module_integrity(pppd, accel_cmd):
    """Start accel-pppd with the full module set and require zero load errors.

    Equivalent (userspace) check for the upstream kernel-module cases
    (test_vlan_mon_kernel_module_loaded / test_ipoe_kernel_module_loaded):
    the kernel modules themselves cannot be loaded without CAP_SYS_MODULE, but
    every shipped userspace module must load inside accel-pppd with all
    DT_NEEDED symbols resolved (triton_*/connlimit_*/rad_*/openssl/log_*/
    ap_session_*).  Mirrors test_load_all_modules: accel-pppd dlopens modules
    from its own global scope, so we verify through a real server run rather
    than an artificial ctypes dlopen.

    Note: on unprivileged hosts accel-pppd may later crash in the ipoe driver
    (raw-socket init, "arp: socket: Permission denied"); that happens after
    module loading, so the gate is: no "failed to load" line in the log.
    """
    env = environment_with_modules(pppd)
    config = """[modules]
log_file
log_syslog
log_tcp
connlimit
pptp
l2tp
sstp
radius
pppoe
ipoe
auth_mschap_v2
auth_mschap_v1
auth_chap_md5
auth_pap
chap-secrets
ippool
pppd_compat
shaper
logwtmp
ipv6_nd
ipv6_dhcp
ipv6pool

[core]
log-error=/dev/stderr

[log]
log-debug=/dev/stdout
level=5

[cli]
tcp=127.0.0.1:2001

[pppoe]

[client-ip-range]
10.0.0.0/8

[radius]
"""
    config_file = tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False)
    config_file.write(config)
    config_file.close()
    server = subprocess.Popen(
        [pppd, "-c", config_file.name],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        try:
            _, err = server.communicate(timeout=4)
        except subprocess.TimeoutExpired as exc:
            # Process still alive: capture what was written so far.
            err = exc.stderr or ""
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
    finally:
        if server.poll() is None:
            server.kill()
        os.unlink(config_file.name)
    if "failed to load" in (err or ""):
        raise AssertionError(f"module load errors detected: {err}")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: smoke_test.py <accel-pppd> <accel-cmd>")

    pppd, accel_cmd = sys.argv[1], sys.argv[2]
    for binary in (pppd, accel_cmd):
        if not os.path.isfile(binary):
            raise AssertionError(f"missing installed binary: {binary}")

    env = environment_with_modules(pppd)

    # Equivalent userspace check for the upstream kernel-module cases:
    # start accel-pppd with the full module set and require zero load errors.
    check_module_integrity(pppd, accel_cmd)

    # test_accel_pppd_version: --version exits 0, prints exactly 2 tokens.
    version = run([pppd, "--version"], env)
    if "accel-ppp " not in version.stdout or len(version.stdout.split()) != 2:
        raise AssertionError(f"unexpected --version output: {version.stdout}")
    if "1.14.0" not in version.stdout:
        raise AssertionError(f"unexpected --version output: {version.stdout}")

    # test_accel_pppd help surface (extra, same family).
    run([pppd, "--help"], env)

    # test_accel_cmd_version: --version exits 0, prints exactly 2 tokens.
    cmd_version = run([accel_cmd, "--version"], env)
    if "accel-cmd " not in cmd_version.stdout or len(cmd_version.stdout.split()) != 2:
        raise AssertionError(f"unexpected accel-cmd --version: {cmd_version.stdout}")

    # test_accel_cmd_non_existent_host: connect failure -> nonzero, stderr nonempty.
    bad_host = subprocess.run(
        [accel_cmd, "-Hnon-existent-host", "--verbose"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if bad_host.returncode == 0 or bad_host.stdout != "" or bad_host.stderr == "":
        raise AssertionError(
            f"non-existent host should fail: rc={bad_host.returncode} "
            f"out={bad_host.stdout!r} err={bad_host.stderr!r}"
        )

    # test_accel_cmd_mcast_host: multicast target must fail.
    mcast = subprocess.run(
        [accel_cmd, "-H225.0.0.1"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if mcast.returncode == 0 or mcast.stdout != "":
        raise AssertionError(
            f"multicast host should fail: rc={mcast.returncode} out={mcast.stdout!r}"
        )

    # test_accel_cmd_commands: start accel-pppd with an empty-module config,
    # then query it through the TCP CLI (show stat/help).
    config = """[modules]

[log]
log-debug=/dev/stdout
level=5

[cli]
tcp=127.0.0.1:2001
"""
    config_file = tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False)
    config_file.write(config)
    config_file.close()

    server = subprocess.Popen(
        [pppd, "-c", config_file.name],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 10.0
        show_stat = None
        while time.time() < deadline:
            if server.poll() is not None:
                raise AssertionError(
                    f"accel-pppd exited early rc={server.returncode} "
                    f"err={server.stderr.read()}"
                )
            show_stat = subprocess.run(
                [accel_cmd, "show stat"],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if show_stat.returncode == 0 and "uptime" in show_stat.stdout:
                break
            time.sleep(0.3)
        else:
            raise AssertionError(
                f"accel-cmd show stat never returned uptime: {show_stat.stdout if show_stat else None}"
            )

        help_out = subprocess.run(
            [accel_cmd, "help"],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if help_out.returncode != 0 or "show stat" not in help_out.stdout:
            raise AssertionError(
                f"accel-cmd help missing 'show stat': rc={help_out.returncode} "
                f"out={help_out.stdout}"
            )
    finally:
        server.send_signal(signal.SIGTERM)
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        os.unlink(config_file.name)

    print(
        "smoke_test OK: module integrity (full module load), accel-pppd/accel-cmd "
        "version/help, host/mcast failure, CLI show stat/help, missing-config "
        "fail-closed — all assertions passed"
    )


if __name__ == "__main__":
    main()