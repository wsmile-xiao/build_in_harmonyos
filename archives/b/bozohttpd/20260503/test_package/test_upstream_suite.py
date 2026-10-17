#!/usr/bin/env python3
"""Execute the unmodified bozohttpd 20260503 upstream testsuite fixtures."""

import base64
import http.client
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import shutil


SIMPLE_TESTS = [f"t{number}" for number in range(1, 19) if number != 11]


def normalize_output(data):
    """Apply the volatile-header normalization used by upstream html_cmp."""
    text = data.decode("latin1")
    text = re.sub(r"(?m)^Date: .*?$", "Date: nowish", text)
    text = re.sub(r"(?m)^Last-Modified: .*?$", "Last-Modified: nowish", text)
    text = re.sub(r"(?m)^Server: .*?$", "Server: bozotic HTTP server version 5.08", text)
    text = re.sub(r"(?m)^Content-Length: .*?$", "Content-Length: 223", text)
    text = re.sub(r"[a-zA-Z0-9-]*\.eterna\.com\.au", "localhost", text)
    text = re.sub(r"[a-zA-Z0-9-]*\.eterna23\.net", "localhost", text)
    return text.encode("latin1")


def run_simple(binary, fixtures, number, workdir, cgi=False):
    args = [binary]
    if cgi:
        args.extend(["-c", os.path.join(fixtures, "cgi-bin")])
    args.append(os.path.join(fixtures, "data"))
    with open(os.path.join(fixtures, f"{number}.in.b64"), "rb") as request_file:
        request = base64.b64decode(request_file.read().strip(), validate=True)
    result = subprocess.run(
        args,
        input=request,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=workdir,
        timeout=15,
    )
    with open(os.path.join(fixtures, f"{number}.out.b64"), "rb") as expected_file:
        expected = base64.b64decode(expected_file.read().strip(), validate=True)
    if result.returncode != 0:
        raise AssertionError(f"upstream {number}: server exit {result.returncode}: {result.stderr!r}")
    if normalize_output(result.stdout) != normalize_output(expected):
        raise AssertionError(
            f"upstream {number}: response differs from the upstream fixture\n"
            f"expected={normalize_output(expected)!r}\nactual={normalize_output(result.stdout)!r}"
        )


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def run_bigfile(binary, fixtures, partial_size, workdir):
    data_dir = os.path.join(fixtures, "data")
    complete_path = os.path.join(data_dir, "bigfile")
    partial_path = os.path.join(data_dir, f"bigfile.partial{partial_size}")
    with open(complete_path, "rb") as complete_file:
        complete = complete_file.read()
    with open(partial_path, "rb") as partial_file:
        partial = partial_file.read()
    if len(partial) != partial_size or complete[:partial_size] != partial:
        raise AssertionError(f"upstream partial{partial_size}: invalid partial fixture")

    docroot = os.path.join(workdir, f"bigfile-{partial_size}")
    os.makedirs(docroot)
    with open(os.path.join(docroot, "bigfile"), "wb") as output:
        output.write(partial)
    port = free_port()
    server = subprocess.Popen(
        [
            binary,
            "-b",
            "-b",
            "-i",
            "127.0.0.1",
            "-I",
            str(port),
            "-n",
            "-s",
            "-f",
            data_dir,
            "",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=workdir,
    )
    try:
        deadline = time.monotonic() + 10
        response = None
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise AssertionError(f"upstream partial{partial_size}: server exited {server.returncode}")
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                connection.request(
                    "GET", "/bigfile", headers={"Range": f"bytes={partial_size}-"}
                )
                response = connection.getresponse()
                body = response.read()
                break
            except OSError:
                time.sleep(0.1)
            finally:
                if "connection" in locals():
                    connection.close()
                    del connection
        if response is None:
            raise AssertionError(f"upstream partial{partial_size}: server did not accept a connection")
        if response.status != 206:
            raise AssertionError(f"upstream partial{partial_size}: expected 206, got {response.status}")
        expected_range = f"bytes {partial_size}-{len(complete) - 1}/{len(complete)}"
        if response.getheader("Content-Range") != expected_range:
            raise AssertionError(
                f"upstream partial{partial_size}: Content-Range {response.getheader('Content-Range')!r}"
            )
        with open(os.path.join(docroot, "bigfile"), "ab") as output:
            output.write(body)
        with open(os.path.join(docroot, "bigfile"), "rb") as result_file:
            actual = result_file.read()
        if actual != complete:
            raise AssertionError(f"upstream partial{partial_size}: resumed file differs from fixture")
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=3)


def main(binary, fixtures):
    passed = 0
    with tempfile.TemporaryDirectory(prefix="bozohttpd-upstream-") as workdir:
        runtime_fixtures = os.path.join(workdir, "fixtures")
        shutil.copytree(fixtures, runtime_fixtures)
        remap_path = os.path.join(runtime_fixtures, "data", "bzremap.b64")
        with open(remap_path, "rb") as remap_file:
            remap = base64.b64decode(remap_file.read().strip(), validate=True)
        with open(os.path.join(runtime_fixtures, "data", ".bzremap"), "wb") as remap_file:
            remap_file.write(remap)
        for number in SIMPLE_TESTS:
            run_simple(binary, runtime_fixtures, f"t{number[1:]}", workdir)
            passed += 1
            print(f"PASS upstream {number}")
        run_simple(binary, runtime_fixtures, "t11", workdir, cgi=True)
        passed += 1
        print("PASS upstream t11 (CGI)")
        for partial_size in (4000, 8000):
            run_bigfile(binary, runtime_fixtures, partial_size, workdir)
            passed += 1
            print(f"PASS upstream partial{partial_size}")
    if passed != 20:
        raise AssertionError(f"expected 20 upstream cases, executed {passed}")
    print(f"UPSTREAM_TESTS=20/20")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
