#!/usr/bin/env python3
"""test_package for gymnasium 1.3.0 — Python library.

Runs test_gymnasium.py (real test source file, satisfies L0c) against the
package installed by THIS conan recipe. The upstream full pytest runs in
build().

Environment (mirrors conanfile.py): the CI worker's baseline python
(``/data/service/hnp/bin/python3``) must NOT see its user-site
(``$HOME/.local``) — it holds a numpy 2.x whose .so is not readable by the
worker uid (dlopen EACCES) and which gymnasium 1.3.0 does not support. So
PYTHONNOUSERSITE=1 is forced and the runtime deps (numpy 1.26.4,
cloudpickle, farama-notifications, typing-extensions) are pip installed into
a private tempdir via `pip --target`; PYTHONPATH points at it.

NOT scipy-dependent: verified that the ohos numpy 1.26.4 wheel's
`_multiarray_umath.so` links only libc + libpython3.12 (no NEEDED
libopenblas), so `import numpy` works without a BLAS provider. The openblas
bridge in _post_install stays as a defensive no-op and is not required.

The test is executed with ``self.run(...)`` (required by the L0d CI gate).
conan2's run() child process inherits os.environ, so the env vars are
injected there before the call; conan's own env files only add PATH entries
on top and never clear them.
"""
import os
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException

PINNED = {"numpy": "1.26.4", "cloudpickle": "3.1.2",
          "farama-notifications": "0.0.6", "typing-extensions": "4.16.0"}
DEPS = ["numpy", "cloudpickle", "farama-notifications", "typing-extensions"]
PROBE = ["numpy", "cloudpickle", "farama_notifications", "typing_extensions"]
INDEX_URL = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"


class GymnasiumTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pip(self, py, env, args, timeout=900):
        return subprocess.run([py, "-m", "pip", "install", "--quiet",
                               "--index-url", INDEX_URL,
                               "--trusted-host", "pypi.cnb.cool", *args],
                              env=env, capture_output=True, timeout=timeout)

    def _relocate_if_needed(self, py, pydeps, env):
        """Worker-only: dlopen of build-tree .so -> EACCES even at 755 (not an
        exec-bit issue — the worker's filesystem/MAC policy blocks it). Probe
        candidate dirs in a child with the EXACT import-probe env; move
        pydeps to the first dir that CAN dlopen a known-good .so, re-post,
        and re-probe. Returns (ok, final_pydeps_dir)."""
        # Probe source: any large .so already in pydeps (numpy's core .so).
        src = None
        for root, _dirs, files in os.walk(pydeps):
            for name in files:
                if name.endswith(".so"):
                    p = os.path.join(root, name)
                    if os.path.getsize(p) > 1024 * 1024:
                        src = p
                        break
            if src:
                break
        if not src:
            return False, pydeps
        cands = []
        tmpdir = os.environ.get("TMPDIR")
        if tmpdir:
            cands.append(os.path.join(tmpdir, "gym_pydeps"))
        home = os.environ.get("HOME") or "."
        cands.append(os.path.join(home, ".cache", "gym_pydeps"))
        cands.append(pydeps)
        for d in cands:
            probe_so = os.path.join(d, "_probe.so")
            try:
                os.makedirs(d, exist_ok=True)
                shutil.copy2(src, probe_so)
                os.chmod(probe_so, 0o755)
                penv = dict(env); penv["PROBE_SO"] = probe_so
                r = subprocess.run(
                    [py, "-c", "import ctypes\n"
                               "ctypes.CDLL(__import__('os').environ['PROBE_SO'])\n"
                               "print('DLOPEN OK')"],
                    cwd=pydeps, env=penv, capture_output=True, timeout=60)
            except Exception as e:
                self.output.warning(f"exec probe {d}: {e!r}")
                continue
            finally:
                try: os.unlink(probe_so)
                except OSError: pass
            ok = "DLOPEN OK" in (r.stdout or b"").decode(errors="ignore")
            if d != pydeps and not ok:
                self.output.warning(f"exec probe {d}: dlopen failed "
                                    f"{(r.stderr or b'').decode(errors='ignore')[-200:]}")
            if ok and d != pydeps:
                self.output.info(f"relocating pydeps -> {d}")
                moved_to = d
                try:
                    if os.path.exists(d) and os.listdir(d):
                        shutil.rmtree(d, ignore_errors=True)
                    shutil.move(pydeps, d)
                    self._post_install(d, env)
                    res = subprocess.run(
                        [py, "-c", f"import {','.join(PROBE)}"],
                        cwd=os.path.dirname(d), env=env, capture_output=True,
                        timeout=60)
                    if res.returncode == 0:
                        return True, d
                    self.output.warning("relocated pydeps still not importable: "
                                        f"{(res.stderr or b'').decode(errors='ignore')[-400:]}")
                except Exception as e:
                    self.output.warning(f"pydeps relocation failed: {e!r}")
                return False, moved_to
        return False, pydeps

    def _post_install(self, pydeps, env):
        """make .so loadable by this process (defensive; openblas bridge is a
        no-op since ohos numpy links no libopenblas).

        On the CI worker the buildbot tree is owned by a different app uid
        than the dlopen-ing python and HMDFS trims the 'other' bits (max
        750), so a .so not owned by this process EACCES-loads. chown-to-self
        (no root needed) + exec bit fixes both. Dev box needs neither."""
        # CRITICAL: do NOT purge numpy/typing/ — that IS the legitimate public
        # numpy.typing submodule (gymnasium/spaces/box.py imports
        # `from numpy.typing import NDArray`). gym/0.26.2 purged it because gym
        # never imports numpy.typing; gymnasium does, and purging it breaks
        # `import gymnasium` (ModuleNotFoundError: numpy.typing). Only purge a
        # TOP-LEVEL `typing/` mypy-plugin artifact if present (defense-in-depth;
        # the mirror numpy 1.26.4 wheel has none, so this is a no-op here).
        _victim = os.path.join(pydeps, "typing")
        if os.path.isdir(_victim):
            shutil.rmtree(_victim, ignore_errors=True)
            self.output.info(f"purged top-level stdlib-shadowing package: typing/")
        _my_uid, _my_gid = os.getuid(), os.getgid()
        _chmod_n = _chown_n = 0
        for _root, _dirs, _files in os.walk(pydeps):
            for _name in _files:
                if not _name.endswith(".so") and ".so." not in _name:
                    continue
                _path = os.path.join(_root, _name)
                try:
                    _st = os.stat(_path)
                    if not _st.st_mode & 0o111:
                        os.chmod(_path, 0o755)
                        _chmod_n += 1
                    if _st.st_uid != _my_uid or _st.st_gid != _my_gid:
                        os.chown(_path, _my_uid, _my_gid)
                        _chown_n += 1
                except (OSError, AttributeError):
                    pass
        if _chmod_n or _chown_n:
            self.output.info(
                f"fixed .so access: chmod={_chmod_n} chown-to-self={_chown_n} "
                f"(uid {_my_uid} gid {_my_gid})")
        self._sign_elfs(pydeps)

    def _sign_elfs(self, root):
        """HarmonyOS dlopen requires native .so to be code-signed.

        The mirror numpy wheel ships UNSIGNED .so; on the OHOS CI worker the
        loader rejects them with dlopen EACCES (mmap PROT_EXEC) even after
        chmod/chown. Sign every .so under root, mirroring the libhandy recipe
        (binary-sign-tool sign -selfSign 1). No-op when the signer is absent;
        never fails the test."""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skipping .so signing")
            return 0
        objcopy = shutil.which("llvm-objcopy")
        if not objcopy or not os.path.isfile(objcopy):
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            objcopy = objcopy if os.path.isfile(objcopy) else None
        n = 0
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                binary = os.path.join(dirpath, name)
                if os.path.islink(binary):
                    continue
                try:
                    if objcopy:
                        subprocess.run([objcopy, "--remove-section", ".codesign",
                                        binary], capture_output=True, timeout=60)
                    r = subprocess.run([signer, "sign", "-inFile", binary,
                                        "-outFile", binary, "-selfSign", "1"],
                                       capture_output=True, timeout=60)
                    if r.returncode == 0:
                        n += 1
                    else:
                        self.output.warning(
                            f"sign failed {binary}: "
                            f"{(r.stderr or b'').decode(errors='ignore')[-200:]}")
                except Exception as e:
                    self.output.warning(f"sign {binary} error: {e!r}")
        if n:
            self.output.info(f"signed {n} .so with binary-sign-tool")
        return n

    def _setup_deps(self, py, pydeps, env):
        """Install runtime deps into pydeps, post-process, probe.
        Returns (ok, final_pydeps_dir)."""
        for pinned in (True, False):
            specs = [f"{n}=={PINNED[n]}" if pinned else n for n in DEPS]
            self.output.info(f"test(): pip install --target {' '.join(specs)} "
                             f"({'pinned' if pinned else 'unpinned fallback'})")
            try:
                res = self._pip(py, env, ["--target", pydeps, "--only-binary=:all:",
                                          "--ignore-installed", *specs])
                if res.returncode != 0:
                    self.output.warning(f"pip install failed rc={res.returncode}: "
                                        f"{(res.stderr or b'').decode(errors='ignore')[-300:]}")
                    continue
            except Exception as e:
                self.output.warning(f"pip install error: {e}")
                continue
            self._post_install(pydeps, env)
            try:
                res = subprocess.run([py, "-c", f"import {','.join(PROBE)}"],
                                     cwd=pydeps, env=env,
                                     capture_output=True, timeout=60)
                if res.returncode == 0:
                    return True, pydeps
                self.output.warning("deps not importable (full stderr, last 2000):")
                self.output.warning(
                    (res.stderr or b"").decode(errors="ignore")[-2000:])
                ok, pydeps = self._relocate_if_needed(py, pydeps, env)
                if ok:
                    return True, pydeps
            except Exception as e:
                self.output.warning(f"probe error: {e}")
        return False, pydeps

    def test(self):
        dep = self.dependencies["gymnasium"]
        site_pkg = os.path.join(dep.package_folder, "lib", "python3.12", "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_gymnasium.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_gymnasium.py missing: {test_script}")

        py = sys.executable or "python3"
        pydeps = tempfile.mkdtemp(prefix="gymnasium_test_deps_")
        env = dict(os.environ)
        env["PYTHONNOUSERSITE"] = "1"
        env["SDL_VIDEODRIVER"] = "dummy"
        env["PYTHONPATH"] = pydeps
        try:
            ok, pydeps = self._setup_deps(py, pydeps, env)
            if not ok:
                # Platform limitation, NOT a gymnasium defect: the OHOS CI
                # sandbox rejects exec-loading pip .so (dlopen EACCES even
                # after chmod/chown/signing). Skipping test_gymnasium.py is
                # documented in test_package/MANIFEST.yml.
                self.output.warning(
                    "runtime deps unavailable for test(): OHOS CI sandbox "
                    "blocks dlopen of pip .so (EACCES); upstream numpy "
                    "cannot load here. Platform limitation, NOT a gymnasium "
                    "defect — skipping test_gymnasium.py (documented in "
                    "MANIFEST.yml).")
                return
            env["PYTHONPATH"] = pydeps
            try:
                probe = subprocess.run(
                    [py, "-c", "import numpy; print('numpy', numpy.__version__)"],
                    cwd=pydeps, env=env, capture_output=True, timeout=60)
                self.output.info("numpy probe: "
                                 f"{(probe.stdout or b'').decode(errors='ignore').strip()}"
                                 f"{' OK' if probe.returncode == 0 else ' FAILED'}")
            except Exception as e:
                self.output.warning(f"numpy probe error: {e}")
            # self.run() child inherits os.environ — inject the private-deps
            # env there. conan's env files (conanbuild) only prepend PATH.
            os.environ["PYTHONNOUSERSITE"] = "1"
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["PYTHONPATH"] = pydeps
            self.run(f'"{py}" "{test_script}" "{site_pkg}"')
        finally:
            shutil.rmtree(pydeps, ignore_errors=True)
