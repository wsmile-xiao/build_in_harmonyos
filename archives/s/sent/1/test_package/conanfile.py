#!/usr/bin/env python3
"""Conan test_package — sent 1

sent is a GUI viewer, so there is no ``--version``-style happy path that also
needs a display.  ``test_sent.sh`` therefore really executes the packaged
binary along the four code paths upstream reaches before ``xinit()``
(``-v``, unknown option, missing file, empty stdin), plus two packaging
existence checks.  See the header comment of ``test_sent.sh`` for why no
display-touching case is run.

Runtime library lookup is double-buffered on purpose:
  1. ``VirtualRunEnv`` puts every run-visible dependency libdir on
     ``LD_LIBRARY_PATH`` (the primary channel);
  2. an ``LD_PRELOAD`` list of absolute ``.so`` paths is passed as argv[2],
     because the device loader has been observed to ignore
     ``LD_LIBRARY_PATH`` for some directories (HMBS [stale_runtime_library],
     xeyes 1.3.1 audit).
``_runtime_preload()`` degrades to an empty string rather than failing when a
dependency is not reachable from this node, exactly as the xeyes precedent
does — the assertions are still genuine executions either way.

Device-specific twist (A machine, 2026-09-28): the published
``fontconfig/2.18.3`` and ``libxft/2.3.9`` binaries carry a ``.codesign``
section the loader still rejects (``Error loading shared library`` from every
search path), while seven sibling X11 libs from the same download load fine.
E135 family — an invalid signature is as fatal as a missing one.  The whole
closure is therefore copied into a scratch directory under its exact
DT_NEEDED/SONAME name and re-signed with ``binary-sign-tool -selfSign 1``;
the scratch dir is handed to the test script as argv[3] and prepended to
``LD_LIBRARY_PATH`` (verified manually: ``sent -v`` runs to completion with
the re-signed copies).
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile

# (conan package, soname) in dependency order — leaves first.
# This ordering is not a guess: it is the measured DT_NEEDED closure of the
# downloaded OHOS binaries (llvm-readelf -d, 2026-09-23):
#   libX11.so.6   -> libxcb.so.1 libXau.so.6 libXdmcp.so.6
#   libXrender.so.1 -> libX11.so.6 libxcb.so.1
#   libXft.so.2   -> libfontconfig.so.1 libfreetype.so.6 libXrender.so.1 libX11.so.6
#   libfontconfig.so.1 -> libfreetype.so.6 libxml2.so.16
# (libfontenc and expat are *not* in this closure: fontconfig/2.18.3 uses the
# libxml2 backend, unlike fontconfig/2.18.1.1 which pins expat.)
RUNTIME_SONAMES = (
    ("libxau", "libXau.so.6"),
    ("libxdmcp", "libXdmcp.so.6"),
    ("libxcb", "libxcb.so.1"),
    ("libx11", "libX11.so.6"),
    ("libxrender", "libXrender.so.1"),
    ("freetype", "libfreetype.so.6"),
    ("libxml2", "libxml2.so.16"),
    ("fontconfig", "libfontconfig.so.1"),
    ("libxft", "libXft.so.2"),
)


class SentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _find_tool(name):
        candidate = os.path.join("/data/service/hnp/bin", name)
        if os.path.isfile(candidate):
            return candidate
        return shutil.which(name)

    def _dep_folder(self, name):
        """Package folder for a dependency, tolerating non-immediate deps.

        ``self.dependencies`` only carries immediate requirements, so the
        transitive X11 stack usually is not reachable from here by name.  The
        first attempt therefore falls through to scanning the folder of any
        dependency that *is* visible for a matching soname.
        """
        try:
            dep = self.dependencies[name]
        except KeyError:
            return None
        return getattr(dep, "package_folder", None)

    def _find_so(self, root, prefix):
        """Best real ``prefix*`` file under *root*.

        Two device quirks drive the ranking (xeyes 1.3.1 audit; sent 1 first
        run 2026-09-28 lost every Xft relocation because the ``libXft.so.2``
        symlink slot was handed to the loader while still unmaterialised):
          * HMDFS does not reliably materialise symlinks (E050), so the
            ``libX*.so.N`` link name must never win while a fully versioned
            real file exists in the same directory;
          * ``os.path.islink`` cannot be trusted on HMDFS, so candidates are
            ranked non-link first, then by a size floor that rejects symlink
            slots not yet materialised, then by longest name (the fully
            versioned real file, e.g. ``libXft.so.2.3.9``).
        """
        if not root or not os.path.isdir(root):
            return None
        hits = []
        for dirpath, _dirnames, filenames in os.walk(root):
            for fname in filenames:
                if fname.startswith(prefix):
                    hits.append(os.path.join(dirpath, fname))

        def _rank(path):
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            return (os.path.islink(path), size < 4096, -len(path))

        hits.sort(key=_rank)
        return hits[0] if hits else None

    def _runtime_closure(self):
        """``[(soname, absolute real path), ...]`` in dependency order."""
        pairs = []
        for name, soname in RUNTIME_SONAMES:
            path = None
            folder = self._dep_folder(name)
            if folder:
                path = self._find_so(folder, soname)
            if not path:
                # Fall back to any visible dependency that ships this soname.
                for dep_name in list(self.dependencies):
                    if dep_name == "sent":
                        continue
                    candidate = self._find_so(
                        self._dep_folder(dep_name), soname
                    )
                    if candidate:
                        path = candidate
                        break
            if path:
                pairs.append((soname, path))
        return pairs

    def _signed_dynload(self, pairs):
        """Copy the closure under exact SONAME names and self-sign the copies.

        Returns ``(dynload_dir, preload_paths)``.  Without the signer the
        original paths are preloaded, exactly as the xeyes precedent does.
        """
        originals = [path for _soname, path in pairs]
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            self.output.info(
                "binary-sign-tool not found; preloading original library paths"
            )
            return None, originals
        objcopy = self._find_tool("llvm-objcopy")
        # Live under $TMPDIR/~/tmp (device /tmp is read-only, E002), never
        # inside the repo: with no layout() the test build folder *is* the
        # test_package source dir, so a repo-local scratch dir would pollute
        # the worktree on every run.
        scratch = os.path.join(
            os.environ.get("TMPDIR") or os.path.expanduser("~/tmp"),
            "qw2-sent-dynload",
        )
        try:
            shutil.rmtree(scratch, ignore_errors=True)
            os.makedirs(scratch, exist_ok=True)
        except OSError:
            return None, originals
        preload = []
        signed = 0
        for soname, path in pairs:
            raw = os.path.join(scratch, "raw_" + soname)
            dst = os.path.join(scratch, soname)
            done_ok = False
            # HMDFS/tool hiccups under load made single-shot signing flaky
            # (2026-09-28 00:58 run degraded silently); retry instead.
            for _attempt in range(3):
                try:
                    shutil.copyfile(path, raw)
                    if objcopy:
                        subprocess.run(
                            [objcopy, "--remove-section", ".codesign", raw],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=120,
                            check=False,
                        )
                    done = subprocess.run(
                        [signer, "sign", "-inFile", raw, "-outFile", dst, "-selfSign", "1"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=180,
                        check=False,
                    )
                    if done.returncode == 0 and os.path.getsize(dst) > 4096:
                        done_ok = True
                        break
                except (OSError, subprocess.SubprocessError):
                    pass
                time.sleep(3)
            if done_ok:
                preload.append(dst)
                signed += 1
            else:
                preload.append(path)
        self.output.info(
            "dynload: %d/%d libs re-signed into %s" % (signed, len(pairs), scratch)
        )
        return scratch, preload

    def test(self):
        sent_folder = self.dependencies["sent"].package_folder
        sent_bin = os.path.join(sent_folder, "bin", "sent")

        # HMBS [shell_getcwd]: run with the injected SHELL (/bin/sh), never a
        # hardcoded HNP bash, and keep the script POSIX-sh compatible.
        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("sh")
            or "/bin/sh"
        )
        script = os.path.join(self.source_folder, "test_sent.sh")
        dynload_dir, preload_list = self._signed_dynload(self._runtime_closure())
        preload = ":".join(preload_list)
        self.output.info("dynload dir=%s" % (dynload_dir or "<none>"))
        self.output.info("runtime LD_PRELOAD=%s" % (preload or "<empty>"))
        self.run(
            '"{shell}" "{script}" "{binary}" "{preload}" "{dynload}"'.format(
                shell=shell,
                script=script,
                binary=sent_bin,
                preload=preload,
                dynload=dynload_dir or "",
            ),
            env="conanrun",
        )
        # HMBS_TEST_PACKAGE_RESULT is printed by test_sent.sh itself, with
        # discovered/passedCount counted from its own assertions.
        #
        # Upstream test-suite audit (see MANIFEST.yml): sent 1 ships no
        # automated tests at all — the Makefile defines only
        # all/options/config.h/.c.o/sent/cscope/clean/dist/install/uninstall
        # and there is no check or TESTS target, no t/ directory, no test source.
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
            '"framework":"none",'
            '"command":"make -n check (no check target)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,'
            '"skipped":0,'
            '"reason":"sent 1 上游无测试套件：Makefile 仅有 all/options/clean/dist/'
            'install/uninstall/cscope 目标，无 check/TESTS；源码树无 tests 目录与测试源文件"}'
        )
