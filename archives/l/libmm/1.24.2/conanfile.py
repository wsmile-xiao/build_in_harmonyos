#!/usr/bin/env python3
"""Conan recipe — libmm 1.24.2 (Meson).

libmm packages the mm-glib client library from the ModemManager 1.24.2
upstream release (mobile-broadband/ModemManager). mm-glib is the GLib/GObject
client library for managing mobile broadband modems over D-Bus; no daemon is
required at build or link time.

Adapted to HarmonyOS PC (aarch64). Only the mm-glib library target and the
daemon-independent unit tests are built; the ModemManager daemon, CLI tools
and D-Bus integration tests are excluded (the daemon does not compile against
the HarmonyOS SDK: linux/socket.h and sys/socket.h both define
sockaddr_storage, see notes.md and patches/). See notes.md for details.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


# Upstream meson test targets that only depend on library code
# (no ModemManager daemon, no D-Bus session bus):
#   libmm-glib/tests/meson.build -> test-common-helpers, test-pco
#   libqcdm/tests/meson.build    -> test-qcdm
# tools/tests/test-stub needs introspection (disabled here), test/ programs
# are helper executables not registered via test().
UPSTREAM_LIB_TEST_TARGETS = ["test-common-helpers", "test-pco", "test-qcdm"]

# Stdlib-only fallback for build-aux/header-generator.xsl + xsltproc.
# include/meson.build generates ModemManager-names.h via
# `xsltproc --xinclude --nonet` over introspection/all.xml; the OHOS worker
# has no xsltproc (verified: not on PATH, not at /data/service/hnp/bin or
# /usr/bin) and tool_requires(libxslt) pulls CCI recipes with no OHOS source
# entry (KeyError: 'OHOS'). The XSL itself is trivial (upper-case defines
# for node/interface + method/signal/property), so the patched meson.build
# falls back to this script with the same inputs/outputs. Written into
# <source>/build-aux/mm-names-generator.py at build() time.
_MM_NAMES_GENERATOR_PY = '''#!/usr/bin/env python3
"""Stdlib-only replacement for xsltproc on build-aux/header-generator.xsl.
Usage: mm-names-generator.py <introspection/all.xml> <output.h>
Resolves xi:include locally (no network) and emits the same #defines.
"""
import os
import sys
import xml.etree.ElementTree as ET

XI = "{http://www.w3.org/2001/XInclude}"
PREFIX = "org.freedesktop.ModemManager1"
BASE_PREFIX = "org.freedesktop.ModemManager1"


def up(name):
    return name.upper().replace(".", "_").replace(" ", "_")


def intname(iface):
    if iface.startswith(BASE_PREFIX + "."):
        return up(iface[len(BASE_PREFIX) + 1:])
    return "MANAGER"


def collect(all_xml):
    base = os.path.dirname(os.path.abspath(all_xml))
    tree = ET.parse(all_xml)
    root = tree.getroot()
    ifaces = []
    for inc in root.iter(XI + "include"):
        href = inc.get("href")
        if not href:
            continue
        path = os.path.join(base, href)
        try:
            sub = ET.parse(path).getroot()
        except OSError:
            continue
        for node in sub.iter("node"):
            for iface in node.findall("interface"):
                if iface.get("name"):
                    ifaces.append(iface)
        for iface in sub.findall("interface"):
            if iface.get("name"):
                if iface not in ifaces:
                    ifaces.append(iface)
    for node in root.iter("node"):
        for iface in node.findall("interface"):
            if iface.get("name") and iface not in ifaces:
                ifaces.append(iface)
    return ifaces


PROLOGUE = """/* Generated Header file do not edit */

/*
 * ModemManager Interface Specification
 * Version 0.6
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301 USA.
 *
 * Copyright (C) 2008 - 2009 Novell, Inc.
 * Copyright (C) 2009 - 2012 Red Hat, Inc.
 * Copyright (C) 2011 - 2012 Google, Inc.
 * Copyright (C) 2015 - Riccardo Vangelisti riccardo.vangelisti@sadel.it
 * Copyright (C) 2015 - Marco Bascetta marco.bascetta@sadel.it
 */

#ifndef _MODEM_MANAGER_NAMES_H_
#define _MODEM_MANAGER_NAMES_H_

#define MM_DBUS_PATH    "/org/freedesktop/ModemManager1"
#define MM_DBUS_SERVICE "org.freedesktop.ModemManager1"

/* Prefix for object paths */
#define MM_DBUS_MODEM_PREFIX  MM_DBUS_PATH "/Modem"
#define MM_DBUS_BEARER_PREFIX MM_DBUS_PATH "/Bearer"
#define MM_DBUS_CBM_PREFIX MM_DBUS_PATH "/CBM"
#define MM_DBUS_SIM_PREFIX    MM_DBUS_PATH "/SIM"
#define MM_DBUS_SMS_PREFIX    MM_DBUS_PATH "/SMS"
#define MM_DBUS_CALL_PREFIX   MM_DBUS_PATH "/Call"

/* Prefix for DBus errors */
#define MM_DBUS_ERROR_PREFIX "org.freedesktop.ModemManager1.Error"

/**************
 * Interfaces *
 **************/
"""


def main():
    all_xml, out = sys.argv[1], sys.argv[2]
    ifaces = collect(all_xml)
    lines = [PROLOGUE.rstrip("\\n")]
    for iface in ifaces:
        name = iface.get("name")
        if not name.startswith(PREFIX):
            continue
        rest = name[len(PREFIX):]
        varname = up(rest[1:]) if rest.startswith(".") else ""
        macro = "MM_DBUS_INTERFACE" + ("_" + varname if varname else "")
        lines.append('#define %s "%s"' % (macro, name))
    lines.append("")
    lines.append("/******************************")
    lines.append(" * Methods/Signals/Properties *")
    lines.append(" ******************************/")
    for iface in ifaces:
        name = iface.get("name")
        lines.append("/*")
        lines.append(" * Interface '%s'" % name)
        lines.append(" */")
        tag = intname(name)
        for m in iface.findall("method"):
            mn = m.get("name")
            lines.append('#define MM_%s_METHOD_%s "%s"' % (tag, up(mn), mn))
        for s in iface.findall("signal"):
            sn = s.get("name")
            lines.append('#define MM_%s_SIGNAL_%s "%s"' % (tag, up(sn), sn))
        for p in iface.findall("property"):
            pn = p.get("name")
            lines.append('#define MM_%s_PROPERTY_%s "%s"' % (tag, up(pn), pn))
    lines.append("")
    lines.append("#endif /*  _MODEM_MANAGER_NAMES_H_ */")
    lines.append("")
    with open(out, "w", encoding="utf-8", newline="\\n") as fh:
        fh.write("\\n".join(lines))


if __name__ == "__main__":
    main()
'''


class LibmmConan(ConanFile):
    name = "libmm"
    version = "1.24.2"
    description = "mm-glib client library from ModemManager: GLib/GObject API for mobile broadband modem management"
    license = "LGPL-2.1-or-later"
    homepage = "https://modemmanager.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
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

    def requirements(self):
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("dbus/1.14.10", transitive_headers=True, transitive_libs=True)
        # RREV pin (ohpcd): preflight checks conancenter first, so bare
        # expat/zlib resolve to CCI recipes whose tool_requires pulls
        # cmake/4.4.x with no OHOS source entry (KeyError: 'OHOS').
        # Pin to the ohpcd-hardened revisions (debsig-verify/0.34 precedent,
        # same versions) so the graph stays on OHOS-compatible recipes.
        # override=True forces the pin through the transitive edges
        # (dbus -> expat, glib2 -> zlib).
        self.requires("expat/2.8.2#d4cf31cad46d9a206cad68ce0bd8b562", override=True)
        self.requires("zlib/1.3.1#2ee7c0eeb8f4dfef8982d0c5c1551a61", override=True)

    def build_requirements(self):
        # The worker has no system pkg-config on PATH (meson aborts with
        # "Did not find pkg-config by name 'pkg-config'"); provide the
        # pkgconf binary like 20+ meson recipes in this repo (atk, burp2,
        # ayatana-indicator-keyboard, ... all use pkgconf/3.0.5).
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_glib_pkg_config_aliases()
        self._create_dbus_pkg_config_alias()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OHOS has no systemd / polkit / udev / MBIM / QMI / QRTR stacks.
        tc.project_options["bash_completion"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["udev"] = "false"
        tc.project_options["udevdir"] = "/dev/null"
        tc.project_options["systemdsystemunitdir"] = "no"
        tc.project_options["systemd_suspend_resume"] = "false"
        tc.project_options["systemd_journal"] = "false"
        tc.project_options["polkit"] = "no"
        tc.project_options["mbim"] = "false"
        tc.project_options["qmi"] = "false"
        tc.project_options["qrtr"] = "false"
        # Enable the upstream unit-test targets (libmm-glib/tests,
        # libqcdm/tests); they are executed in build() via meson test.
        tc.project_options["tests"] = "true"
        tc.generate()
        self._repair_meson_compiler_paths()
        self._inject_archive_tools()

    def build(self):
        apply_conandata_patches(self)
        self._write_mm_names_generator()
        self._patch_include_meson_build()
        meson = Meson(self)
        meson.configure()
        # Build only the mm-glib library. The ModemManager daemon in src/
        # does not compile against the HarmonyOS SDK (sockaddr_storage is
        # defined by both linux/socket.h and sys/socket.h), so a full
        # default build is not possible on OHOS; see notes.md.
        meson.build(target="mm-glib")
        # Build the daemon-independent upstream unit tests.
        for target in UPSTREAM_LIB_TEST_TARGETS:
            meson.build(target=target)
        self._run_upstream_tests()

    def _patch_include_meson_build(self):
        meson_build = os.path.join(self.source_folder, "include", "meson.build")
        with open(meson_build, encoding="utf-8") as handle:
            content = handle.read()
        if "xsltproc = find_program" in content:
            return
        old_block = (
            "mm_names_header = configure_file(\n"
            "  input: [build_aux_dir / 'header-generator.xsl', mm_ifaces_all],\n"
            "  output: header,\n"
            "  command: [find_program('xsltproc'), '--xinclude', '--nonet', '--output', '@OUTPUT@', '@INPUT@'],\n"
            "  install: true,\n"
            "  install_dir: mm_pkgincludedir,\n"
            ")\n"
        )
        new_block = (
            "xsltproc = find_program('xsltproc', required : false)\n"
            "if xsltproc.found()\n"
            "  mm_names_header = configure_file(\n"
            "    input: [build_aux_dir / 'header-generator.xsl', mm_ifaces_all],\n"
            "    output: header,\n"
            "    command: [xsltproc, '--xinclude', '--nonet', '--output', '@OUTPUT@', '@INPUT@'],\n"
            "    install: true,\n"
            "    install_dir: mm_pkgincludedir,\n"
            "  )\n"
            "else\n"
            "  mm_names_header_py = find_program('python3', required : true)\n"
            "  mm_names_header = configure_file(\n"
            "    input: mm_ifaces_all,\n"
            "    output: header,\n"
            "    command: [mm_names_header_py, build_aux_dir / 'mm-names-generator.py', '@INPUT@', '@OUTPUT@'],\n"
            "    install: true,\n"
            "    install_dir: mm_pkgincludedir,\n"
            "  )\n"
            "endif\n"
        )
        if old_block not in content:
            raise ConanInvalidConfiguration(
                "include/meson.build xsltproc block not found; upstream layout drifted")
        content = content.replace(old_block, new_block, 1)
        with open(meson_build, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("patched include/meson.build with xsltproc python fallback")

    def _write_mm_names_generator(self):
        """Stage the stdlib-only fallback used by the patched meson.build."""
        target_dir = os.path.join(self.source_folder, "build-aux")
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError:
            pass
        target = os.path.join(target_dir, "mm-names-generator.py")
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_MM_NAMES_GENERATOR_PY)

    def _run_upstream_tests(self):
        """Run upstream meson unit tests and emit the HMBS evidence marker.

        Only the daemon-independent tests (UPSTREAM_LIB_TEST_TARGETS) are
        executed: a bare ``meson test`` tries all 29 registered tests and
        aborts with "test-shared-icera does not exist. Cannot run tests
        before building them" because the ModemManager daemon in src/ does
        not compile on OHOS (sockaddr_storage conflict, see notes.md), so
        its plugin/integration test binaries are never built. Counts for
        the executed tests come from the single deterministic source
        <build>/meson_test_stdout.txt (plus structured meson-logs/
        testlog.json when present); discovered comes from
        ``meson introspect --tests`` (deterministic JSON list); the 26
        unbuilt daemon/plugin tests are reported as ohos_feature gaps.
        No guessing or arithmetic fix-ups. The result is also persisted to
        <build>/upstream_test_result.json so package() can ship it.

        No shell is used here (device /tmp is read-only erofs, dcap
        precedent): subprocess list-form writes the log via Python.
        """
        log_file = os.path.join(self.build_folder, "meson_test_stdout.txt")
        tmp_dir = self._ensure_writable_tmp()
        env = dict(os.environ)
        env["TMPDIR"] = tmp_dir
        env["TMP"] = tmp_dir
        env["TEMP"] = tmp_dir
        env["SHELL"] = "/bin/sh"
        meson_bin = shutil.which("meson") or "meson"
        test_cmd = (["test", "-C", self.build_folder, "--no-rebuild",
                     "--print-errorlogs"] + UPSTREAM_LIB_TEST_TARGETS)
        argv = [meson_bin] + test_cmd
        self.output.info("upstream meson test exec: " + " ".join(argv))
        try:
            proc = subprocess.run(argv, cwd=self.build_folder, env=env,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True)
            output = proc.stdout if proc.stdout is not None else ""
            self.output.info(
                "upstream meson test exit: {}".format(proc.returncode))
        except OSError as exc:
            output = "meson test exec failed: {!r}\n".format(exc)
            self.output.warning(output.strip())
        # Diagnostic tail: the preflight summary hides the captured stdout,
        # so emit the last lines plus the meson-logs tree; the next round
        # can then see the real meson error instead of guessing.
        try:
            tail = "\n".join(output.splitlines()[-60:])
            if tail.strip():
                for chunk in tail.splitlines():
                    self.output.info("meson-test-out: " + chunk)
            else:
                self.output.warning("meson-test-out: <empty stdout>")
            logs_dir = os.path.join(self.build_folder, "meson-logs")
            try:
                entries = sorted(os.listdir(logs_dir))
            except OSError as exc:
                self.output.warning(
                    "meson-logs list failed: {!r}".format(exc))
            else:
                self.output.info(
                    "meson-logs entries: " + ", ".join(entries[:40]))
                for name in ("testlog.txt", "testlog.json", "meson-log.txt"):
                    path = os.path.join(logs_dir, name)
                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        self.output.info(
                            "meson-logs {}: missing".format(name))
                    else:
                        self.output.info(
                            "meson-logs {}: {} bytes".format(name, size))
            # Registered-test introspection (diagnostic only, not a marker
            # source): shows whether the audit total of 3 matches the
            # configured build, independent of the test run outcome.
            try:
                intro = subprocess.run(
                    [meson_bin, "introspect", self.build_folder, "--tests"],
                    cwd=self.build_folder, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=120)
                intro_out = intro.stdout or ""
                try:
                    intro_tests = json.loads(intro_out) if intro_out.strip() else []
                except ValueError:
                    intro_tests = []
                if isinstance(intro_tests, list):
                    names = [str(t.get("name", "?")) for t in intro_tests
                             if isinstance(t, dict)][:20]
                    self.output.info(
                        "meson introspect tests: {} [{}]".format(
                            len(intro_tests), ", ".join(names)))
                else:
                    self.output.info("meson introspect tests: non-list payload")
            except Exception as exc:
                self.output.warning(
                    "meson introspect failed: {!r}".format(exc))
        except Exception as exc:
            self.output.warning("meson test diagnostics failed: {!r}".format(exc))
        try:
            with open(log_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(output)
        except OSError as exc:
            self.output.warning(
                "cannot write meson test log {}: {!r}".format(log_file, exc))
        result = self._parse_meson_test_log(log_file)
        # Discovered total comes from introspect (deterministic JSON list,
        # single source for that field); the executed subset keeps its own
        # parsed counts. The 26 unbuilt tests need the src/ daemon which
        # does not compile on OHOS, reported as ohos_feature gaps.
        total = 0
        unbuilt_names = []
        try:
            intro2 = subprocess.run(
                [meson_bin, "introspect", self.build_folder, "--tests"],
                cwd=self.build_folder, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=120)
            payload = json.loads(intro2.stdout) if intro2.stdout.strip() else []
            if isinstance(payload, list) and payload:
                total = len(payload)
                executed_names = set(UPSTREAM_LIB_TEST_TARGETS)
                for entry in payload:
                    name = str(entry.get("name", "")) if isinstance(entry, dict) else ""
                    if name and name not in executed_names:
                        unbuilt_names.append(name)
        except Exception as exc:
            self.output.warning("meson introspect total failed: {!r}".format(exc))
        if total > 0:
            result["command"] = ("meson test " + " ".join(UPSTREAM_LIB_TEST_TARGETS)
                                 + " --no-rebuild --print-errorlogs")
            result["discovered"] = total
            executed = int(result.get("executed", 0))
            # Single deterministic source for the unbuilt count: the
            # introspect name list minus the executed targets (no arithmetic
            # patch-ups on stdout substrings). Falls back to total-executed
            # only when the introspect payload gave no names.
            if unbuilt_names:
                unbuilt = len(unbuilt_names)
            else:
                unbuilt = total - executed
            if unbuilt > 0:
                detail = (str(unbuilt) + " daemon/plugin tests unbuilt on OHOS "
                          "(src/ daemon fails: linux/socket.h vs sys/socket.h "
                          "sockaddr_storage conflict); only the 3 "
                          "daemon-independent lib tests were executed")
                gaps = result.get("gaps")
                if not isinstance(gaps, list):
                    gaps = []
                gaps.append({
                    "count": unbuilt,
                    "category": "ohos_feature",
                    "detail": detail,
                    "evidence": ("meson introspect --tests lists {}: executed [{}]; "
                                 "unbuilt [{}]").format(
                                     total, ", ".join(UPSTREAM_LIB_TEST_TARGETS),
                                     ", ".join(sorted(unbuilt_names))),
                })
                result["gaps"] = gaps
                # rule4: status must be incomplete (catch2/libm2k precedent)
                # whenever gaps exist; passed requires executed == discovered.
                result["status"] = "incomplete"
                result["reason"] = (
                    "only {}/{} upstream meson tests executed on OHOS; {} "
                    "daemon/plugin tests unbuilt (src/ daemon does not compile "
                    "against the HarmonyOS SDK)".format(executed, total, unbuilt))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, sort_keys=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, sort_keys=True))

    def _ensure_writable_tmp(self):
        """Return a writable temp dir (device /tmp is read-only erofs)."""
        candidates = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.environ.get(key)
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        try:
            base = getattr(self, "build_folder", None)
            if base:
                local_tmp = os.path.join(str(base), "tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_wtest")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("w")
                os.remove(probe)
                return cand
            except OSError:
                continue
        fallback = os.path.join(str(self.build_folder), "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
            return fallback
        except OSError:
            return "/tmp"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)

    @staticmethod
    def _parse_meson_testlog_json(build_dir):
        """Parse meson-logs/testlog.json (structured, no string counting)."""
        path = os.path.join(build_dir, "meson-logs", "testlog.json")
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            return None
        entries = payload if isinstance(payload, list) else payload.get("tests", None)
        if not isinstance(entries, list) or not entries:
            return None
        passed = failed = skipped = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw = str(entry.get("result", entry.get("status", ""))).upper()
            if raw in ("OK", "EXPECTEDFAIL", "EXPECTED_FAIL", "PASS"):
                passed += 1
            elif raw in ("SKIP", "SKIPPED"):
                skipped += 1
            elif raw:
                failed += 1
            else:
                failed += 1
        executed = passed + failed + skipped
        if executed == 0:
            return None
        return passed, failed, skipped, executed, path

    @staticmethod
    def _parse_meson_test_log(log_file):
        searched = [log_file]
        build_dir = os.path.dirname(log_file)
        structured = LibmmConan._parse_meson_testlog_json(build_dir)
        if structured is not None:
            passed, failed, skipped, executed, json_path = structured
            searched.append(json_path)
            result = {
                "status": "passed" if failed == 0 else "failed",
                "framework": "meson",
                "command": "meson test --no-rebuild --print-errorlogs",
                "discovered": executed,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
            if failed:
                result["gaps"] = [{
                    "count": failed,
                    "category": "test_failure",
                    "detail": "upstream meson unit test(s) failed on OHOS; see meson test log tail in build output",
                    "evidence": json_path,
                }]
            return result
        counts = {"ok": 0, "fail": 0, "skipped": 0}
        found = False
        try:
            with open(log_file, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            content = ""
        content = LibmmConan._strip_ansi(content)
        if not content.strip():
            testlog = os.path.join(build_dir, "meson-logs", "testlog.txt")
            searched.append(testlog)
            try:
                with open(testlog, encoding="utf-8", errors="replace") as handle:
                    content = LibmmConan._strip_ansi(handle.read())
            except OSError:
                content = ""
        for line in content.splitlines():
            match = re.match(
                r"^(Ok|Fail|Expected Fail|Timeout|Skipped|Unexpected Pass|ERROR)\s*:\s*(\d+)\s*$",
                line.strip(),
            )
            if not match:
                continue
            found = True
            kind, number = match.group(1), int(match.group(2))
            if kind in ("Ok", "Expected Fail"):
                counts["ok"] += number
            elif kind == "Skipped":
                counts["skipped"] += number
            else:
                counts["fail"] += number
        passed = counts["ok"]
        failed = counts["fail"]
        skipped = counts["skipped"]
        executed = passed + failed + skipped
        if not found:
            return {
                "status": "failed",
                "framework": "meson",
                "command": "meson test --no-rebuild --print-errorlogs",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "no meson test summary found; searched: " + ", ".join(searched),
            }
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "meson",
            "command": "meson test --no-rebuild --print-errorlogs",
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if failed:
            result["gaps"] = [{
                "count": failed,
                "category": "test_failure",
                "detail": "upstream meson unit test(s) failed on OHOS; see meson test log tail in build output",
                "evidence": log_file,
            }]
        return result

    def package(self):
        self._install_mm_glib()
        # Ship the upstream test evidence so test_package can re-emit the
        # marker on cache hits (when build() is skipped as "Already installed").
        evidence = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(evidence):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            shutil.copyfile(evidence, os.path.join(res_dir, "upstream_test_result.json"))

    def _install_mm_glib(self):
        """Install the mm-glib library without running the full meson install.

        A full meson install would also install the ModemManager daemon, CLI
        and D-Bus policy files, whose targets are intentionally not built on
        OHOS. Only the versioned shared/static library, public headers,
        generated headers and pkg-config files are staged.
        """
        build_lib_dir = os.path.join(self.build_folder, "libmm-glib")
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        staged = 0
        for pattern in ("libmm-glib.so*", "libmm-glib.a"):
            for candidate in sorted(glob.glob(os.path.join(build_lib_dir, pattern))):
                self._stage_file(candidate,
                                 os.path.join(lib_dir, os.path.basename(candidate)))
                staged += 1
        if staged == 0:
            raise ConanInvalidConfiguration(
                "mm-glib library not found in {}".format(build_lib_dir))

        include_dir = os.path.join(self.package_folder, "include", "libmm-glib")
        os.makedirs(include_dir, exist_ok=True)
        source_lib_dir = os.path.join(self.source_folder, "libmm-glib")
        for candidate in sorted(glob.glob(os.path.join(source_lib_dir, "*.h"))):
            self._stage_file(candidate,
                             os.path.join(include_dir, os.path.basename(candidate)))
        # Generated headers (enum types, gdbus glue) live next to the build,
        # including in subdirectories (mm-gdbus-*.h via gdbus-codegen).
        # test_package failed with "'mm-gdbus-cbm.h' file not found" because
        # only top-level <build>/libmm-glib/*.h was staged.
        for candidate in sorted(glob.glob(
                os.path.join(build_lib_dir, "**", "*.h"), recursive=True)):
            target = os.path.join(include_dir, os.path.basename(candidate))
            if not os.path.isfile(target):
                self._stage_file(candidate, target)
        # Umbrella include dir if upstream provides one.
        source_include_dir = os.path.join(self.source_folder, "include")
        if os.path.isdir(source_include_dir):
            for candidate in sorted(glob.glob(os.path.join(source_include_dir, "*.h"))):
                self._stage_file(candidate,
                                 os.path.join(self.package_folder, "include",
                                              os.path.basename(candidate)))
        # Generated ModemManager-names.h (include/meson.build configure_file
        # via xsltproc or the python fallback) lands under <build>/include/;
        # test_package failed with "'ModemManager-names.h' file not found"
        # because only <build>/libmm-glib/*.h was staged. Stage the whole
        # build include dir plus a recursive fallback for the names header.
        build_include_dir = os.path.join(self.build_folder, "include")
        if os.path.isdir(build_include_dir):
            for candidate in sorted(glob.glob(
                    os.path.join(build_include_dir, "*.h"))):
                target = os.path.join(self.package_folder, "include",
                                      os.path.basename(candidate))
                if not os.path.isfile(target):
                    self._stage_file(candidate, target)
        for candidate in sorted(glob.glob(
                os.path.join(self.build_folder, "**", "ModemManager-names.h"),
                recursive=True)):
            target = os.path.join(self.package_folder, "include",
                                  os.path.basename(candidate))
            if not os.path.isfile(target):
                self._stage_file(candidate, target)
            break

        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        staged_pc = 0
        for pattern in ("mm-glib.pc", "ModemManager.pc"):
            matches = sorted(glob.glob(
                os.path.join(self.build_folder, "**", pattern), recursive=True))
            if matches:
                target = os.path.join(pkgconfig_dir, pattern)
                if not os.path.isfile(target):
                    self._stage_file(matches[0], target)
                    staged_pc += 1
        if staged_pc == 0:
            self._write_mm_glib_pc(pkgconfig_dir)

    @staticmethod
    def _stage_file(source, target):
        """Stage a file preserving symlinks when the filesystem allows them."""
        if os.path.islink(source):
            link_target = os.readlink(source)
            try:
                if os.path.islink(target) or os.path.isfile(target):
                    os.unlink(target)
                os.symlink(link_target, target)
                return
            except OSError:
                pass
        shutil.copyfile(source, target)

    def _write_mm_glib_pc(self, pkgconfig_dir):
        """Fallback mm-glib.pc used only when meson generated none."""
        with open(os.path.join(pkgconfig_dir, "mm-glib.pc"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(
                "prefix=${pcfiledir}/../..\n"
                "exec_prefix=${prefix}\n"
                "libdir=${exec_prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: mm-glib\n"
                "Description: Library to control and monitor the ModemManager\n"
                "Version: 1.24.2\n"
                "Requires: gio-2.0 glib-2.0 gobject-2.0\n"
                "Libs: -L${libdir} -lmm-glib\n"
                "Cflags: -I${includedir} -I${includedir}/libmm-glib\n"
            )

    def package_info(self):
        self.cpp_info.libs = ["mm-glib"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "libmm-glib")]
        self.cpp_info.requires = ["glib2::glib2", "dbus::dbus"]
        self.cpp_info.set_property("pkg_config_name", "mm-glib")
        self.cpp_info.set_property("cmake_file_name", "mm-glib")
        self.cpp_info.set_property("cmake_target_name", "mm-glib::mm-glib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _create_glib_pkg_config_aliases(self):
        """Alias gio/gobject/gio-unix .pc files and stage glib build tools.

        Adapted from the libaccounts-glib recipe: PkgConfigDeps emits a single
        glib-2.0.pc while ModemManager configure queries gio-2.0, gobject-2.0
        and gio-unix-2.0, and the build runs glib-mkenums + gdbus-codegen.
        """
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()

        for variable, executable in {
            "glib_genmarshal": "glib-genmarshal",
            "glib_mkenums": "glib-mkenums",
            "gdbus_codegen": "gdbus-codegen",
        }.items():
            if not re.search(rf"^{variable}=", content, flags=re.M):
                tool = self._stage_glib_tool(content, executable)
                content = content.replace(
                    "\nName:",
                    f"\n{variable}={tool}\nName:",
                    1,
                )

        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)

        for filename, name in {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
        }.items():
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(os.path.join(self.generators_folder, filename),
                      "w", encoding="utf-8") as target:
                target.write(alias)

        prefix_match = re.search(r"^prefix=(.+)$", content, flags=re.M)
        prefix = prefix_match.group(1).strip() if prefix_match else "${pcfiledir}"
        with open(os.path.join(self.generators_folder, "gio-unix-2.0.pc"),
                  "w", encoding="utf-8") as target:
            target.write(
                f"prefix={prefix}\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: gio-unix-2.0\n"
                f"Description: unix specific headers for glib I/O library\n"
                f"Version: 2.88.0\n"
                f"Requires: gobject-2.0 gio-2.0\n"
                f"Cflags: -I${{includedir}}/gio-unix-2.0\n"
            )

    def _create_dbus_pkg_config_alias(self):
        """Alias dbus-1.pc from the PkgConfigDeps dbus.pc."""
        # The dbus recipe declares no pkg_config_name, so PkgConfigDeps
        # emits dbus.pc while ModemManager queries dbus-1 (same situation
        # as the accountsservice recipe, same alias solution). Copy and
        # rename so Libs/Cflags/Requires always track the real dependency.
        dbus_pc = os.path.join(self.generators_folder, "dbus.pc")
        if not os.path.isfile(dbus_pc):
            self.output.warning(
                "dbus.pc not generated by PkgConfigDeps; "
                "skipping dbus-1.pc alias")
            return
        with open(dbus_pc, encoding="utf-8") as source:
            content = source.read()
        alias = re.sub(r"^Name:.*$", "Name: dbus-1", content, flags=re.M)
        with open(os.path.join(self.generators_folder, "dbus-1.pc"),
                  "w", encoding="utf-8") as target:
            target.write(alias)

    def _repair_meson_compiler_paths(self):
        """Rewrite dead conf compiler paths in the meson machine files.

        The profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang, which is absent on some workers
        (meson aborts with "Unknown compiler(s)" + ENOENT on --version).
        Same fallback principle as the ayatana-ido CMake recipe and the
        local _inject_archive_tools ar/ranlib fix: keep the conf path
        when the file exists and is executable, otherwise rewrite the
        generated conan_meson_{native,cross}.ini entries to the
        PATH-resolved compiler, preserving any extra args. Raises only
        when no runnable compiler exists at all (infra fault).
        """
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            executables = {}
        conf_c = executables.get("c")
        conf_cxx = (executables.get("cpp") or executables.get("cxx")
                    or executables.get("c++"))

        def _usable(path):
            try:
                return (bool(path) and os.path.isfile(str(path))
                        and os.access(str(path), os.X_OK))
            except Exception:
                return False

        if _usable(conf_c) and (_usable(conf_cxx) or not conf_cxx):
            return
        fallback_c = shutil.which("clang") or shutil.which("cc")
        fallback_cxx = (shutil.which("clang++") or shutil.which("c++")
                        or fallback_c)
        if not fallback_c:
            raise ConanInvalidConfiguration(
                "Meson needs a C compiler: conf c={!r} is not executable "
                "and no clang/cc on PATH".format(conf_c))
        self.output.warning(
            "conf compiler c={!r} cxx={!r} unusable; rewriting meson "
            "machine files to c={!r} cxx={!r}".format(
                conf_c, conf_cxx, fallback_c, fallback_cxx))
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            original = content
            if conf_c and str(conf_c) in content:
                content = content.replace(str(conf_c), fallback_c)
            if conf_cxx and fallback_cxx and str(conf_cxx) in content:
                content = content.replace(str(conf_cxx), fallback_cxx)
            if content != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)

    @staticmethod
    def _tool_usable(path):
        """True when path (bare or with args) points at an executable file."""
        if not path:
            return False
        first = str(path).split()[0].strip("'\"") if isinstance(path, str) else ""
        if not first:
            return False
        try:
            return os.path.isfile(first) and os.access(first, os.X_OK)
        except Exception:
            return False

    @staticmethod
    def _resolve_tool(candidates):
        for candidate in candidates:
            if candidate and LibmmConan._tool_usable(candidate):
                return candidate.split()[0].strip("'\"") if isinstance(candidate, str) else candidate
        return ""

    def _inject_archive_tools(self):
        """Repair ar/ranlib/strip/pkg-config in both meson machine files.

        The profile (or MesonToolchain default) writes
        /data/service/hnp/bin/ar, which is absent on some workers;
        meson aborts at configure with "Unknown linker(s)" + ENOENT on
        `ar --version`. The previous inject-only-when-missing logic left
        that dead entry untouched (early return on "\\nar =") and never
        patched conan_meson_cross.ini, so the same failure survived the
        compiler-path fix. This repair validates every existing entry and
        replaces dead paths with PATH-resolved tools in both files.
        The worker likewise has no system pkg-config on PATH, so the
        pkgconf build requirement is recorded under the 'pkg-config' key
        (atk recipe precedent) and the PkgConfigDeps output dirs are
        merged into pkg_config_path.
        """
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            executables = {}
        conf_ar = executables.get("ar", "")
        conf_ranlib = executables.get("ranlib", "")
        conf_strip = executables.get("strip", "")
        good_ar = (conf_ar if self._tool_usable(conf_ar)
                   else self._resolve_tool([shutil.which("llvm-ar"),
                                            shutil.which("ar")]))
        good_ranlib = (conf_ranlib if self._tool_usable(conf_ranlib)
                       else self._resolve_tool([shutil.which("llvm-ranlib"),
                                                shutil.which("ranlib")]))
        good_strip = (conf_strip if self._tool_usable(conf_strip)
                      else self._resolve_tool([shutil.which("llvm-strip"),
                                               shutil.which("strip")]))
        if not good_ar:
            raise ConanInvalidConfiguration(
                "Meson needs ar: conf ar={!r} is not executable and no "
                "llvm-ar/ar on PATH".format(conf_ar))
        goods = {"ar": good_ar}
        if good_ranlib:
            goods["ranlib"] = good_ranlib
        if good_strip:
            goods["strip"] = good_strip
        pkg_config = self._resolve_pkg_config()
        if not pkg_config:
            raise ConanInvalidConfiguration(
                "Meson needs pkg-config/pkgconf for the gio-unix-2.0 lookup: "
                "no usable tools.gnu:pkg_config, no pkg-config/pkgconf on "
                "PATH and no pkgconf build requirement")
        # xsltproc is handled separately (see _write_mm_names_generator +
        # _patch_include_meson_build): include/meson.build falls back to a stdlib-only
        # python generator when xsltproc is absent, so no hard failure here.
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            original = content
            for tool, good in goods.items():
                pattern = re.compile(
                    r"^(\s*" + tool + r"\s*=\s*)(['\"]?)(.*?)(\2)\s*$",
                    flags=re.M)
                match = pattern.search(content)
                if match:
                    current = match.group(3).strip()
                    # Entry may be a meson list like ['/x/ar'] or plain path.
                    inner = re.findall(r"'([^']+)'|\"([^\"]+)\"|(\S+)", current)
                    first = ""
                    if inner:
                        for single, double, bare in inner:
                            first = single or double or bare
                            if first and first != good:
                                # Keep scanning; first token decides.
                                break
                    else:
                        first = current.split()[0] if current.split() else ""
                    first = first.strip("'\"") if isinstance(first, str) else ""
                    if first and first != good and not self._tool_usable(first):
                        self.output.warning(
                            "meson {} {!r} unusable in {}; rewriting to {!r}".format(
                                tool, first, filename, good))
                        content = pattern.sub(
                            lambda m, _g=good: m.group(1) + "'" + _g + "'",
                            content, count=1)
                elif "[binaries]" in content:
                    self.output.warning(
                        "meson {} missing in {}; injecting {!r}".format(
                            tool, filename, good))
                    content = content.replace(
                        "[binaries]\n",
                        "[binaries]\n{} = '{}'\n".format(tool, good), 1)
            content = self._ensure_pkg_config_entry(content, filename, pkg_config)
            content = self._ensure_pkg_config_path(content)
            # Belt-and-braces: the known dead toolchain prefix may appear
            # inside list syntax (e.g. ar = ['/data/service/hnp/bin/ar'])
            # that the line regex above already covered, or inside an
            # unexpected key; replace the exact dead substring when its
            # target is not executable.
            for dead in ("/data/service/hnp/bin/ar",
                         "/data/service/hnp/bin/llvm-ranlib",
                         "/data/service/hnp/bin/ranlib"):
                tool = "ar" if dead.endswith("/ar") else (
                    "ranlib" if "ranlib" in dead else "strip")
                good = goods.get(tool, "")
                if dead in content and good and not self._tool_usable(dead):
                    content = content.replace(dead, good)
            if content != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _resolve_pkg_config(self):
        """Locate a usable pkg-config compatible binary.

        Order: conf tools.gnu:pkg_config, PATH (pkg-config, then pkgconf),
        then the pkgconf build-requirement package folder (bin/pkgconf).
        """
        try:
            conf_pc = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            conf_pc = None
        if conf_pc and self._tool_usable(conf_pc):
            return str(conf_pc).split()[0]
        found = shutil.which("pkg-config") or shutil.which("pkgconf")
        if found and self._tool_usable(found):
            return found
        try:
            build_deps = self.dependencies.build
        except Exception:
            build_deps = None
        if build_deps is not None:
            try:
                pkgconf = build_deps["pkgconf"]
            except Exception:
                pkgconf = None
            if pkgconf is not None:
                for name in ("pkgconf", "pkg-config"):
                    candidate = os.path.join(
                        pkgconf.package_folder, "bin", name)
                    if self._tool_usable(candidate):
                        return candidate
        return ""

    def _ensure_pkg_config_entry(self, content, filename, pkg_config):
        """Point meson at the pkg-config binary (atk recipe precedent).

        Meson only probes the literal name 'pkg-config'; the pkgconf
        package ships bin/pkgconf, so record it under the 'pkg-config'
        key. A dead existing entry is rewritten, a missing one injected.
        """
        if "[binaries]" not in content:
            return content
        if ("\npkg-config =" not in content
                and "\npkgconfig =" not in content):
            self.output.warning(
                "meson pkg-config missing in {}; injecting {!r}".format(
                    filename, pkg_config))
            return content.replace(
                "[binaries]\n",
                "[binaries]\npkg-config = '{}'\n".format(pkg_config), 1)
        for key in ("pkg-config", "pkgconfig"):
            pattern = re.compile(
                r"^(\s*" + key + r"\s*=\s*)(['\"]?)(.*?)(\2)\s*$",
                flags=re.M)
            match = pattern.search(content)
            if not match:
                continue
            current = (match.group(3) or "").strip().split()
            first = current[0].strip("'\"") if current else ""
            if first and first != pkg_config and not self._tool_usable(first):
                self.output.warning(
                    "meson {} {!r} unusable in {}; rewriting to {!r}".format(
                        key, first, filename, pkg_config))
                content = pattern.sub(
                    lambda m: m.group(1) + "'" + pkg_config + "'",
                    content, count=1)
        return content

    def _ensure_pkg_config_path(self, content):
        """Merge generators folder and host deps' pkgconfig dirs.

        Same defensive merge as the atk recipe: guarantees the
        PkgConfigDeps .pc files (glib-2.0, gio aliases, dbus) stay
        visible to the pkg-config binary recorded above.
        """
        paths = [self.generators_folder]
        try:
            host_deps = self.dependencies.host.values()
        except Exception:
            host_deps = []
        for dependency in host_deps:
            try:
                folder = dependency.package_folder
            except Exception:
                continue
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        replacement = "pkg_config_path = [" + ", ".join(
            "'{}'".format(path) for path in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        return "\n".join(lines) + "\n"

    def _stage_glib_tool(self, pc_content, executable):
        prefix_match = re.search(r"^prefix=(.+)$", pc_content, flags=re.M)
        if not prefix_match:
            return f"${{bindir}}/{executable}"
        prefix = prefix_match.group(1).strip()
        source = os.path.join(prefix, "bin", executable)
        if not os.path.isfile(source):
            return f"${{bindir}}/{executable}"

        is_python = False
        with open(source, encoding="utf-8", errors="ignore") as handle:
            if "python" in handle.readline():
                is_python = True

        if is_python:
            return self._build_python_wrapper(executable, prefix, source)
        target = os.path.join(self.generators_folder, executable)
        shutil.copyfile(source, target)
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return target

    def _build_python_wrapper(self, executable, glib_prefix, script_path):
        codegen_dir = os.path.join(glib_prefix, "share", "glib-2.0")
        wrapper = os.path.join(self.generators_folder, executable)
        python = (os.environ.get("HMBS_PYTHON3")
                  or shutil.which("python3") or sys.executable)
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/bin/sh\n"
                f"export PYTHONPATH={codegen_dir}:$PYTHONPATH\n"
                f'exec "{python}" "{script_path}" "$@"\n'
            )
        try:
            os.chmod(wrapper, 0o755)
        except OSError:
            pass
        return wrapper
