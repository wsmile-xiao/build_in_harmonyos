#!/usr/bin/env python3
"""kubergrunt 0.19.0 消费者用例 + 交付形态自检。

用法:
    python3 consumer_check.py <package_folder> [--expect-machine aarch64]
                              [--require-signature] [--expect-version 0.19.0]

消费者用例（C1-C8）**真跑交付出来的 bin/kubergrunt**，断言真实 stdout / stderr /
退出码；期望值取自上游源码与行为（urfave/cli v1 + gruntwork go-commons
entrypoint，cmd/main.go 里 `app.Version = VERSION`，VERSION 由 -X main.VERSION 注入；
`eks oidc-thumbprint` 的 `--issuer-url is required` 来自 cmd/eks.go 的必填 flag）。

交付形态自检（M1-M13）检查二进制本体与包内容物，不依赖任何外部资源。
任一 check 失败 → 退出码 1（R34 反空壳：把 bin/ 挪走后本脚本必然失败）。
"""
import os
import subprocess
import sys

_MACHINE_ID = {"aarch64": 0xB7, "x86_64": 0x3E}
_CODESIGN = b".codesign"
_WORKDIR_MARKERS = (b"conan-go-build", b".go-work")


class Report(object):
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.note = 0

    def check(self, condition, label):
        if condition:
            self.ok += 1
            print("        [ok] %s" % label)
        else:
            self.fail += 1
            print("        [FAIL] %s" % label)
        return bool(condition)

    def skip(self, label):
        self.note += 1
        print("        [skip] %s" % label)


def _run(binary, args, timeout=60):
    proc = subprocess.Popen([binary] + args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd="/")
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None, "", "timeout after %ss" % timeout
    return proc.returncode, out.decode("utf-8", "replace"), \
        err.decode("utf-8", "replace")


def _elf(data):
    """返回 (ei_class, ei_data, e_machine, program_header_types)。"""
    ei_class, ei_data = data[4], data[5]
    e_machine = int.from_bytes(data[18:20], "little")
    e_phoff = int.from_bytes(data[32:40], "little")
    e_phentsize = int.from_bytes(data[54:56], "little")
    e_phnum = int.from_bytes(data[56:58], "little")
    ptypes = []
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        if off + 4 > len(data):
            break
        ptypes.append(int.from_bytes(data[off:off + 4], "little"))
    return ei_class, ei_data, e_machine, ptypes


def _iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            yield dirpath, name
        for name in dirnames:
            yield dirpath, name


def main(argv):
    if len(argv) < 2:
        print("usage: consumer_check.py <package_folder> [options]")
        return 2
    package_folder = os.path.abspath(argv[1])
    expect_machine = "aarch64"
    require_signature = False
    expect_version = "0.19.0"
    rest = argv[2:]
    while rest:
        opt = rest.pop(0)
        if opt == "--expect-machine":
            expect_machine = rest.pop(0)
        elif opt == "--require-signature":
            require_signature = True
        elif opt == "--expect-version":
            expect_version = rest.pop(0)
        else:
            print("unknown option: %s" % opt)
            return 2

    report = Report()
    bin_dir = os.path.join(package_folder, "bin")
    binary = os.path.join(bin_dir, "kubergrunt")
    print("[step] package folder: %s" % package_folder)
    print("[step] binary: %s" % binary)
    print("[step] expect machine=%s version=%s require_signature=%s"
          % (expect_machine, expect_version, require_signature))

    if not os.path.isfile(binary):
        print("[FAIL] bin/kubergrunt missing — nothing to test")
        return 1

    with open(binary, "rb") as handle:
        data = handle.read()

    # ── C: 消费者用例（真跑交付出来的二进制）──────────────────────
    print("[step] C1: kubergrunt --version")
    code, out, err = _run(binary, ["--version"])
    report.check(code == 0, "C1 exit code 0 (got %s)" % code)
    report.check(out == "kubergrunt version %s\n" % expect_version,
                 "C1 stdout == 'kubergrunt version %s' (got %r)"
                 % (expect_version, out))

    print("[step] C2: kubergrunt --help")
    code, out, err = _run(binary, ["--help"])
    report.check(code == 0, "C2 exit code 0 (got %s)" % code)
    report.check("A CLI tool to help setup and manage a Kubernetes cluster." in out,
                 "C2 stdout carries the upstream app description")
    report.check(all(("   %s " % name) in out for name in ("eks", "k8s", "tls")),
                 "C2 stdout lists subcommands eks / k8s / tls")

    print("[step] C3: kubergrunt eks --help")
    code, out, err = _run(binary, ["eks", "--help"])
    report.check(code == 0, "C3 exit code 0 (got %s)" % code)
    report.check("Helper commands to configure EKS" in out,
                 "C3 stdout carries the eks group description")
    report.check(all(name in out for name in (
        "deploy", "drain", "sync-core-components", "cleanup-security-group",
        "oidc-thumbprint", "verify", "configure")),
        "C3 stdout lists the documented eks subcommands")

    print("[step] C4: kubergrunt k8s --help")
    code, out, err = _run(binary, ["k8s", "--help"])
    report.check(code == 0, "C4 exit code 0 (got %s)" % code)
    report.check("wait-for-ingress" in out and "kubectl" in out,
                 "C4 stdout lists wait-for-ingress and kubectl")

    print("[step] C5: kubergrunt tls gen --help")
    code, out, err = _run(binary, ["tls", "gen", "--help"])
    report.check(code == 0, "C5 exit code 0 (got %s)" % code)
    report.check("--namespace value" in out and "--secret-name value" in out,
                 "C5 stdout documents the required --namespace/--secret-name flags")

    print("[step] C6: kubergrunt eks oidc-thumbprint (missing required flag)")
    code, out, err = _run(binary, ["eks", "oidc-thumbprint"])
    report.check(code == 1, "C6 exit code 1 (got %s)" % code)
    report.check(out == "", "C6 stdout empty on failure (got %r)" % out)
    report.check("--issuer-url is required" in err,
                 "C6 stderr explains the missing --issuer-url flag")

    print("[step] C7: kubergrunt bogus (unknown subcommand)")
    code, out, err = _run(binary, ["bogus"])
    report.check(code == 1, "C7 exit code 1 (got %s)" % code)
    report.check("No help topic for 'bogus'" in err,
                 "C7 stderr reports the unknown help topic")

    print("[step] C8: kubergrunt --loglevel bogus (invalid log level)")
    code, out, err = _run(binary, ["--loglevel", "bogus"])
    report.check(code == 1, "C8 exit code 1 (got %s)" % code)
    report.check('not a valid logrus Level: "bogus"' in err,
                 "C8 stderr reports the invalid logrus level")

    # ── M: 交付形态自检 ───────────────────────────────────────────
    print("[step] M1: bin/kubergrunt exists")
    report.check(os.path.isfile(binary), "M1 bin/kubergrunt is a regular file")

    print("[step] M2: plausible binary size")
    size = os.path.getsize(binary)
    report.check(5 * 1024 * 1024 <= size <= 300 * 1024 * 1024,
                 "M2 size %d bytes within 5MiB..300MiB" % size)

    print("[step] M3: owner execute bit")
    report.check(os.access(binary, os.X_OK),
                 "M3 binary is executable by the current user")

    print("[step] M4: ELF magic")
    report.check(data[:4] == b"\x7fELF",
                 "M4 starts with the ELF magic (got %r)" % data[:4])

    print("[step] M5: ELF machine is %s" % expect_machine)
    ei_class, ei_data, e_machine, ptypes = _elf(data)
    report.check(ei_class == 2 and ei_data == 1,
                 "M5 ELF64 little-endian (class=%d data=%d)" % (ei_class, ei_data))
    report.check(e_machine == _MACHINE_ID[expect_machine],
                 "M5 e_machine 0x%X == %s (0x%X)"
                 % (e_machine, expect_machine, _MACHINE_ID[expect_machine]))

    print("[step] M6: statically linked (no PT_INTERP)")
    report.check(3 not in ptypes,
                 "M6 program headers contain no PT_INTERP (%d phdrs)"
                 % len(ptypes))

    print("[step] M7: HongMeng ELF signature")
    if require_signature:
        report.check(_CODESIGN in data,
                     "M7 .codesign section present (E128 self-sign)")
    else:
        report.skip("M7 signature not required for %s" % expect_machine)

    print("[step] M8: bin/ contains only the delivered binary")
    entries = sorted(os.listdir(bin_dir))
    report.check(entries == ["kubergrunt"],
                 "M8 bin/ listing is exactly ['kubergrunt'] (got %r)" % entries)

    print("[step] M9: license shipped")
    license_path = os.path.join(package_folder, "licenses", "LICENSE")
    license_text = ""
    if os.path.isfile(license_path):
        with open(license_path, "r", encoding="utf-8", errors="replace") as handle:
            license_text = handle.read()
    report.check("Apache License" in license_text and "Version 2.0" in license_text,
                 "M9 licenses/LICENSE is the Apache-2.0 text (%d bytes)"
                 % len(license_text))

    print("[step] M10-M12: package content hygiene")
    go_sources = []
    hidden = []
    objects = []
    for dirpath, name in _iter_files(package_folder):
        rel = os.path.relpath(os.path.join(dirpath, name), package_folder)
        if name.endswith(".go") or name in ("go.mod", "go.sum") \
                or name.endswith(".test"):
            go_sources.append(rel)
        if name.startswith(".") or name in ("__pycache__", "go-build"):
            hidden.append(rel)
        if name.endswith((".o", ".a", ".c", ".s", ".h")):
            objects.append(rel)
    report.check(not go_sources,
                 "M10 no Go sources/module files in the package (got %r)"
                 % go_sources[:5])
    report.check(not hidden,
                 "M11 no hidden files or build caches in the package (got %r)"
                 % hidden[:5])
    report.check(not objects,
                 "M12 no intermediate object/source files in the package (got %r)"
                 % objects[:5])

    print("[step] M13: build work directory path not embedded (-trimpath)")
    embedded = [marker.decode() for marker in _WORKDIR_MARKERS if marker in data]
    report.check(not embedded,
                 "M13 binary embeds no build work-dir marker (got %r)" % embedded)

    print("[summary] consumer checks: %d passed, %d failed, %d skipped"
          % (report.ok, report.fail, report.note))
    if report.fail:
        print("[summary] kubergrunt consumer check FAILED")
        return 1
    print("[summary] kubergrunt consumer check PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
