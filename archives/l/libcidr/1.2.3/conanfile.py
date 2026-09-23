#!/usr/bin/env python3
"""Conan recipe — libcidr 1.2.3 (plain GNU/BSD Makefile, no configure)."""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibcidrConan(ConanFile):
    name = "libcidr"
    version = "1.2.3"
    description = "Library for manipulating IPv4/IPv6 CIDR netblocks"
    license = "BSD-2-Clause"
    homepage = "https://www.over-yonder.net/~fullermd/projects/libcidr"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcidr supports Linux/OHOS only, got {}".format(self.settings.os)
            )

    def _is_usable_executable(self, path):
        if not path:
            return False
        path = str(path)
        if not os.path.isabs(path):
            return True
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def _resolve_tool(self, key, fallbacks):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get(key)
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for tool_name in fallbacks:
            found = shutil.which(tool_name)
            if found and os.path.isfile(found):
                return found
        for abs_path in ("/data/service/hnp/bin/clang",
                         "/data/service/hnp/bin/llvm-ar",
                         "/data/service/hnp/bin/ar"):
            if fallbacks and os.path.basename(abs_path) in fallbacks:
                if self._is_usable_executable(abs_path):
                    return abs_path
        if cand and self._is_usable_executable(str(cand)):
            return str(cand)
        return fallbacks[0]

    def _sign_if_available(self, path):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            return
        if not os.path.isfile(path):
            return
        tmp_signed = path + ".signed"
        try:
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    sign_tool, path, tmp_signed),
                quiet=True,
            )
            os.replace(tmp_signed, path)
            os.chmod(path, 0o755)
        except Exception as exc:
            self.output.warning("signing {} failed: {}".format(path, exc))
            try:
                if os.path.isfile(tmp_signed):
                    os.remove(tmp_signed)
            except Exception:
                pass

    _CIDR_SOURCES = (
        "cidr_addr.c", "cidr_compare.c", "cidr_from_str.c", "cidr_get.c",
        "cidr_inaddr.c", "cidr_mem.c", "cidr_misc.c", "cidr_net.c",
        "cidr_num.c", "cidr_to_str.c",
    )

    def _resolve_nm(self, cc):
        cands = []
        try:
            cands.append(os.path.join(os.path.dirname(str(cc)), "llvm-nm"))
        except Exception:
            pass
        cands.append("/data/service/hnp/bin/llvm-nm")
        for tool_name in ("llvm-nm", "nm"):
            found = shutil.which(tool_name)
            if found:
                cands.append(found)
        cands.append("nm")
        for cand in cands:
            if cand and os.path.isabs(str(cand)):
                if os.path.isfile(str(cand)) and os.access(str(cand), os.X_OK):
                    return str(cand)
            elif cand and shutil.which(str(cand)):
                return str(cand)
        return None

    def _log_symbol_check(self, path, symbols):
        try:
            size = os.path.getsize(path)
        except Exception:
            size = -1
        nm = self._resolve_nm(self._resolve_tool("c", ["clang", "cc"]))
        if not nm:
            self.output.warning(
                "nm unavailable; skipping export check for {} ({} bytes)".format(path, size))
            return None
        try:
            proc = subprocess.run(
                [nm, "-D", "--defined-only", path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, timeout=60)
            out = proc.stdout or ""
            if proc.returncode != 0 or not out.strip():
                proc = subprocess.run(
                    [nm, "-g", path],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    universal_newlines=True, timeout=60)
                out = proc.stdout or ""
            missing = [s for s in symbols if s not in out]
            self.output.info(
                "exports {}: {} bytes via {} missing={}".format(path, size, nm, missing))
            return not missing
        except Exception as exc:
            self.output.warning("nm check failed for {}: {}".format(path, exc))
            return None

    def _relink_shared_lib(self, cc, src_dir):
        # CI #47997: even with LORDER=echo TSORT=cat (the full .So list is
        # visibly on the `clang -shared` line), CI workers still produce a
        # libcidr.so.0 that exports no symbols (0/114 regression, and
        # binary-sign-tool rejects that file while signing every other ELF
        # fine) — yet the same recipe passes 114/114 on preflight. The only
        # remaining worker-dependent steps are the `.c.So` rule's `ld -r`
        # relocatable link and `clang -shared -Wl,-x`, so bypass the whole
        # upstream link pipeline: compile the 10 sources to PIC objects with
        # CC (known good on every worker — it builds all test programs) and
        # link the .so directly, then verify the key API symbols are really
        # exported. Test programs link by SONAME, so replacing
        # src/libcidr.so.0 after they were built only affects runtime
        # resolution, which is exactly what the regression harness checks.
        fix_dir = os.path.join(src_dir, ".relink")
        try:
            os.makedirs(fix_dir)
        except OSError:
            pass
        objs = []
        for name in self._CIDR_SOURCES:
            obj = os.path.join(fix_dir, name[:-2] + ".o")
            self.run(
                '{} -fpic -DPIC -c -fPIC -O2 -std=c99 -D_XOPEN_SOURCE=600'
                ' -I../include -Iinclude -o "{}" "{}"'.format(cc, obj, name),
                cwd=src_dir)
            objs.append(obj)
        new_so = os.path.join(fix_dir, "libcidr.so.0")
        if os.path.isfile(new_so):
            os.remove(new_so)
        self.run(
            '{} -shared -o "{}" -Wl,-soname,libcidr.so.0 {}'.format(
                cc, new_so, " ".join('"{}"'.format(o) for o in objs)),
            cwd=src_dir)
        ok = self._log_symbol_check(
            new_so, ("cidr_from_str", "cidr_to_str", "cidr_free"))
        # Inspect one upstream `ld -r` object for the record: on the next CI
        # log this tells the `ld -r` step apart from the shared-link step.
        self._log_symbol_check(os.path.join(src_dir, "cidr_from_str.So"),
                               ("cidr_from_str",))
        if ok is False:
            self.output.warning(
                "relinked libcidr.so.0 still exports no symbols; regression is expected to fail")
        lib_file = os.path.join(src_dir, "libcidr.so.0")
        shutil.copy2(new_so, lib_file)
        # Materialize the libcidr.so alias as a real copy: some worker
        # filesystems lack symlink support (runtime resolves by SONAME, so
        # only the .so.0 content matters).
        alias = os.path.join(src_dir, "libcidr.so")
        if os.path.lexists(alias):
            os.remove(alias)
        shutil.copy2(new_so, alias)
        try:
            os.chmod(lib_file, 0o755)
        except Exception:
            pass
        return objs

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _run_regression(self, mkstr_bin, lib_dir):
        arr_path = os.path.join(
            self.source_folder, "src", "test", "regression", "arr.pl")
        with open(arr_path, encoding="utf-8") as handle:
            text = handle.read()
        marker = "'mkstr' => {"
        start = text.find(marker)
        body = text[start + len(marker):] if start >= 0 else text
        input_re = re.compile(r"'([^']+)'\s*=>\s*\[")
        case_re = re.compile(
            r"\{\s*(?:'args'\s*=>\s*'([^']*)'\s*,\s*)?'res'\s*=>\s*'([^']*)'\s*,?\s*\}")
        inputs = list(input_re.finditer(body))
        vectors = []
        for idx, match in enumerate(inputs):
            name = match.group(1)
            if name == "mkstr":
                continue
            end = inputs[idx + 1].start() if idx + 1 < len(inputs) else len(body)
            block = body[match.end():end]
            for case in case_re.finditer(block):
                args = case.group(1) or ""
                expected = case.group(2)
                # Skip the program-name pseudo block if it leaked in.
                if name == "mkstr" and expected == "":
                    continue
                vectors.append((name, args, expected))
        # The file ends with the closing of %TESTS; drop trailing non-vector
        # noise: keep only entries whose expected output looks like a CIDR
        # result, FROMFAILED, or TOFALLED marker from test.pl.
        vectors = [v for v in vectors if v[2] != ""]
        discovered = len(vectors)
        if discovered == 0:
            raise ConanInvalidConfiguration("failed to parse regression vectors from arr.pl")
        env = dict(os.environ)
        lib_path = lib_dir + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = lib_path
        passed = 0
        failed = 0
        failures = []
        for addr, args, expected in vectors:
            cmd = [mkstr_bin, "-_"]
            if args:
                cmd.extend(args.split())
            cmd.append(addr)
            try:
                proc = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    env=env, cwd=self.source_folder, timeout=30,
                    universal_newlines=True)
                out = (proc.stdout or "").strip()
                got = ""
                m_out = re.match(r"^'(.*)' -> '(.*)'$", out)
                if m_out:
                    got = m_out.group(2)
                if proc.returncode == 0 and got == expected:
                    passed += 1
                else:
                    failed += 1
                    if len(failures) < 5:
                        failures.append(
                            "input={!r} args={!r} expected={!r} got={!r} rc={}".format(
                                addr, args, expected, out, proc.returncode))
            except Exception as exc:
                failed += 1
                if len(failures) < 5:
                    failures.append(
                        "input={!r} error={}".format(addr, exc))
        for line in failures:
            self.output.warning("regression mismatch: {}".format(line))
        self.output.info(
            "libcidr regression: {}/{} passed ({} failed)".format(
                passed, discovered, failed))
        return discovered, passed, failed

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_tool("c", ["clang", "cc"])
        if not cc:
            raise ConanInvalidConfiguration("A C compiler is required to build libcidr")
        ar = self._resolve_tool("ar", ["llvm-ar", "ar"])
        if not ar:
            raise ConanInvalidConfiguration("An archiver (llvm-ar or ar) is required to build libcidr")
        self.output.info("libcidr CC={} AR={}".format(cc, ar))
        # Top level builds src + docs manpage + cidrcalc example. GNU make
        # picks GNUmakefile automatically; -j1 per R9. CC is passed on the
        # command line so the Makefile `CC ?= cc` default is overridden
        # (command-line assignments win over `=` in the makefile).
        # LORDER/TSORT override bypasses the BSD tools/lorder script, whose
        # sed/join pipeline breaks on OHOS toybox (CI #47983).
        self.run("make -j1 CC={} LORDER=echo TSORT=cat -C .".format(cc), cwd=self.source_folder)
        # Build the manual test programs (not part of `all`).
        self.run("make -j1 CC={} LORDER=echo TSORT=cat".format(cc),
                 cwd=os.path.join(self.source_folder, "src", "test"))
        src_dir = os.path.join(self.source_folder, "src")
        # CI #47997: even with the full .So list on the link line, CI
        # workers still emit a symbol-less libcidr.so.0 while preflight
        # passes — relink it from freshly compiled PIC objects with CC and
        # verify the exports (see _relink_shared_lib). Test binaries link by
        # SONAME, so replacing src/libcidr.so.0 afterwards is runtime-safe.
        pic_objs = self._relink_shared_lib(cc, src_dir)
        # Best effort: sign build-tree ELFs so they can execute on OHOS.
        lib_file = os.path.join(src_dir, "libcidr.so.0")
        self._sign_if_available(lib_file)
        for prog in ("compare", "inaddr", "kids", "mkstr", "netbc", "nums", "parent"):
            self._sign_if_available(
                os.path.join(src_dir, "test", prog, "cidr_" + prog))
        self._sign_if_available(
            os.path.join(src_dir, "examples", "cidrcalc", "cidrcalc"))
        # Upstream automated suite: src/test/regression (perl test.pl +
        # arr.pl, 114 vectors over cidr_mkstr -_). Perl is not guaranteed
        # on OHOS workers, so run the same vectors with a small python
        # harness against the freshly built cidr_mkstr (low-cost补齐).
        mkstr_bin = os.path.join(src_dir, "test", "mkstr", "cidr_mkstr")
        discovered, passed, failed = self._run_regression(mkstr_bin, src_dir)
        marker = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "perl-regression",
            "command": "python3 regression harness over src/test/regression/arr.pl via src/test/mkstr/cidr_mkstr -_",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(marker)))
        if failed != 0:
            raise ConanInvalidConfiguration(
                "libcidr upstream regression failed: {}/{} passed".format(passed, discovered))
        # Static variant: upstream only builds the shared object, so archive
        # the PIC objects compiled by _relink_shared_lib above — not the
        # `ld -r` .So files, whose provenance differs across worker images.
        if not self.options.shared:
            if not pic_objs:
                raise ConanInvalidConfiguration("no objects found to archive libcidr.a")
            lib_static = os.path.join(src_dir, "libcidr.a")
            if os.path.isfile(lib_static):
                os.remove(lib_static)
            self.run("{} rcs {} {}".format(ar, lib_static, " ".join(
                '"{}"'.format(p) for p in pic_objs)), cwd=self.source_folder)

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        licenses_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "libcidr.h", src=os.path.join(self.source_folder, "include"),
             dst=include_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=licenses_dir)
        if self.options.shared:
            copy(self, "libcidr.so.0", src=src_dir, dst=lib_dir)
            # Deliver the .so alias as a real file copy: the worker
            # filesystem may not support symlinks.
            src_lib = os.path.join(lib_dir, "libcidr.so.0")
            dst_link = os.path.join(lib_dir, "libcidr.so")
            if os.path.isfile(src_lib) and not os.path.isfile(dst_link):
                shutil.copy2(src_lib, dst_link)
        else:
            copy(self, "libcidr.a", src=src_dir, dst=lib_dir)
        copy(self, "cidrcalc", src=os.path.join(src_dir, "examples", "cidrcalc"),
             dst=bin_dir)
        bin_path = os.path.join(bin_dir, "cidrcalc")
        if os.path.isfile(bin_path):
            try:
                os.chmod(bin_path, 0o755)
            except Exception:
                pass
            self._sign_if_available(bin_path)
        copy(self, "libcidr.3", src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(self.package_folder, "share", "man", "man3"))

    def package_info(self):
        self.cpp_info.libs = ["cidr"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
