#!/usr/bin/env python3
"""End-to-end assertions for protoc-gen-grpc-web 2.1.1 (R34).

Driven by test_package/conanfile.py test() via self.run(). Executes the
plugin through protoc's plugin protocol and asserts on the generated
JavaScript client stubs.
"""

import argparse
import os
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-bin", required=True)
    parser.add_argument("--protoc", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Cross-build mode: run only the presence/ELF assertion (T1)",
    )
    args = parser.parse_args()

    total = 0
    passed = 0

    def check(name, condition):
        nonlocal total, passed
        total += 1
        if condition:
            passed += 1
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}", file=sys.stderr)

    # T1: binary sanity (works even when cross-building)
    with open(args.plugin_bin, "rb") as fh:
        magic = fh.read(4)
    check("T1 plugin binary exists with ELF magic", magic == b"\x7fELF")

    if args.smoke_only:
        print(f"HMBS_TEST_PACKAGE_RESULT: total={total} passed={passed}")
        return 0 if passed == total else 1

    workdir = args.workdir
    outdir = os.path.join(workdir, "out")
    ver_log = os.path.join(workdir, "version.log")
    gen_log = os.path.join(workdir, "generate.log")
    neg_log = os.path.join(workdir, "negative.log")
    generated_js = os.path.join(outdir, "sample_grpc_web_pb.js")

    try:
        os.makedirs(outdir, exist_ok=True)
        proto_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.proto")
        shutil.copy(proto_src, os.path.join(workdir, "sample.proto"))

        # T2: --version smoke (plugin protocol handshake)
        import subprocess
        with open(ver_log, "w") as fh:
            rc = subprocess.call([args.plugin_bin, "--version"], stdout=fh, stderr=fh)
        with open(ver_log, encoding="utf-8") as fh:
            ver_out = fh.read()
        check(
            "T2 plugin --version reports 2.1.1",
            rc == 0
            and "protoc-gen-grpc-web" in ver_out
            and "2.1.1" in ver_out,
        )

        # T3: end-to-end generation through protoc
        rc = subprocess.call(
            [
                args.protoc,
                f"--plugin=protoc-gen-grpc-web={args.plugin_bin}",
                "--grpc-web_out=import_style=commonjs,mode=grpcweb:" + outdir,
                "-I" + workdir,
                os.path.join(workdir, "sample.proto"),
            ],
            stdout=open(gen_log, "w"),
            stderr=subprocess.STDOUT,
        )
        check("T3 protoc + plugin generation succeeded", rc == 0)

        # T4: generated client stub exists
        check(
            "T4 generated sample_grpc_web_pb.js exists",
            os.path.isfile(generated_js),
        )
        with open(generated_js, encoding="utf-8") as fh:
            js = fh.read()

        # T5: service client stubs
        check(
            "T5 service client stubs (EchoServiceClient/PromiseClient)",
            "EchoServiceClient" in js and "EchoServicePromiseClient" in js,
        )

        # T6: method descriptor for the Echo rpc
        check(
            "T6 method stub (/sample.v1.EchoService/Echo)",
            "methodDescriptor_EchoService_Echo" in js
            and "/sample.v1.EchoService/Echo" in js,
        )

        # T7: import directives (commonjs style)
        check(
            "T7 import directives (sample_pb.js + grpc-web)",
            "require('./sample_pb.js')" in js and "require('grpc-web')" in js,
        )

        # T8: generator version banner embedded by the plugin
        check(
            "T8 generator banner protoc-gen-grpc-web v2.1.1",
            "protoc-gen-grpc-web v2.1.1" in js,
        )

        # T9 (negative): missing mode= option must be rejected
        with open(neg_log, "w") as fh:
            rc = subprocess.call(
                [
                    args.protoc,
                    f"--plugin=protoc-gen-grpc-web={args.plugin_bin}",
                    "--grpc-web_out=import_style=commonjs:" + outdir,
                    "-I" + workdir,
                    os.path.join(workdir, "sample.proto"),
                ],
                stdout=fh,
                stderr=subprocess.STDOUT,
            )
            if rc != 0:
                fh.write("EXITED_NONZERO\n")
        with open(neg_log, encoding="utf-8") as fh:
            neg_out = fh.read()
        check(
            "T9 missing mode option rejected",
            "mode is required" in neg_out and "EXITED_NONZERO" in neg_out,
        )
    finally:
        # R34 hygiene: never leave generated artifacts behind
        shutil.rmtree(workdir, ignore_errors=True)

    print(f"HMBS_TEST_PACKAGE_RESULT: total={total} passed={passed}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
