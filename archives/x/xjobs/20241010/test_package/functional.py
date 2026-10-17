import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def load_state(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def require_started(path, proc):
    try:
        state = load_state(path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise AssertionError("worker state unavailable: " + str(error)) from error
    if not state["started"]:
        raise AssertionError(
            "worker did not start: xjobs exit=" + str(proc.returncode)
            + ", stdout=" + repr(proc.stdout[-1500:])
            + ", stderr=" + repr(proc.stderr[-1500:]))
    return state


def wait_for_started(path, proc, timeout=8.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            state = load_state(path)
            if state["started"]:
                return state
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        if proc.poll() is not None:
            break
        time.sleep(0.02)
    raise AssertionError("worker did not start before timeout")


def command(binary, worker, state, limit, delay, extra=(), xjobs_options=(),
            parse_lines=False):
    args = [binary, "-v4", "-j", str(limit), *xjobs_options]
    if not parse_lines:
        args.append("-1")
    args.extend(["--", sys.executable, worker, "--worker", "--state", state,
                 "--delay", str(delay), *extra])
    return args


def invoke(binary, worker, root, name, items, limit=1, delay=0.1,
           extra=(), xjobs_options=(), parse_lines=False, timeout=20):
    state = os.path.join(root, name + ".json")
    with open(state, "w", encoding="utf-8") as stream:
        json.dump({"active": 0, "max_active": 0, "started": [], "finished": []}, stream)
    input_text = "\n".join(items) + "\n"
    proc = subprocess.run(
        command(binary, worker, state, limit, delay, extra, xjobs_options, parse_lines),
        input=input_text, text=True, capture_output=True, timeout=timeout)
    return proc, state


def record(state_path, field, item, pid):
    with open(state_path + ".lock", "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state(state_path)
        if field == "started":
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        else:
            state["active"] -= 1
        state[field].append({"item": item, "pid": pid})
        temp = state_path + ".tmp." + str(pid)
        with open(temp, "w", encoding="utf-8") as stream:
            json.dump(state, stream)
        os.replace(temp, state_path)


def worker_main(argv):
    state = None
    delay = 0.1
    fail_item = None
    item = None
    index = 0
    while index < len(argv):
        if argv[index] == "--state":
            state = argv[index + 1]
            index += 2
        elif argv[index] == "--delay":
            delay = float(argv[index + 1])
            index += 2
        elif argv[index] == "--fail-item":
            fail_item = "fail"
            index += 1
        else:
            item = argv[index]
            index += 1
    if state is None or item is None:
        return 64
    record(state, "started", item, os.getpid())
    print("payload:" + item, flush=True)
    time.sleep(delay)
    record(state, "finished", item, os.getpid())
    return 17 if item == fail_item else 0


def run_tests(binary, results):
    worker = os.path.abspath(__file__)
    root = os.path.abspath(results)
    os.makedirs(root, exist_ok=True)
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    version = subprocess.run([binary, "--version"], text=True, capture_output=True,
                             timeout=5)
    check("framework-compatible --version option",
          version.returncode == 0 and "xjobs version " in version.stdout,
          "exit=" + str(version.returncode) + ", stdout=" + repr(version.stdout.strip()))

    proc, state_path = invoke(binary, worker, root, "concurrency",
                              ["task-" + str(i) for i in range(6)],
                              limit=2, delay=0.35)
    require_started(state_path, proc)
    state = load_state(state_path)
    check("six jobs started", len(state["started"]) == 6,
          "started=" + str(len(state["started"])))
    check("six jobs finished", len(state["finished"]) == 6 and state["active"] == 0,
          "finished=" + str(len(state["finished"])) + ", active=" + str(state["active"]))
    check("parallel limit two", proc.returncode == 0 and state["max_active"] == 2,
          "exit=" + str(proc.returncode) + ", max_active=" + str(state["max_active"]))

    proc, state_path = invoke(binary, worker, root, "spaces", ["argument with spaces"],
                              delay=0)
    require_started(state_path, proc)
    state = load_state(state_path)
    check("single-character template argument and spaced job argument preserved",
          proc.returncode == 0 and state["started"][0]["item"] == "argument with spaces",
          "started=" + repr(state["started"]))

    redirect_path = os.path.join(root, "redirect output with spaces.txt")
    proc, state_path = invoke(binary, worker, root, "redirect",
                              ['redirect-target > "' + redirect_path + '"'],
                              delay=0, parse_lines=True)
    require_started(state_path, proc)
    state = load_state(state_path)
    redirected = Path(redirect_path).read_text(encoding="utf-8") if os.path.exists(redirect_path) else ""
    check("stdout redirected to spaced path",
          proc.returncode == 0 and "payload:redirect-target" in redirected
          and state["started"][0]["item"] == "redirect-target",
          "exit=" + str(proc.returncode) + ", content=" + repr(redirected))

    proc, state_path = invoke(binary, worker, root, "failure",
                              ["before", "fail", "after"], delay=0.35,
                              extra=["--fail-item"], xjobs_options=["-e"])
    require_started(state_path, proc)
    state = load_state(state_path)
    started = [entry["item"] for entry in state["started"]]
    check("failed child sets nonzero exit and -e stops queued jobs",
          proc.returncode == 1 and started == ["before", "fail"],
          "exit=" + str(proc.returncode) + ", started=" + repr(started))

    state_path = os.path.join(root, "cancel.json")
    with open(state_path, "w", encoding="utf-8") as stream:
        json.dump({"active": 0, "max_active": 0, "started": [], "finished": []}, stream)
    args = command(binary, worker, state_path, 1, 1.0)
    proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    proc.stdin.write("cancel-first\ncancel-second\ncancel-third\n")
    proc.stdin.close()
    proc.stdin = None
    try:
        started_state = wait_for_started(state_path, proc)
        child_pid = started_state["started"][0]["pid"]
        proc.send_signal(signal.SIGINT)
        _, stderr = proc.communicate(timeout=10)
    except Exception as error:
        if proc.poll() is None:
            proc.terminate()
        stdout, child_stderr = proc.communicate(timeout=5)
        raise AssertionError(
            str(error) + ", xjobs stdout=" + repr(stdout[-1500:])
            + ", stderr=" + repr(child_stderr[-1500:])) from error
    state = load_state(state_path)
    started = [entry["item"] for entry in state["started"]]
    finished = [entry["item"] for entry in state["finished"]]
    child_alive = True
    try:
        os.kill(child_pid, 0)
    except OSError:
        child_alive = False
    check("SIGINT stops queued jobs and reaps running child",
          proc.returncode == 0 and started == ["cancel-first"]
          and finished == ["cancel-first"] and not child_alive,
          "exit=" + str(proc.returncode) + ", started=" + repr(started)
          + ", finished=" + repr(finished) + ", child_alive=" + str(child_alive)
          + ", stderr=" + stderr[-300:])

    report = {"total": len(checks),
              "passed": sum(item["passed"] for item in checks),
              "failed": sum(not item["passed"] for item in checks),
              "checks": checks}
    with open(os.path.join(root, "summary.json"), "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    if report["failed"]:
        raise AssertionError("xjobs behavior checks failed: " + str(report["failed"]))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker":
        raise SystemExit(worker_main(sys.argv[2:]))
    if len(sys.argv) != 3:
        raise SystemExit("usage: functional.py XJOBS_BINARY RESULT_DIRECTORY")
    run_tests(os.path.abspath(sys.argv[1]), sys.argv[2])
