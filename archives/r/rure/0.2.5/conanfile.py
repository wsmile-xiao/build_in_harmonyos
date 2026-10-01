#!/usr/bin/env python3
"""Conan recipe - rure 0.2.5 (C API for Rust's regular expression library).

Upstream : https://github.com/rust-lang/regex (workspace member `regex-capi`)
Crate    : rure 0.2.5 (crates.io, vcs sha1 2aaa18dfaeda7a07202f1c8a0d7a7a10116d5153)
Build    : cargo (crate-type staticlib/cdylib/rlib); upstream C test `ctest/test.c`.

OHOS notes (verified on device):
  * rust-toolchain/1.97.1 ships cargo/rustc/rustc_driver. OHOS refuses to exec an
    unsigned mmap'ed ELF, so a private *signed* copy of those three files is made
    inside the build folder - the Conan dependency package is never modified.
  * Cargo is linked against libssl.so / libcrypto.so / libz.so. The OpenSSL DSOs
    are relinked from the PIC static archives of openssl/3.5.6.1.1 (soname set to
    the plain names cargo requires) and signed; libz.so is a signed copy of the
    system /usr/lib/libz.so.1.
  * `/data/service/hnp/bin/clang` is a `#!/bin/sh` wrapper. OHOS/conan cannot
    exec shebang scripts, so the recipe follows the wrapper to the real ELF
    driver (clang-15) before invoking it.
  * The private runtime dir is only exposed through a package-local build env
    script; no global prefix or public Conan lib dir receives the DSOs.
"""

import json
import os
import re
import shlex
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

RUST_TARGET = "aarch64-unknown-linux-ohos"
CA_BUNDLE = "/etc/ssl/certs/cacert.pem"
ATTEMPTS = 10


class RureConan(ConanFile):
    name = "rure"
    version = "0.2.5"
    description = "A C API for Rust's regular expression library"
    license = "MIT", "Apache-2.0"
    homepage = "https://github.com/rust-lang/regex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rure is supported on Linux/OHOS only")
        if self.settings.build_type != "Release":
            raise ConanInvalidConfiguration("This package uses the Cargo release profile")

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], filename="rure-0.2.5.tar.gz", strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    # ------------------------------------------------------------------ #
    # paths / helpers
    # ------------------------------------------------------------------ #
    def _rust_folder(self):
        return self.dependencies.build["rust-toolchain"].package_folder

    def _compiler(self):
        conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return conf.get("c", "clang")

    def _real_cc(self, cc):
        # `/data/service/hnp/bin/clang` is a `#!/bin/sh` wrapper. OHOS/conan
        # cannot exec shebang scripts, so follow the wrapper to the real ELF
        # driver (clang-15) it execs. os.path.realpath() does not resolve the
        # symlink on HMDFS here, so parse the wrapper body instead.
        path = cc
        for _ in range(4):
            try:
                with open(path, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        return path
                with open(path, "r", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                break
            body = "\n".join(l for l in text.splitlines() if not l.startswith("#!"))
            nxt = None
            for token in re.findall(r"/[^\s\"']+", body):
                try:
                    with open(token, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            nxt = token
                            break
                except OSError:
                    continue
            if not nxt:
                break
            path = nxt
        return path

    def _runtime_dirs(self):
        private = os.path.join(self.build_folder, "runtime")
        return os.path.join(private, "bin"), os.path.join(private, "lib")

    def generate(self):
        VirtualBuildEnv(self).generate()
        rust = self._rust_folder()
        binp, libp = self._runtime_dirs()
        env = Environment()
        env.define("RUSTC", os.path.join(binp, "rustc"))
        env.define("RUSTFLAGS", "--sysroot=%s -C linker=%s" % (rust, self._real_cc(self._compiler())))
        env.define("CARGO_HOME", os.path.join(self.build_folder, "cargo-home"))
        env.define("CARGO_TARGET_DIR", os.path.join(self.build_folder, "cargo-target"))
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        if os.path.isfile(CA_BUNDLE):
            env.define("CARGO_HTTP_CAINFO", CA_BUNDLE)
            env.define("SSL_CERT_FILE", CA_BUNDLE)
        for path in (libp,
                     os.path.join(rust, "lib"),
                     os.path.join(rust, "lib", "rustlib", RUST_TARGET, "lib")):
            env.prepend_path("LD_LIBRARY_PATH", path)
        env.prepend_path("PATH", binp)
        env.vars(self).save_script("rure_env")

    def _sign(self, sign_tool, src, dst):
        proc = subprocess.run(
            [sign_tool, "sign", "-inFile", src, "-outFile", dst, "-selfSign", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0 or not os.path.isfile(dst):
            raise ConanException(
                "binary-sign-tool failed for %s: %s" % (src, (proc.stdout or "")[-2000:]))
        os.chmod(dst, 0o755)

    def _wait_memory(self, min_kb=4 * 1024 * 1024, timeout=240):
        # Loading the OHOS clang/LLVM driver intermittently fails when the
        # shared builder is low on free memory. Wait for a headroom window.
        waited = 0
        while waited < timeout:
            try:
                with open("/proc/meminfo") as fh:
                    info = fh.read()
                free = 0
                avail = 0
                for line in info.splitlines():
                    if line.startswith("MemFree:"):
                        free = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        avail = int(line.split()[1])
                if max(free, avail) >= min_kb:
                    return
            except OSError:
                return
            time.sleep(5)
            waited += 5

    def _clang(self, args, cwd):
        # The driver is invoked with a minimal, explicit environment: Conan
        # buildenv exports (CFLAGS/LDFLAGS/LIBRARY_PATH) leak into the OHOS
        # driver. Loading the large driver/LLVM image can transiently fail on a
        # memory-overcommitted machine, so wait for headroom and retry.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env = {
            "PATH": "/data/service/hnp/bin:/usr/bin:/bin",
            "HOME": os.environ.get("HOME", ""),
            "TMPDIR": tmp,
        }
        last = ""
        for attempt in range(ATTEMPTS):
            self._wait_memory()
            proc = subprocess.run(args, cwd=cwd, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if proc.returncode == 0:
                return proc.stdout or ""
            last = proc.stdout or ""
            time.sleep(2 + attempt)
        raise ConanException("command failed (exit=%s): %s\n%s"
                             % (proc.returncode, " ".join(args), last[-4000:]))

    def _prepare_runtime(self, rust, openssl, cc, sign_tool):
        binp, libp = self._runtime_dirs()
        os.makedirs(binp, exist_ok=True)
        os.makedirs(libp, exist_ok=True)

        # 1) signed cargo / rustc / rustc_driver
        for name in ("cargo", "rustc"):
            self._sign(sign_tool, os.path.join(rust, "bin", name), os.path.join(binp, name))
        drivers = [n for n in os.listdir(os.path.join(rust, "lib"))
                   if n.startswith("librustc_driver-")]
        if len(drivers) != 1:
            raise ConanException("expected exactly one librustc_driver in rust-toolchain")
        self._sign(sign_tool, os.path.join(rust, "lib", drivers[0]),
                   os.path.join(libp, drivers[0]))

        # 2) OpenSSL DSOs relinked from PIC static archives, then signed
        build = self.build_folder
        link_dir = os.path.join(build, "link")
        os.makedirs(link_dir, exist_ok=True)
        raw_crypto = os.path.join(link_dir, "libcrypto.so")
        raw_ssl = os.path.join(link_dir, "libssl.so")
        self._clang([cc, "-shared", "-Wl,-z,relro,-z,now", "-Wl,-soname,libcrypto.so",
                     "-Wl,--whole-archive", os.path.join(openssl, "lib", "libcrypto.a"),
                     "-Wl,--no-whole-archive", "-ldl", "-pthread", "-o", raw_crypto], build)
        self._clang([cc, "-shared", "-Wl,-z,relro,-z,now", "-Wl,-soname,libssl.so",
                     "-Wl,--whole-archive", os.path.join(openssl, "lib", "libssl.a"),
                     "-Wl,--no-whole-archive", "-ldl", "-pthread",
                     "-L" + link_dir, "-lcrypto", "-o", raw_ssl], build)
        self._sign(sign_tool, raw_crypto, os.path.join(libp, "libcrypto.so"))
        self._sign(sign_tool, raw_ssl, os.path.join(libp, "libssl.so"))

        # 3) libz.so (loader dependency of cargo) - signed copy of the system library
        system_z = "/usr/lib/libz.so.1"
        if not os.path.isfile(system_z):
            raise ConanException("system libz.so.1 not found for the cargo runtime")
        self._sign(sign_tool, system_z, os.path.join(libp, "libz.so"))

    def _write_cargo_config(self, cc):
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        lines = [
            "[source.crates-io]",
            'replace-with = "rsproxy-sparse"',
            "[source.rsproxy-sparse]",
            'registry = "sparse+https://rsproxy.cn/index/"',
            "[net]",
            "retry = 10",
            "[http]",
            "timeout = 600",
            "low-speed-limit = 1",
        ]
        if os.path.isfile(CA_BUNDLE):
            lines.append('cainfo = "%s"' % CA_BUNDLE)
        lines += ["", "[target.%s]" % RUST_TARGET, 'linker = "%s"' % cc]
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def _cargo_env(self, rust, binp, libp, cc):
        # Explicit environment for cargo/rustc: the private signed toolchain and
        # DSOs must come first on PATH/LD_LIBRARY_PATH. Passing an explicit dict
        # avoids the Conan buildenv CFLAGS/LDFLAGS leaking into the driver.
        tmp = os.path.join(self.build_folder, "tmp")
        env = os.environ.copy()
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH"):
            env.pop(key, None)
        env.update({
            "RUSTC": os.path.join(binp, "rustc"),
            "RUSTFLAGS": "--sysroot=%s -C linker=%s" % (rust, cc),
            "CARGO_HOME": os.path.join(self.build_folder, "cargo-home"),
            "CARGO_TARGET_DIR": os.path.join(self.build_folder, "cargo-target"),
            "TMPDIR": tmp, "TMP": tmp, "TEMP": tmp,
        })
        if os.path.isfile(CA_BUNDLE):
            env["CARGO_HTTP_CAINFO"] = CA_BUNDLE
            env["SSL_CERT_FILE"] = CA_BUNDLE
        ld = [libp, os.path.join(rust, "lib"),
              os.path.join(rust, "lib", "rustlib", RUST_TARGET, "lib")]
        if os.environ.get("LD_LIBRARY_PATH"):
            ld.append(os.environ["LD_LIBRARY_PATH"])
        env["LD_LIBRARY_PATH"] = os.pathsep.join(ld)
        env["PATH"] = os.pathsep.join([binp, os.path.join(rust, "bin"), os.environ.get("PATH", "")])
        return env

    # ------------------------------------------------------------------ #
    # build
    # ------------------------------------------------------------------ #
    def build(self):
        rust = self._rust_folder()
        openssl = self.dependencies.build["openssl"].package_folder
        cc = self._real_cc(self._compiler())
        sign_tool = os.path.join(os.path.dirname(self._compiler()), "binary-sign-tool")
        if not os.path.isfile(sign_tool):
            raise ConanException("binary-sign-tool not found next to the OHOS clang driver")
        apply_conandata_patches(self)

        binp, _libp = self._runtime_dirs()
        self._prepare_runtime(rust, openssl, cc, sign_tool)
        self._write_cargo_config(cc)

        for d in (os.path.join(self.build_folder, "cargo-home"),
                  os.path.join(self.build_folder, "cargo-target"),
                  os.path.join(self.build_folder, "tmp")):
            os.makedirs(d, exist_ok=True)

        cargo = os.path.join(binp, "cargo")
        crate_dir = self.source_folder
        if not os.path.isfile(os.path.join(crate_dir, "Cargo.toml")):
            raise ConanException("rure crate not found in %s" % crate_dir)
        cargo_env = self._cargo_env(rust, binp, _libp, cc)

        # 1) build the C library (Cargo.toml crate-type = staticlib/cdylib/rlib)
        last = ""
        for attempt in range(4):
            self._wait_memory()
            proc = subprocess.run([cargo, "build", "--release", "--locked"], cwd=crate_dir,
                                  env=cargo_env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True)
            if proc.returncode == 0:
                break
            last = proc.stdout or ""
            self.output.info("cargo attempt %d failed:\n%s" % (attempt + 1, last[-1500:]))
            time.sleep(5 + attempt * 5)
        else:
            raise ConanException("cargo build failed:\n%s" % last[-3000:])

        target_rel = os.path.join(self.build_folder, "cargo-target", "release")
        lib_art = os.path.join(target_rel, "librure.so" if self.options.shared else "librure.a")
        if not os.path.isfile(lib_art):
            raise ConanException("expected cargo artifact missing: %s" % lib_art)

        # 2) upstream test suite (ctest/test.c) - build + run, then report
        test_src = os.path.join(crate_dir, "ctest", "test.c")
        if not os.path.isfile(test_src):
            raise ConanException("upstream test source ctest/test.c missing")
        test_bin = os.path.join(self.build_folder, "rure_ctest")
        self._clang([cc, "-O2", "-I", os.path.join(crate_dir, "include"), test_src,
                     os.path.join(target_rel, "librure.a"), "-o", test_bin,
                     "-lpthread", "-ldl", "-lm"], crate_dir)
        signed_test = test_bin + ".signed"
        self._sign(sign_tool, test_bin, signed_test)
        out = ""
        for attempt in range(6):
            proc = subprocess.run([signed_test], cwd=self.build_folder, env=cargo_env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            out = proc.stdout or ""
            if proc.returncode == 0:
                break
            time.sleep(3 + attempt * 3)
        else:
            raise ConanException("upstream ctest failed (exit=%s):\n%s"
                                 % (proc.returncode, out[-2000:]))
        for line in out.splitlines():
            self.output.info(line)
        passed = [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("PASSED:")]
        failed = [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("FAILED:")]
        upstream = {
            "status": "passed" if not failed and passed else "failed",
            "framework": "upstream-ctest",
            "command": "clang -O2 ctest/test.c librure.a -o rure_ctest && ./rure_ctest",
            "discovered": len(passed) + len(failed),
            "executed": len(passed) + len(failed),
            "passed": len(passed),
            "failed": len(failed),
            "skipped": 0,
            "cases": passed + failed,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        with open(os.path.join(self.build_folder, "hmbs_upstream.json"), "w", encoding="utf-8") as fh:
            json.dump(upstream, fh)
        if failed or not passed:
            raise ConanException("upstream ctest failed (passed=%d, failed=%d)"
                                 % (len(passed), len(failed)))

    # ------------------------------------------------------------------ #
    # package
    # ------------------------------------------------------------------ #
    def package(self):
        target_rel = os.path.join(self.build_folder, "cargo-target", "release")
        copy(self, "librure.so" if self.options.shared else "librure.a",
             target_rel, os.path.join(self.package_folder, "lib"))
        copy(self, "rure.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        for lic in ("LICENSE-MIT", "LICENSE-APACHE", "LICENSE"):
            if os.path.isfile(os.path.join(self.source_folder, lic)):
                copy(self, lic, self.source_folder, os.path.join(self.package_folder, "licenses"),
                     keep_path=False)
        src = os.path.join(self.build_folder, "hmbs_upstream.json")
        if os.path.isfile(src):
            dst = os.path.join(self.package_folder, "res")
            os.makedirs(dst, exist_ok=True)
            copy(self, "hmbs_upstream.json", self.build_folder, dst)

    def package_info(self):
        self.cpp_info.libs = ["rure"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
