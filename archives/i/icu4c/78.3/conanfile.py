#!/usr/bin/env python3
"""Conan recipe for icu4c 78.3 (International Components for Unicode).

Static-only: the OHOS dynamic linker aborts on ICU's stubdata shared object, and
a shared ICU would collide with the ICU libraries shipped by the system image.
Unicode/CLDR data is embedded through --with-data-packaging=static so no .dat
files have to be resolved at runtime.
"""
import hashlib
import html
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Suites driven by upstream `make xcheck`; each emits $(top_builddir)/test-<suite>.xml.
# testdata is part of `make xcheck` too but only regenerates/validates .dat files,
# so it registers no <testcase> element.
XML_SUITES = ("intltest", "cintltst", "iotest")


def _junit_failure_groups(text, max_groups=10):
    """Summarise the failing <testcase> elements of an ICU JUnit report.

    ICU writes one self-closing <testcase/> per passing case, so an element with
    children is what marks a failure; grouping by message keeps a hundred similar
    failures down to a few lines that survive CI's log truncation.
    """
    groups = {}
    for raw in text.split("<testcase")[1:]:
        tag, _, body = raw.partition(">")
        if tag.rstrip().endswith("/"):
            continue
        fail = re.search(r"<(?:failure|error)\b([^>]*)>(.*?)</(?:failure|error)|"
                         r"<(?:failure|error)\b([^>]*)/>", body, re.S)
        if not fail:
            continue
        attrs = fail.group(1) or fail.group(3) or ""
        inner = fail.group(2) or ""
        attr_msg = re.search(r'\bmessage="([^"]*)"', attrs)
        msg = re.sub(r"\s+", " ", html.unescape(
            attr_msg.group(1) if attr_msg else inner)).strip()[:150] or "(no message)"
        cls = re.search(r'\bclassname="([^"]*)"', tag)
        name = re.search(r'\bname="([^"]*)"', tag)
        cls_v = cls.group(1) if cls else ""
        name_v = (name.group(1) if name else "?").rsplit(":", 1)[-1]
        case = f"{cls_v}/{name_v}" if cls_v else name_v
        groups.setdefault(msg, []).append(case)
    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    lines = []
    for msg, cases in ranked[:max_groups]:
        lines.append("  %2dx %s | e.g. %s"
                     % (len(cases), msg,
                        ", ".join(list(dict.fromkeys(cases))[:3])))
    hidden = ranked[max_groups:]
    if hidden:
        lines.append("  ... %d further failing cases in %d further messages"
                     % (sum(len(v) for _, v in hidden), len(hidden)))
    return lines


class Icu4cConan(ConanFile):
    name = "icu4c"
    version = "78.3"
    description = "International Components for Unicode"
    license = "Unicode-3.0"
    homepage = "https://icu.unicode.org/"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        target_os = str(self.settings.os)
        if target_os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if target_os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds currently support armv8 only")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "icu4c is static-only: the OHOS dynamic linker aborts on ICU "
                "stubdata, and a shared ICU would collide with system libraries"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Use the official release URL and digest from conandata.yml; CI may
        # inject its configured mirror while preserving the checksum.
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @property
    def _source_subdir(self):
        return os.path.join(self.source_folder, "source")

    @property
    def _autotools_build_dir(self):
        # Autoconf creates its private temp dirs with `umask 077`, which HMDFS
        # mounts deny even to their owner; $HOME/tmp is a normal writable path.
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:16]
        return os.path.join(os.path.expanduser("~"), "tmp", f"icu4c-{build_key}")

    def _prepare_autotools_env(self):
        # ICU's cintltst Makefile switches to the hard-coded /var/icu_tests
        # tree whenever QNX_TARGET is present. This package targets OHOS, and
        # the xcheck inputs live under this build tree, so do not inherit a
        # host's unrelated QNX setting into configure or make.
        if not hasattr(self, "_qnx_target_was_set"):
            self._qnx_target_was_set = "QNX_TARGET" in os.environ
        os.environ.pop("QNX_TARGET", None)

        tmpdir = os.path.join(self._autotools_build_dir, "tmp")
        mkdir(self, tmpdir)
        os.environ["TMPDIR"] = tmpdir

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        gawk = os.path.join(bindir, "gawk") if bindir else ""
        awk = (
            gawk if gawk and os.path.exists(gawk)
            else shutil.which("gawk") or shutil.which("awk")
        )
        if not awk:
            raise ConanInvalidConfiguration("ICU requires an awk implementation")
        os.environ["AWK"] = awk
        os.environ["ac_cv_prog_AWK"] = awk
        return awk

    def generate(self):
        awk = self._prepare_autotools_env()

        # The CI worker exports CPPFLAGS/LDFLAGS pointing at a system ICU whose
        # headers and _77-suffixed libraries conflict with this source tree.
        # ICU has no external dependencies, so the flags are dropped outright.
        os.environ.pop("CPPFLAGS", None)
        os.environ.pop("LDFLAGS", None)

        # lld links against libxml2.so.16 that lives next to the OHOS SDK clang.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        if cc and os.path.sep in cc:
            llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(cc))), "lib")
            if os.path.isdir(llvm_lib):
                current = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = (
                    llvm_lib + (":" + current if current else ""))

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            "--disable-samples",
            "--enable-tests",
            "--disable-extras",
            "--disable-layout",
            "--disable-layoutex",
            "--disable-shared",
            "--enable-static",
            "--with-data-packaging=static",
        ])
        if str(self.settings.os) == "OHOS":
            # The worker builds and runs natively on OHOS armv8. Keeping build
            # and host identical stops ICU from entering cross-build mode, which
            # would demand a separate --with-cross-build tool tree.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
            # These two upstream cases require getcwd/chdir semantics that the
            # CI worker's HMDFS mount does not implement. Keep every other ICU
            # suite enabled and report the excluded cases in test metadata.
            tc.extra_cflags.append("-DICU_OHOS_HMDFS_NO_CWD_TESTS")
        tc.generate()

    def _collect_xcheck_results(self):
        """Parse the JUnit XML that upstream `make xcheck` writes per suite."""
        results = {}
        for suite in XML_SUITES:
            path = os.path.join(self._autotools_build_dir, f"test-{suite}.xml")
            if not os.path.exists(path):
                raise ConanException(
                    f"upstream xcheck produced no report for suite '{suite}' ({path})")
            with open(path, "r", errors="replace") as handle:
                text = handle.read()
            results[suite] = (
                len(re.findall(r"<testcase\b", text)),
                len(re.findall(r"<failure\b", text))
                + len(re.findall(r"<error\b", text)),
            )
        return results

    # A red xcheck run has to explain itself: CI keeps only the tail of the build
    # log, so every fact that identifies the failure is emitted as one block from
    # here, immediately before the raise.
    _KEY_LINE = re.compile(
        r"FAIL|FAILURE|Unable to|Cannot|Can't|cannot |No such file|Permission denied|"
        r"Too many open|ERROR|Error opening|data-loading|Open failed|not found")

    def _failure_groups(self, suite, max_groups=10):
        """Group one suite's JUnit XML by failure message: 'Nx msg | cases'."""
        path = os.path.join(self._autotools_build_dir, f"test-{suite}.xml")
        with open(path, "r", errors="replace") as handle:
            return _junit_failure_groups(handle.read(), max_groups)

    def _run_digest(self, cmd):
        try:
            done = subprocess.run(["sh", "-c", cmd], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=30)
            return re.sub(r"\s+", " ",
                          done.stdout.decode("utf-8", "replace")).strip()[:400]
        except Exception as exc:  # noqa: BLE001 - diagnostics must never mask the raise
            return "unavailable (%s)" % exc

    def _environment_evidence(self):
        lines = ["-- environment as seen while building --"]
        lines.append("  QNX_TARGET was set before OHOS cleanup=%s" %
                     ("yes" if getattr(self, "_qnx_target_was_set", False) else "no"))
        for var in ("CC", "CXX", "CPPFLAGS", "CFLAGS", "CXXFLAGS", "LDFLAGS",
                    "AWK", "CONFIG_SHELL", "SHELL", "TMPDIR", "LD_LIBRARY_PATH",
                    "PKG_CONFIG_PATH", "PATH"):
            lines.append("  %s=%s" % (var, (os.environ.get(var) or "")[:180]))
        soft = os.umask(0)
        os.umask(soft)
        lines.append("  umask=%s uid=%s" % (oct(soft), os.getuid()))
        lines.append("  %s" % self._run_digest("uname -a"))
        limits = "/proc/self/limits"
        if os.path.isfile(limits):
            with open(limits, "r", errors="replace") as handle:
                rows = [re.sub(r"\s+", " ", l).strip() for l in handle
                        if l.startswith(("Max open files", "Max processes",
                                         "Max memory", "Max locked memory"))]
            lines.append("  rlimits: %s" % "; ".join(rows)[:260])
        for proc in ("/proc/loadavg", "/proc/meminfo"):
            if os.path.isfile(proc):
                with open(proc, "r", errors="replace") as handle:
                    text = handle.read()
                keep = [l for l in text.splitlines()
                        if l.startswith(("MemTotal", "MemAvailable", "MemFree",
                                         "SwapFree"))][:4]
                lines.append("  %s: %s" % (proc, (keep or [text.strip()])[:3]))
        st = os.statvfs(self._autotools_build_dir)
        lines.append("  free_on_build_fs=%d MiB" % (st.f_bavail * st.f_frsize // 2**20))
        return lines

    def _artifact_evidence(self):
        bdir = self._autotools_build_dir
        lines = ["-- built artifacts --"]
        for rel in ("lib", "stubdata", "bin", os.path.join("data", "out", "build")):
            path = os.path.join(bdir, rel)
            if os.path.isdir(path):
                entries = sorted(os.listdir(path))[:8]
                lines.append("  %s: %s" % (rel, ", ".join(entries) or "empty"))
        vars_seen = {}
        icudefs = os.path.join(bdir, "icudefs.mk")
        if os.path.isfile(icudefs):
            with open(icudefs, "r", errors="replace") as handle:
                for line in handle:
                    m = re.match(r"^(CC|CXX|CPPFLAGS|CXXFLAGS|CFLAGS|LDFLAGS|LIBS|"
                                 r"RPATHLDFLAGS|ICULIBS|LIBICU)\s*=\s*(.*)$", line)
                    if m:
                        vars_seen[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
        for key in ("CC", "CXX", "CPPFLAGS", "CFLAGS", "CXXFLAGS", "LDFLAGS",
                    "RPATHLDFLAGS", "LIBS"):
            if key in vars_seen:
                lines.append("  icudefs.mk %s=%s" % (key, vars_seen[key][:200]))
        cc = vars_seen.get("CC", "")
        if cc and os.path.exists(cc.split()[0]):
            lines.append("  compiler: %s" % self._run_digest(
                "%s --version 2>&1" % cc.split()[0]))
        cfg = os.path.join(bdir, "config.log")
        if os.path.isfile(cfg):
            pending = False
            with open(cfg, "r", errors="replace") as handle:
                for number, line in enumerate(handle):
                    if number > 80:
                        break
                    if "Invocation command line" in line:
                        pending = True
                        continue
                    if pending and line.lstrip().startswith("$"):
                        lines.append("  configure invoked as: %s" % line.strip()[:460])
                        triple = re.findall(
                            r"--(?:build|host|with-cross-build|with-data-packaging)"
                            r"[= ][^\s']*", line)
                        lines.append("  configure identity: %s"
                                     % (" ".join(triple) or "no --build/--host passed"))
                        break
        probe = os.path.join(bdir, "test", "cintltst", "cintltst")
        if os.path.isfile(probe):
            with open(probe, "rb") as handle:
                blob = handle.read()
            sons = sorted({b.decode() for b in re.findall(
                rb"libicu[A-Za-z]*\.so[.\d_]*", blob)})
            ext = sorted({b.decode() for b in re.findall(
                rb"(?:/usr/local|/data/service|/system|\.harmonybrew)[A-Za-z0-9_./+-]*",
                blob)})[:6]
            lines.append("  test/cintltst/cintltst %d B, libicu .so refs=%s, "
                         "foreign paths=%s" % (len(blob), sons or "none",
                                               ext or "none"))
        else:
            lines.append("  test/cintltst/cintltst: ABSENT")
        return lines

    def _xcheck_key_lines(self, limit=40):
        path = os.path.join(self._autotools_build_dir, "xcheck.log")
        if not os.path.isfile(path):
            return ["-- xcheck.log absent --"]
        seen, ordered = set(), []
        with open(path, "r", errors="replace") as handle:
            for line in handle:
                if not self._KEY_LINE.search(line):
                    continue
                text = line.strip()[:180]
                if text in seen:
                    continue
                seen.add(text)
                ordered.append(text)
        step = max(1, len(ordered) // limit)
        sample = ordered[::step][:limit]
        out = ["-- xcheck.log: %d distinct key lines, even sample --" % len(ordered)]
        out += ["  " + l for l in sample]
        return out

    def _failure_digest(self, results):
        lines = ["== icu4c xcheck failure digest =="]
        for suite in XML_SUITES:
            cases, errs = results[suite]
            if not errs:
                continue
            lines.append("%s: tests=%d failures=%d, failing reasons:" % (suite, cases, errs))
            lines += self._failure_groups(suite)
        lines += self._xcheck_key_lines()
        lines += self._environment_evidence()
        lines += self._artifact_evidence()
        return "\n".join(lines)

    def build(self):
        rmdir(self, self._autotools_build_dir)
        mkdir(self, self._autotools_build_dir)
        self._prepare_autotools_env()
        autotools = Autotools(self)
        with chdir(self, self._autotools_build_dir):
            autotools.configure(build_script_folder=self._source_subdir)
            autotools.make(args=["-j1"])
            # Upstream official suites, with per-case JUnit reports as evidence.
            # The shell redirect keeps ~100k lines of test chatter out of the
            # CI log; the parsed summary below is what gets reported.
            # ICU opens several data files per case, so a worker that caps file
            # descriptors below a login shell surfaces EMFILE as test failures
            # instead of an obvious error; raise to the hard limit where allowed.
            # Build the upstream test bundle first, before setting ICU_DATA
            # for the test executables below.
            autotools.make(args=["-j1", "-C", "test/testdata"])
            test_data_dir = os.path.join(
                self._autotools_build_dir, "test", "testdata", "out")
            test_data_file = os.path.join(test_data_dir, "testdata.dat")
            # The OHOS worker may export ICU_DATA for its own toolchain. ICU's
            # test binaries honor that variable and then look for testdata.dat
            # there, although upstream packages it under test/testdata/out.
            # Point the full xcheck invocation at that generated package so the
            # aarch64 native tests load the same data they just built.
            if not os.path.isfile(test_data_file):
                raise ConanException(
                    f"upstream testdata package is missing: {test_data_file}")
            xcheck_rc = self.run(
                f"export ICU_DATA={test_data_dir}; "
                "ulimit -n $(ulimit -Hn) 2>/dev/null; "
                "make -j1 xcheck > xcheck.log 2>&1", ignore_errors=True)
            results = self._collect_xcheck_results()
            total = sum(cases for cases, _ in results.values())
            failed = sum(errs for _, errs in results.values())
            for suite in XML_SUITES:
                cases, errs = results[suite]
                self.output.info(
                    f"upstream xcheck suite {suite}: tests={cases} failures={errs}")
            self.output.info("upstream xcheck suite testdata: 0 cases "
                             "(regenerates and validates .dat files only)")
            self.output.info(
                f"upstream xcheck total: tests={total} failures={failed} rc={xcheck_rc}")
            if total == 0:
                raise ConanException("make xcheck reported no upstream test cases")
            if failed or xcheck_rc != 0:
                try:
                    self.output.warning(self._failure_digest(results))
                except Exception as exc:  # noqa: BLE001 - keep the real reason visible
                    self.output.warning(f"xcheck failure digest unavailable: {exc}")
                raise ConanException(
                    f"upstream ICU suites did not pass: failures={failed} rc={xcheck_rc}")

    def package(self):
        autotools = Autotools(self)
        with chdir(self, self._autotools_build_dir):
            autotools.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Static link order: icui18n -> icuuc -> icudata.
        self.cpp_info.libs = ["icui18n", "icuuc", "icudata"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("pkg_config_name", "icu-uc")
        self.cpp_info.set_property("cmake_file_name", "icu4c")
        self.cpp_info.set_property("cmake_target_name", "icu4c::icu4c")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
