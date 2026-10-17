#!/usr/bin/env python3
"""Conan test_package for tabbed 0.9 (two installed programs).

tabbed needs an X display to do anything useful, but every argument path is
reached before ``XOpenDisplay()`` (tabbed.c:1372), so the installed programs can
be exercised for real here: the version banner, the usage path, the
"cannot open display" path (which also proves the X11/Xft/fontconfig runtime
closure loads) and the ``xembed`` helper (which upstream links into the same
X closure through the single ``.o`` rule in its Makefile).

All assertions are made on stderr text: upstream routes *every* early exit of
tabbed through ``die()`` -> ``exit(EXIT_FAILURE)``, so exit codes carry no
information (``-v`` exits 1 just like a real error).

OHOS runtime closure (E452)
---------------------------
The packaged programs carry no RPATH and the musl loader rejects a shared
object whose ``.codesign`` data it does not accept -- rejecting it at *load*
time, so the process exits 127 and every assertion reports
``Error loading shared library``.  Reproduced on 2026-09-24 with
fontconfig/2.18.3: its .so is byte-identical to the registry copy (MD5 matches
``conanmanifest.txt``), every path/permission/symlink check passes and
``LD_LIBRARY_PATH`` is already populated by ``conanrun``, yet the loader still
refuses it; re-signing a private copy makes the very same probe return its
expected code.  So a valid environment is not enough -- the closure has to be
re-signed for *this* execution boundary.

Per E452 the provider cache stays read-only: the closure is copied into a
task-private directory, each copy is re-signed there, that directory is
prepended to ``LD_LIBRARY_PATH``, and the directory is removed afterwards.
If the signing tools are unavailable the test falls back to the plain
``conanrun`` closure instead of failing the build.
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run

CHECKS = 4


class TabbedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise Exception("tabbed test_package must run on the host")

        package = self.dependencies["tabbed"]
        bin_dir = os.path.join(package.package_folder, "bin")
        for name in ("tabbed", "xembed"):
            exe = os.path.join(bin_dir, name)
            if not os.path.isfile(exe):
                raise Exception("program not packaged: " + exe)

        script = os.path.join(self.recipe_folder, "test_tabbed.sh")
        if not os.path.isfile(script):
            raise Exception("test script not found: " + script)

        # E452: task-private re-signed runtime root (None => plain conanrun).
        runtime_lib = None
        try:
            runtime_lib = self._materialize_signed_runtime()

            # VirtualRunEnv already exports the dependency closure through
            # conanrun; the private root is prepended so the loader sees the
            # re-signed copies first.  $LD_LIBRARY_PATH stays unquoted so the
            # shell expands it *after* conanrun has populated it.
            ld_prefix = ""
            if runtime_lib:
                ld_prefix = "LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH ".format(
                    shlex.quote(runtime_lib))

            # self.run() raises when the script exits non-zero.
            self.run("{}TABBED_BIN={} XEMBED_BIN={} sh {}".format(
                ld_prefix,
                shlex.quote(os.path.join(bin_dir, "tabbed")),
                shlex.quote(os.path.join(bin_dir, "xembed")),
                shlex.quote(script)), env="conanrun")
        finally:
            if runtime_lib and os.path.isdir(runtime_lib):
                shutil.rmtree(runtime_lib, ignore_errors=True)

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_tabbed.sh (tabbed -v / -Z / bare / xembed)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))

    # ── E452: private runtime root ──────────────────────────────────────

    def _materialize_signed_runtime(self):
        """Copy the dependency closure beside a private dir and re-sign it.

        Returns the directory to prepend to LD_LIBRARY_PATH, or None when the
        platform or the signing tools do not allow it (caller then relies on
        the plain conanrun closure).
        """
        if str(self.settings.os) != "OHOS":
            return None
        objcopy = self._find_tool("llvm-objcopy")
        signer = self._find_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "E452: signing tools not found, falling back to the plain "
                "conanrun runtime closure")
            return None

        # The workspace contract sends every disposable artefact to ~/tmp;
        # TMPDIR points at the home root on this device, and the home root must
        # not receive new loose files.
        base = os.path.join(os.path.expanduser("~"), "tmp")
        root = os.path.join(base, "tabbed-test-runtime-{}".format(os.getpid()))
        shutil.rmtree(root, ignore_errors=True)
        try:
            os.makedirs(root)
        except OSError as error:
            self.output.warning(
                "E452: cannot create private runtime dir ({})".format(error))
            return None

        copied = self._copy_closure_into(root)
        if not copied:
            shutil.rmtree(root, ignore_errors=True)
            return None
        if not self._resign_tree(root):
            # Nothing re-signed: the plain closure is no worse off.
            shutil.rmtree(root, ignore_errors=True)
            return None
        return root

    def _dependency_lib_dirs(self):
        """Every lib dir of the whole dependency closure (read-only access)."""
        dirs = []
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder, libdir)
                if os.path.isdir(path) and path not in dirs:
                    dirs.append(path)
        return dirs

    def _copy_closure_into(self, root):
        """Materialise the closure next to each other; provider cache is only
        ever read from here (E452 forbid: never rewrite the Conan cache)."""
        copied = 0
        for src_dir in self._dependency_lib_dirs():
            for name in sorted(os.listdir(src_dir)):
                if ".so" not in name:
                    continue
                src = os.path.join(src_dir, name)
                dst = os.path.join(root, name)
                if os.path.lexists(dst):
                    continue
                try:
                    if os.path.islink(src):
                        os.symlink(os.readlink(src), dst)
                    else:
                        shutil.copy2(src, dst)
                    copied += 1
                except OSError:
                    # HMDFS may refuse symlinks; a dereferenced copy of the
                    # real file keeps the SONAME chain resolvable.
                    try:
                        real = os.path.realpath(src)
                        if os.path.isfile(real):
                            shutil.copy2(real, dst)
                            copied += 1
                    except OSError:
                        continue
        return copied

    def _resign_tree(self, root):
        """Strip one stale .codesign and re-sign every private ELF copy."""
        objcopy = self._find_tool("llvm-objcopy")
        signer = self._find_tool("binary-sign-tool")
        signed = 0
        for name in sorted(os.listdir(root)):
            dst = os.path.join(root, name)
            if os.path.islink(dst) or not os.path.isfile(dst):
                continue
            if not self._is_elf(dst):
                continue
            unsigned = dst + ".unsigned"
            signed_tmp = dst + ".signed"
            try:
                self.run("{} --remove-section .codesign {} {}".format(
                    shlex.quote(objcopy), shlex.quote(dst),
                    shlex.quote(unsigned)),
                    quiet=True, ignore_errors=True, env=None)
                self.run("{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer), shlex.quote(unsigned),
                    shlex.quote(signed_tmp)),
                    quiet=True, ignore_errors=True, env=None)
                if os.path.isfile(signed_tmp):
                    shutil.copyfile(signed_tmp, dst)
                    os.chmod(dst, 0o755)
                    signed += 1
            except Exception:  # noqa: BLE001 - fall back to the plain closure
                continue
            finally:
                for tmp in (unsigned, signed_tmp):
                    try:
                        if os.path.isfile(tmp):
                            os.remove(tmp)
                    except OSError:
                        pass
        if signed:
            self.output.info(
                "E452: re-signed {} private runtime copies".format(signed))
        return signed > 0

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _find_tool(name):
        """R33-style lookup: never depend on a bare shell PATH.

        Same candidate chain as the recipe's ``_find_tool`` (env override,
        then PATH, then the HNP bin dir, then the user-local bin dir) so the
        two sides cannot disagree about whether a tool "exists".
        """
        configured = os.environ.get(
            "OHOS_" + name.upper().replace("-", "_"))
        for candidate in (configured,
                          shutil.which(name),
                          os.path.join("/data/service/hnp/bin", name),
                          os.path.join(os.path.expanduser("~"),
                                       "usr", "local", "bin", name)):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None
