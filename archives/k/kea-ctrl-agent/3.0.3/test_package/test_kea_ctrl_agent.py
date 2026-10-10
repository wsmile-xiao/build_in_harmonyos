#!/usr/bin/env python3
"""Consumer test for the packaged kea-ctrl-agent 3.0.3.

Runs the packaged Control Agent (found through the Conan run environment) and
checks the contract a consumer depends on.  Each case is judged PASS/FAIL on
its own; the run ends with a machine-readable TEST SUMMARY line and a non-zero
exit code if any case failed.

Cases
  * version_short        -- ``-v`` prints exactly 3.0.3
  * version_extended     -- ``-V`` prints the extended version block
  * config_report        -- ``-W`` prints the build configuration report
  * usage_error_path     -- no arguments prints the usage text and exits 1
  * config_check_valid   -- ``-t`` accepts a valid minimal configuration
  * config_check_invalid -- ``-t`` rejects a syntax error and an out-of-range
                            port with exit code 1
  * control_channel_e2e  -- start the real agent on a loopback port, POST a
                            real control-channel command (config-get) over
                            HTTP, verify the JSON answer, verify the error
                            answer to an unsupported command, verify the
                            configured log file was written and shut the
                            agent down with SIGTERM
"""
import http.client
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

EXPECTED_VERSION = "3.0.3"

AGENT = shutil.which("kea-ctrl-agent")
if not AGENT:
    print("kea-ctrl-agent is not on PATH - the package exposes no runnable command")
    sys.exit(1)
print("kea-ctrl-agent:", AGENT)

WORK = tempfile.mkdtemp(prefix="kea-ctrl-agent-test-", dir=os.getcwd())


def run(*args, timeout=60):
    return subprocess.run([AGENT, *args], capture_output=True, text=True,
                          timeout=timeout, stdin=subprocess.DEVNULL)


def write_config(name, text):
    path = os.path.join(WORK, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def http_post(port, payload):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("POST", "/", body=json.dumps(payload),
                     headers={"Content-Type": "application/json",
                              "Accept": "application/json"})
        response = conn.getresponse()
        return response.status, response.read().decode("utf-8", "replace")
    finally:
        conn.close()


def find_key(obj, key):
    """Return the first value of ``key`` anywhere in a JSON-like structure."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = find_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_key(value, key)
            if found is not None:
                return found
    return None


def control_answer(parsed):
    """Return the answer object of a control-channel response.

    The Kea control channel wraps each answer in a one-element JSON list (the
    batch/JSON-RPC shape), so unwrap it before inspecting the object.
    """
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        return parsed[0]
    return parsed


def case_version_short():
    result = run("-v")
    fails = []
    if result.returncode != 0:
        fails.append("-v exited with {}".format(result.returncode))
    if result.stdout.strip() != EXPECTED_VERSION:
        fails.append("-v printed {!r}, expected {!r}".format(
            result.stdout.strip(), EXPECTED_VERSION))
    return fails


def case_version_extended():
    result = run("-V")
    fails = []
    if result.returncode != 0:
        fails.append("-V exited with {}".format(result.returncode))
    if not result.stdout.strip().startswith(EXPECTED_VERSION):
        fails.append("-V printed {!r}, expected the {} extended version".format(
            result.stdout.strip(), EXPECTED_VERSION))
    if "linked with:" not in result.stdout:
        fails.append("-V printed no linked-libraries section")
    return fails


def case_config_report():
    result = run("-W")
    fails = []
    if result.returncode != 0:
        fails.append("-W exited with {}".format(result.returncode))
    if "Hooks directory:" not in result.stdout:
        fails.append("-W printed no configuration report")
    if EXPECTED_VERSION not in result.stdout:
        fails.append("-W report does not carry the {} version".format(EXPECTED_VERSION))
    return fails


def case_usage_error_path():
    result = run()
    fails = []
    if result.returncode == 0:
        fails.append("running without arguments exited 0, expected a usage error")
    if "Usage: kea-ctrl-agent" not in result.stderr:
        fails.append("the usage text is missing from stderr: {!r}".format(
            result.stderr.strip()[:200]))
    return fails


VALID_CONFIG = """{
    "Control-agent": {
        "http-host": "127.0.0.1",
        "http-port": 18000,
        "loggers": [
            { "name": "kea-ctrl-agent",
              "output-options": [ { "output": "kea-ctrl-agent.log" } ],
              "severity": "DEBUG" }
        ]
    }
}"""


def case_config_check_valid():
    config = write_config("valid.json", VALID_CONFIG)
    result = run("-t", config)
    fails = []
    if result.returncode != 0:
        fails.append("-t on a valid configuration exited with {}: {}{}".format(
            result.returncode, result.stdout.strip(), result.stderr.strip()))
    return fails


def case_config_check_invalid():
    bad_syntax = write_config(
        "bad-syntax.json",
        '{"Control-agent": {"http-port": BOGUS}}')
    bad_value = write_config(
        "bad-value.json",
        '{"Control-agent": {"http-port": 80000}}')
    fails = []
    for name, config in (("syntax error", bad_syntax), ("out-of-range port", bad_value)):
        result = run("-t", config)
        if result.returncode != 1:
            fails.append("-t on a {} exited with {}, expected 1".format(
                name, result.returncode))
    return fails


def case_control_channel_e2e():
    fails = []
    port = free_port()
    config = write_config("e2e.json", """{
    "Control-agent": {
        "http-host": "127.0.0.1",
        "http-port": %d,
        "loggers": [
            { "name": "kea-ctrl-agent",
              "output-options": [ { "output": "%s" } ],
              "severity": "DEBUG" }
        ]
    }
}""" % (port, os.path.join(WORK, "e2e.log")))

    env = os.environ.copy()
    # The default pid/lock directories live under the system runtime directory,
    # which is not writable for an unprivileged process; point them at the
    # scratch directory like the upstream process tests do.
    env["KEA_PIDFILE_DIR"] = WORK
    env["KEA_LOCKFILE_DIR"] = WORK
    # File loggers are whitelisted to the directory named by KEA_LOG_FILE_DIR
    # (default /var/log/kea, which does not exist on this platform); point it
    # at the scratch directory so the absolute e2e.log below is accepted.
    env["KEA_LOG_FILE_DIR"] = WORK
    out_path = os.path.join(WORK, "e2e.out")
    out = open(out_path, "wb")
    proc = subprocess.Popen([AGENT, "-c", config], stdout=out,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, env=env)
    try:
        # Wait for the control channel to accept connections.
        deadline = time.time() + 15
        listening = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    listening = True
                    break
            except OSError:
                time.sleep(0.2)
        if not listening:
            out.flush()
            with open(out_path, "rb") as handle:
                tail = handle.read()[-500:].decode("utf-8", "replace")
            fails.append("the agent did not open 127.0.0.1:{} within 15 s "
                         "(exit code {}), output tail: {!r}".format(
                             port, proc.poll(), tail))
            return fails

        # A real control-channel command: config-get is served by the agent
        # itself and must return the configuration the agent is running.
        status, body = http_post(port, {"command": "config-get"})
        if status != 200:
            fails.append("config-get was answered with HTTP {}".format(status))
        try:
            answer = control_answer(json.loads(body))
        except ValueError:
            fails.append("the config-get answer is not JSON: {!r}".format(body[:200]))
        else:
            if not isinstance(answer, dict):
                fails.append("the config-get answer is not a JSON object: "
                             "{!r}".format(body[:200]))
            else:
                if answer.get("result") != 0:
                    fails.append("config-get returned result {}: {!r}".format(
                        answer.get("result"), body[:200]))
                if find_key(answer, "http-port") != port:
                    fails.append("config-get did not return the running http-port {}: "
                                 "{!r}".format(port, body[:200]))

        # The error path of the same channel: an unsupported command must be
        # answered with a non-zero result instead of silence or a crash.
        status, body = http_post(port, {"command": "no-such-command"})
        if status != 200:
            fails.append("the unsupported command was answered with HTTP {}".format(status))
        try:
            answer = control_answer(json.loads(body))
        except ValueError:
            fails.append("the unsupported-command answer is not JSON: {!r}".format(
                body[:200]))
        else:
            if not isinstance(answer, dict):
                fails.append("the unsupported-command answer is not a JSON object: "
                             "{!r}".format(body[:200]))
            elif answer.get("result") == 0:
                fails.append("an unsupported command was reported as successful: "
                             "{!r}".format(body[:200]))
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                fails.append("the agent did not stop on SIGTERM within 10 s")
        out.close()
    # The whitelist fix above is only real if the logger actually wrote the
    # file: the agent must have produced e2e.log in the scratch directory.
    if not os.path.exists(os.path.join(WORK, "e2e.log")):
        fails.append("the configured log file e2e.log was not written to the "
                     "scratch directory")
    return fails


CASES = (
    ("version_short", case_version_short),
    ("version_extended", case_version_extended),
    ("config_report", case_config_report),
    ("usage_error_path", case_usage_error_path),
    ("config_check_valid", case_config_check_valid),
    ("config_check_invalid", case_config_check_invalid),
    ("control_channel_e2e", case_control_channel_e2e),
)

passed = 0
failed = 0
try:
    for name, case in CASES:
        try:
            failures = case()
        except Exception as error:  # noqa: BLE001 - report any case crash
            failures = ["crashed: {!r}".format(error)]
        if failures:
            failed += 1
            for failure in failures:
                print("TEST FAIL: {}: {}".format(name, failure))
        else:
            passed += 1
            print("TEST PASS: {}".format(name))
finally:
    shutil.rmtree(WORK, ignore_errors=True)

print("TEST SUMMARY: {} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
