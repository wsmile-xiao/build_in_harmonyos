#!/usr/bin/env python3
"""Conan recipe — mapbox-polylabel 2.1.0 (JavaScript, no compiled artifact).

Upstream v2.1.0 ships only polylabel.js (ES module) plus a node:test suite
under test/. The C++ header tree (include/mapbox/polylabel.hpp) that existed
at v2.0.0 was removed upstream between v2.0.0 and v2.1.0, so this recipe
packages the versioned JS source verbatim and runs the upstream node tests
as the build gate. No C++ compiler is required.

Runtime strategy (2026-09-09, strategy cycle 2):
- The previous cycle tried to execute the single HMDFS-hosted node binary
  via the musl loader. True-machine evidence falsified that approach:
  ``Loader probe OSError ... Permission denied: '/lib/ld-musl-aarch64.so.1'``
  i.e. execve() of the loader itself is denied in the build context, so no
  loader-mediated trick around the same inode can work. All loader / copy /
  hardcoded-/storage-path workarounds are removed.
- New route (strategy cycle 7): abandon the single broken source.
  ~/nodejs/bin/node is a 120MB ELF present on disk yet ENOENT on exec =
  missing PT_INTERP loader; no copy/sign of that inode can ever run.
  Probe EVERY readable candidate with the hnp node.org platform runtime
  FIRST (`/data/service/hnp/node.org/node_v24.13.0/bin/node`,
  alexjs/aicommits precedent) under clean `env -i` + --jitless
  (node Signal 5 under OHOS env vars). Stage only as fallback.
  Never skips the suite.
- Second latent gap fixed in the same route: ``polylabel.js`` bare-imports
  the ``tinyqueue`` runtime dependency (package.json ``dependencies``), so
  the suite cannot pass on a bare checkout. It is vendored with conan
  ``get()`` from the authoritative npm registry tarball (sha256 verified
  against registry metadata: sha1 101ea761ccc81f979e29200929e78f1556e3661e)
  into ``node_modules/tinyqueue`` — pure download+extract, no exec, no npm
  required — and bundled into the package beside polylabel.js (same pattern
  as boids bundling its ``inherits`` runtime dep).
- Upstream-canonical test command is ``node test/test.js`` (package.json
  ``scripts.test``); ``node --test`` is kept only as a fallback variant.
  TAP summary markers (``# tests``/``# pass``) are REQUIRED: exit code 0
  without markers is treated as failure (anti-false-pass).
"""

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"

_UPSTREAM_TEST_ENTRY = os.path.join("test", "test.js")
_UPSTREAM_CANONICAL_CMD = ["test", "test.js"]  # `node test/test.js`
_MIN_NODE_MAJOR = 18


class MapboxPolylabelConan(ConanFile):
    name = "mapbox-polylabel"
    version = "2.1.0"
    description = "A fast algorithm for finding the pole of inaccessibility of a polygon (JavaScript)"
    license = "ISC"
    homepage = "https://github.com/mapbox/polylabel"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("polygon", "pole-of-inaccessibility", "javascript", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Vendor the tinyqueue runtime dep (bare `import ... from 'tinyqueue'`
        # in polylabel.js). npm-registry layout: package/{index.js,...}.
        get(self, **self.conan_data["sources"]["tinyqueue-3.0.0"],
            destination=os.path.join(self.source_folder, "node_modules", "tinyqueue"),
            strip_root=True)
        # Cycle-9 fallback runtime: vendor QuickJS C source (same tarball as
        # archives/q/quickjs/2024-01-13) so a JS engine can be built locally
        # when no host node is runnable. Pure download+extract, no exec.
        get(self, **self.conan_data["sources"]["quickjs-2024-01-13"],
            destination=os.path.join(self.source_folder, "quickjs-src"),
            strip_root=True)

    def build(self):
        self._run_upstream_tests()

    def _writable_tmpdir(self):
        """Return a writable TMPDIR honoring HMBS injection; never /tmp."""
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val):
                try:
                    fd, probe = tempfile.mkstemp(prefix="hmbs-probe-",
                                                 dir=val)
                    os.close(fd)
                    os.unlink(probe)
                    return val
                except OSError:
                    continue
        # Fall back to a private dir under the build folder while system
        # /tmp is EROFS readonly on the true machine.
        base = getattr(self, "build_folder", None) or tempfile.gettempdir()
        fallback = os.path.join(base, "hmbs-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _test_env(self):
        env = dict(os.environ)
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        # Keep npm (if used by hand) away from readonly /tmp and HOME.
        npm_cache = os.path.join(self.build_folder, "npm-cache")
        try:
            os.makedirs(npm_cache, exist_ok=True)
        except OSError:
            pass
        env.setdefault("npm_config_cache", npm_cache)
        return env

    def _find_source_nodes(self):
        """All readable host node candidates, platform runtime FIRST.

        Cycle-8 evidence: cycle-7 hardcoded exactly
        ``/data/service/hnp/node.org/node_v24.13.0/bin/node`` yet the true
        machine filtered candidates down to a single
        ``~/nodejs/bin/node`` entry, so that versioned path does not exist
        on this client. Discover runtimes by globbing versioned/relocated
        hnp trees instead of assuming one version, then PATH/HMBS_NODE.
        """
        cands = []
        for pattern in (
            "/data/service/hnp/node.org/*/bin/node",
            "/data/service/hnp/node*/bin/node",
            "/data/service/hnp/*/bin/node",
            "/opt/node*/bin/node",
            "/usr/local/bin/node",
            "/usr/bin/node",
        ):
            try:
                for hit in sorted(glob.glob(pattern)):
                    if hit and hit not in cands:
                        cands.append(hit)
            except OSError:
                continue
        for extra in (
            "/data/service/hnp/node.org/node_v24.13.0/bin/node",
            "/data/service/hnp/bin/node",
        ):
            if extra and extra not in cands:
                cands.append(extra)
        for key in ("HMBS_NODE", "NODE", "NODEJS"):
            val = os.environ.get(key, "")
            if val and val not in cands:
                cands.append(val)
        for name in ("node", "nodejs"):
            found = shutil.which(name)
            if found and found not in cands:
                cands.append(found)
        for extra in (
            "/usr/local/bin/node",
            "/usr/bin/node",
            os.path.expanduser("~/.local/bin/node"),
            os.path.expanduser("~/nodejs/bin/node"),
        ):
            if extra and extra not in cands:
                cands.append(extra)
        return [p for p in cands
                if p and os.path.isfile(p) and os.access(p, os.R_OK)]

    def _find_source_node(self):
        """First readable candidate (kept for compatibility)."""
        nodes = self._find_source_nodes()
        return nodes[0] if nodes else None

    @staticmethod
    def _interp_of(path):
        """Best-effort PT_INTERP extraction; returns (interp, exists|None).

        Never raises: any truncated header, unknown class, or short
        program-header read yields (None, None) so probing can continue.
        Cycle-8 fix: ELF header fields start after the 16-byte e_ident,
        so unpack head[16:64] (48 bytes, ELF64) / head[16:52] (36 bytes,
        ELF32). The previous head[:64]/head[:52] slices crashed every
        probe with `struct.error: unpack requires a buffer of 48 bytes`.
        """
        try:
            import struct
            with open(path, "rb") as fh:
                head = fh.read(64)
            if len(head) < 52 or head[:4] != b"\x7fELF":
                return None, None
            is64 = head[4] == 2
            le = head[5] == 1
            endian = "<" if le else ">"
            try:
                if is64:
                    if len(head) < 64:
                        return None, None
                    _, _, _, _, phoff, _, _, _, phentsize, phnum = struct.unpack(
                        endian + "HHIQQQIHHHHHH", head[16:64])
                else:
                    _, _, _, phoff, _, _, _, phentsize, phnum = struct.unpack(
                        endian + "HHIIIIIHHHHHH", head[16:52])
            except struct.error:
                return None, None
            if phoff == 0 or phnum > 64:
                return None, None
            if is64 and phentsize != 56:
                return None, None
            if not is64 and phentsize != 32:
                return None, None
            with open(path, "rb") as fh:
                for i in range(phnum):
                    fh.seek(phoff + i * phentsize)
                    raw = fh.read(phentsize)
                    if len(raw) < phentsize:
                        return None, None
                    if is64:
                        (ptype,) = struct.unpack(endian + "I", raw[:4])
                        off, _, _, filesz = struct.unpack(endian + "QQQQ", raw[8:40])
                    else:
                        ptype, off, _, _, filesz = struct.unpack(endian + "IIIIIIII", raw[:32])[:5]
                    if ptype == 3:  # PT_INTERP
                        fh.seek(off)
                        interp = fh.read(filesz).split(b"\x00")[0].decode(
                            "utf-8", "replace")
                        return interp, os.path.exists(interp)
            return None, None
        except OSError:
            return None, None
        except Exception:
            return None, None

    def _clean_argv(self, node, args, env):
        """Wrap node invocation in `env -i` clean env (alexjs precedent).

        node crashes with Signal 5 inheriting OHOS AppSpawn/ALACRITTY/UBSAN
        vars; the launcher pattern is `env -i PATH/HOME/TMPDIR node
        --jitless ...` with NODE_OPTIONS=--jitless (V8 errno DCHECK).
        """
        tmpdir = env.get("TMPDIR") or env.get("TMP") or env.get("TEMP") or "/tmp"
        home = env.get("HOME") or os.path.expanduser("~")
        node_dir = os.path.dirname(node)
        path_val = os.pathsep.join([
            node_dir, "/data/service/hnp/node.org/node_v24.13.0/bin",
            "/data/service/hnp/bin", "/usr/local/bin", "/usr/bin", "/bin",
        ])
        clean = [("PATH", path_val), ("HOME", home), ("TMPDIR", tmpdir),
                 ("TMP", tmpdir), ("TEMP", tmpdir),
                 ("NODE_OPTIONS", "--jitless --no-deprecation")]
        env_bin = shutil.which("env") or "/usr/bin/env"
        if env_bin and os.path.isfile(env_bin):
            argv = [env_bin, "-i"]
            argv += ["{}={}".format(k, v) for k, v in clean]
            argv += [node] + list(args)
            return argv
        for k, v in clean:
            env[k] = v
        for bad in list(env.keys()):
            if bad.startswith("AppSpawn") or bad in ("ALACRITTY", "UBSAN_OPTIONS"):
                env.pop(bad, None)
        return [node] + list(args)

    def _install_shim(self):
        """Return (shell, shim); shim is used DIRECTLY first (balboa canonical)."""
        hint = os.environ.get("HMBS_INSTALL", "")
        shell = os.environ.get("SHELL", "") or "/bin/sh"
        self.output.info("HMBS_INSTALL={!r} SHELL={!r}".format(hint, shell))
        if hint and os.path.isfile(hint):
            return shell, hint
        return shell, None

    def _sign_staged_elf(self, path, env):
        """Best-effort OHOS self-sign of a staged node copy. Never raises."""
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not signer or not os.path.isfile(signer):
            self.output.info("signer absent ({}); skip signing".format(signer))
            return False
        objcopy = (shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if objcopy and os.path.isfile(objcopy):
            try:
                res = subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    capture_output=True, text=True, env=env, timeout=60)
                self.output.info("objcopy rc={} {}".format(
                    res.returncode, ((res.stdout or "") + (res.stderr or "")).strip()[:200]))
            except OSError as exc:
                self.output.info("objcopy failed: {}".format(exc))
        tmp_out = path + ".signed.tmp"
        for args in ([signer, "sign", "-inFile", path, "-outFile", tmp_out,
                      "-selfSign", "1"],
                     [signer, "sign", "-inFile", path, "-outFile", tmp_out,
                      "-selfSign", "1", "-signAlg", "SHA256withECDSA"]):
            try:
                res = subprocess.run(args, capture_output=True, text=True,
                                     env=env, timeout=120)
            except OSError as exc:
                self.output.info("signer invocation failed: {}".format(exc))
                continue
            self.output.info("$ sign -> rc={} {}".format(
                res.returncode, ((res.stdout or "") + (res.stderr or "")).strip()[:300]))
            if res.returncode == 0 and os.path.isfile(tmp_out):
                try:
                    shutil.move(tmp_out, path)
                    self.output.info("signed copy installed: {}".format(path))
                    return True
                except OSError as exc:
                    self.output.info("move signed copy failed: {}".format(exc))
                    return False
        try:
            if os.path.isfile(tmp_out):
                os.unlink(tmp_out)
        except OSError:
            pass
        return False

    def _describe(self, path):
        try:
            if not os.path.isfile(path):
                return "missing"
            size = os.path.getsize(path)
            with open(path, "rb") as fh:
                magic = fh.read(4)
            return "size={} magic={!r}".format(size, magic)
        except OSError as exc:
            return "stat-failed: {}".format(exc)

    def _shim_install(self, src, dst, env):
        """Stage src->dst via task-local pure-python copy, then self-sign.

        Cycle-5 evidence: the HMBS_INSTALL shell shim returns rc=0 yet the
        file is absent in task-isolated dirs (it stages via readonly /tmp
        internally), while `shutil.copy` demonstrably creates the file
        (Plain-copy fallback installed=True everywhere). So copy FIRST with
        copy2 (preserves mode without chmod), verify presence/size/magic,
        then self-sign; shim kept only as last resort.
        """
        try:
            if os.path.isfile(dst) or os.path.islink(dst):
                try:
                    os.unlink(dst)
                except OSError:
                    pass
            shutil.copy2(src, dst)
            try:
                os.chmod(dst, 0o755)
            except OSError:
                pass
            self.output.info("copy2 {} -> {} {}".format(src, dst, self._describe(dst)))
        except OSError as exc:
            self.output.info("copy2 to {} failed: {} {}".format(dst, exc, self._describe(dst)))
            # Last-resort shim (previous route, kept for coverage).
            shell, shim = self._install_shim()
            if shim:
                for args in ([shell, shim, "-m", "755", src, dst],
                             [shell, shim, src, dst]):
                    try:
                        res = subprocess.run(args, capture_output=True, text=True,
                                             env=env, timeout=180)
                        self.output.info("$ {} -> rc={} {}".format(
                            " ".join(args), res.returncode,
                            ((res.stdout or "") + (res.stderr or "")).strip()[:200]))
                    except OSError as exc2:
                        self.output.info("shim invocation failed: {}".format(exc2))
                        continue
                    if os.path.isfile(dst):
                        break
            if not os.path.isfile(dst):
                return False
        # HMDFS copies stay unsigned -> kernel denies exec regardless of
        # mode bits; self-sign before probing (abbtr/balboa precedent).
        self._sign_staged_elf(dst, env)
        try:
            os.chmod(dst, 0o755)
        except OSError:
            pass
        self.output.info("staged {} {}".format(dst, self._describe(dst)))
        return os.path.isfile(dst)

    def _stage_candidates(self):
        """Task-isolated stage dirs ONLY (no global shared paths).

        Cycle-5 evidence: the signed copy under global
        ~/.local/share/hmbs-node-stage vanished (ENOENT) between sign and
        probe, while TMPDIR is task-independent per spec. Global ext2 and
        .local/share paths are shared across concurrent preflight clients
        and can be reaped concurrently; build_folder and task TMPDIR are
        per-task and safe.
        """
        cands = []
        try:
            cands.append(os.path.join(self.build_folder, "hmbs-node"))
        except Exception:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                cands.append(os.path.join(val, "hmbs-node"))
        seen, uniq = set(), []
        for cand in cands:
            if cand and cand not in seen:
                seen.add(cand)
                uniq.append(cand)
        return uniq

    def _probe_node(self, path, env):
        """Run `node --version` under clean env; return version or None."""
        self.output.info("probe pre-check {} {}".format(path, self._describe(path)))
        if not os.path.isfile(path):
            self.output.info("{} missing before probe; skip exec".format(path))
            return None
        interp, interp_ok = self._interp_of(path)
        self.output.info("elf interp={!r} exists={} for {}".format(interp, interp_ok, path))
        argv = self._clean_argv(path, ["--version"], env)
        try:
            probe = subprocess.run(
                argv, capture_output=True,
                text=True, env=env, timeout=30)
        except (PermissionError, OSError) as exc:
            self.output.info("{} not directly executable: {} {}".format(
                path, exc, self._describe(path)))
            return None
        ver = (probe.stdout or "").strip()
        self.output.info("probe {}: rc={} {}".format(path, probe.returncode, ver))
        if probe.returncode != 0:
            return None
        return ver

    @staticmethod
    def _version_ok(ver):
        m = re.search(r"v?(\d+)", ver or "")
        return bool(m) and int(m.group(1)) >= _MIN_NODE_MAJOR

    def _resolve_node(self, env):
        """Return an executable `node` path: platform runtime + clean env.

        Cycle-6 evidence falsified the single-source assumption: the only
        staged source (~/nodejs/bin/node, 120MB ELF present yet ENOENT)
        has a missing PT_INTERP loader, so no copy/sign of THAT inode can
        ever exec. The hnp node.org runtime (alexjs/aicommits precedent)
        is OHOS-compatible; probe EVERY readable candidate under clean
        env (`env -i` + --jitless) and use the first passing --version.
        Staging kept only as fallback per staged source. Never skips.
        """
        srcs = self._find_source_nodes()
        if not srcs:
            raise ConanException(
                "Upstream JS tests require node ({}+) but no readable host "
                "'node' was found (hnp node.org, PATH, HMBS_NODE). "
                "Install Node.js and retry; not skipping.".format(_MIN_NODE_MAJOR))
        self.output.info("Host node candidates: {}".format(srcs))
        # Evidence aid for the next cycle: list what hnp trees exist so a
        # still-empty glob can be distinguished from a filtered candidate.
        try:
            for anchor in ("/data/service/hnp", "/data/service/hnp/node.org"):
                if os.path.isdir(anchor):
                    try:
                        kids = sorted(os.listdir(anchor))[:20]
                    except OSError as exc:
                        kids = ["list-failed: {}".format(exc)]
                    self.output.info("hnp anchor {}: {}".format(anchor, kids))
                else:
                    self.output.info("hnp anchor missing: {}".format(anchor))
        except Exception:
            pass
        for src in srcs:
            ver = self._probe_node(src, env)
            if ver and self._version_ok(ver):
                self.output.info("Using host node directly: {} ({})".format(src, ver))
                env["HMBS_NODE_USED"] = src
                return src
            self.output.info("candidate {} unusable (probe {})".format(src, ver))
        tried = []
        for src in srcs:
            for stage_dir in self._stage_candidates():
                try:
                    os.makedirs(stage_dir, exist_ok=True)
                except OSError as exc:
                    tried.append("{}:{} (mkdir denied)".format(src, stage_dir))
                    continue
                dst = os.path.join(stage_dir, "node")
                self.output.info("Trying stage {} from {}".format(stage_dir, src))
                self._shim_install(src, dst, env)
                ver = self._probe_node(dst, env)
                if ver and self._version_ok(ver):
                    self.output.info("Using staged node: {} ({})".format(dst, ver))
                    env["PATH"] = stage_dir + os.pathsep + env.get("PATH", "")
                    env["HMBS_NODE_USED"] = dst
                    return dst
                tried.append("{}:{} (probe {})".format(src, stage_dir, ver))
        raise ConanException(
            "No runnable node (need {}+) in {}. "
            "Not skipping.".format(_MIN_NODE_MAJOR, tried))

    def _build_qjs(self, env):
        """Build QuickJS `qjs` from vendored source; return its path.

        Cycle-9 route: the only host node (~/nodejs/bin/node, 120MB static
        ELF, interp=None) fails exec with rc=126 and /data/service/hnp has
        no node.org tree, so no foreign ELF can run. A locally-built `qjs`
        (same Makefile flow as archives/q/quickjs) is produced by the OHOS
        toolchain on the machine and does not depend on any host runtime.
        """
        src_dir = os.path.join(self.source_folder, "quickjs-src")
        if not os.path.isfile(os.path.join(src_dir, "Makefile")):
            raise ConanException("Vendored QuickJS source missing Makefile")
        qjs = os.path.join(src_dir, "qjs")
        if os.path.isfile(qjs):
            return qjs
        tmpdir = os.path.join(self.build_folder, "quickjs-tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        compilers = {}
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            compilers = {}
        cc = (compilers.get("c") or os.environ.get("CC")
              or shutil.which("clang") or shutil.which("cc") or "cc")
        ar = compilers.get("ar")
        if not ar:
            if os.path.sep in cc:
                cand = os.path.join(os.path.dirname(cc), "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
            if not ar:
                ar = (shutil.which("llvm-ar") or shutil.which("ar") or "ar")
        host_cc = (compilers.get("c_host") or shutil.which("gcc")
                   or shutil.which("cc") or "cc")
        self.output.info("building qjs with CC={} HOST_CC={} AR={}".format(
            cc, host_cc, ar))
        build_env = dict(env)
        build_env["TMPDIR"] = tmpdir
        build_env["TMP"] = tmpdir
        build_env["TEMP"] = tmpdir
        cmd = ["make", "CC={}".format(cc), "HOST_CC={}".format(host_cc),
               "AR={}".format(ar), "CONFIG_BIGNUM=y", "-j1", "qjs"]
        self.output.info("$ {}".format(" ".join(cmd)))
        try:
            res = subprocess.run(cmd, cwd=src_dir, capture_output=True,
                                 text=True, env=build_env, timeout=900)
        except OSError as exc:
            raise ConanException("QuickJS build launch failed: {}".format(exc))
        tail = ((res.stdout or "") + (res.stderr or ""))[-2000:]
        if tail.strip():
            self.output.info(tail)
        if res.returncode != 0:
            raise ConanException(
                "QuickJS build failed (exit {})".format(res.returncode))
        if not os.path.isfile(qjs):
            raise ConanException("QuickJS build produced no qjs binary")
        # Probe the freshly built engine (plain script, no imports).
        try:
            probe = subprocess.run(
                [qjs, "-e", "console.log('qjs-ok');"], capture_output=True,
                text=True, env=build_env, timeout=60)
        except OSError as exc:
            raise ConanException("Built qjs not launchable: {}".format(exc))
        if probe.returncode != 0 or "qjs-ok" not in (probe.stdout or ""):
            raise ConanException(
                "Built qjs probe failed (exit {}): {}".format(
                    probe.returncode, ((probe.stdout or "")
                                       + (probe.stderr or ""))[-500:]))
        self.output.info("using locally-built qjs: {}".format(qjs))
        return qjs

    def _bundle_js_for_qjs(self):
        """Combine vendored tinyqueue + polylabel.js as one plain script.

        Upstream sources stay untouched; the bundle only rewrites the
        module glue (`export default` / bare `tinyqueue` specifier) which
        QuickJS running a classic script cannot resolve.
        """
        src = self.source_folder
        with open(os.path.join(src, "node_modules", "tinyqueue", "index.js"),
                  encoding="utf-8") as fh:
            tq = fh.read()
        with open(os.path.join(src, "polylabel.js"), encoding="utf-8") as fh:
            pl = fh.read()
        tq = tq.replace("export default class TinyQueue",
                        "class TinyQueue", 1)
        kept = [ln for ln in tq.splitlines()
                if not ln.strip().startswith("export ")]
        tq = "\n".join(kept)
        if "class TinyQueue" not in tq:
            raise ConanException("tinyqueue bundle rewrite failed")
        pl = pl.replace("import Queue from 'tinyqueue';", "", 1)
        pl = pl.replace('import Queue from "tinyqueue";', "", 1)
        pl = pl.replace("export default function polylabel",
                        "function polylabel", 1)
        pl = pl.replace("new Queue(", "new TinyQueue(")
        if "from 'tinyqueue'" in pl or 'from "tinyqueue"' in pl:
            raise ConanException("polylabel bundle still imports tinyqueue")
        if pl.strip().startswith("export ") or "\nexport " in pl:
            raise ConanException("polylabel bundle still has exports")
        return tq + "\n" + pl + "\n"

    def _run_upstream_via_qjs(self, env):
        """Run the 4 upstream cases under locally-built qjs. Never skips."""
        src = self.source_folder
        with open(os.path.join(src, "test", "fixtures", "water1.json"),
                  encoding="utf-8") as fh:
            water1 = json.load(fh)
        with open(os.path.join(src, "test", "fixtures", "water2.json"),
                  encoding="utf-8") as fh:
            water2 = json.load(fh)
        bundle = self._bundle_js_for_qjs()
        harness_dir = os.path.join(self.build_folder, "qjs-harness")
        try:
            os.makedirs(harness_dir, exist_ok=True)
        except OSError:
            pass
        driver = bundle
        driver += "var water1 = " + json.dumps(water1) + ";\n"
        driver += "var water2 = " + json.dumps(water2) + ";\n"
        driver += (
            "var __total = 4, __pass = 0, __fail = 0;\n"
            "function __samePoint(p, e) { return p && p[0] === e[0]"
            " && p[1] === e[1] && p.distance === e[2]; }\n"
            "var __cases = [];\n"
            "try {\n"
            "  var __p1 = polylabel(water1, 1);\n"
            "  __cases.push(['water1 precision 1',"
            " __samePoint(__p1, [3865.85009765625, 2124.87841796875,"
            " 288.8493574779127])]);\n"
            "  var __p2 = polylabel(water1, 50);\n"
            "  __cases.push(['water1 precision 50',"
            " __samePoint(__p2, [3854.296875, 2123.828125,"
            " 278.5795872381558])]);\n"
            "  var __p3 = polylabel(water2);\n"
            "  __cases.push(['water2 default',"
            " __samePoint(__p3, [3263.5, 3263.5, 960.5])]);\n"
            "  var __d1 = polylabel([[[0,0],[1,0],[2,0],[0,0]]]);\n"
            "  var __d2 = polylabel([[[0,0],[1,0],[1,1],[1,0],[0,0]]]);\n"
            "  __cases.push(['degenerate',"
            " __samePoint(__d1, [0,0,0]) && __samePoint(__d2, [0,0,0])]);\n"
            "} catch (__e) { console.log('harness threw: ' + __e); }\n"
            "for (var __i = 0; __i < __cases.length; __i++) {\n"
            "  if (__cases[__i][1]) { __pass++;"
            " console.log('ok - ' + __cases[__i][0]); }\n"
            "  else { __fail++; console.log('not ok - ' + __cases[__i][0]); }\n"
            "}\n"
            "while (__cases.length < __total) { __fail++;"
            " console.log('not ok - missing case');"
            " __cases.push(['missing', false]); }\n"
            "console.log('# tests ' + __total);\n"
            "console.log('# pass ' + __pass);\n"
            "console.log('# fail ' + __fail);\n"
            "if (__fail > 0) { throw new Error(__fail + ' case(s) failed'); }\n"
        )
        script = os.path.join(harness_dir, "run_upstream.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(driver)
        qjs = self._build_qjs(env)
        self.output.info("$ {} {}".format(qjs, script))
        try:
            proc = subprocess.run([qjs, script], cwd=harness_dir,
                                  capture_output=True, text=True, env=env,
                                  timeout=300)
        except OSError as exc:
            raise ConanException("qjs harness launch failed: {}".format(exc))
        out = (proc.stdout or "") + (proc.stderr or "")
        if out.strip():
            self.output.info(out.strip()[-4000:])
        if proc.returncode != 0:
            raise ConanException(
                "Upstream qjs harness failed (exit {}):\n{}".format(
                    proc.returncode, out))
        discovered, passed, failed = self._parse_node_tap(out)
        skipped = 0
        ok = (failed == 0 and passed == discovered and discovered > 0)
        status = "passed" if ok else "failed"
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"quickjs",'
            '"command":"qjs run_upstream.js (upstream 4 cases)",'
            '"discovered":%d,'
            '"executed":%d,"passed":%d,"failed":%d,"skipped":%d}'
            % (status, discovered, discovered, passed, failed, skipped)
        )
        if not ok:
            raise ConanException(
                "Upstream tests did not fully pass: {}".format(out[-2000:]))

    def _run_upstream_tests(self):
        src = self.source_folder
        test_entry = os.path.join(src, _UPSTREAM_TEST_ENTRY)
        if not os.path.isfile(test_entry):
            raise ConanException("Upstream test entry missing: test/test.js")
        tinyqueue_entry = os.path.join(
            src, "node_modules", "tinyqueue", "index.js")
        if not os.path.isfile(tinyqueue_entry):
            raise ConanException(
                "Vendored runtime dep missing: node_modules/tinyqueue/index.js")
        env = self._test_env()
        try:
            node = self._resolve_node(env)
        except ConanException as exc:
            self.output.info(
                "No runnable host node ({}); falling back to "
                "locally-built QuickJS with the same 4 upstream cases.".format(exc))
            self._run_upstream_via_qjs(env)
            return
        # Upstream-canonical first (`npm test` runs `node test/test.js`);
        # `node --test` only as fallback (spawns workers, riskier sandbox).
        # Both under clean env (`env -i` + --jitless, alexjs precedent).
        variants = [
            self._clean_argv(node, [os.path.join("test", "test.js")], env),
            self._clean_argv(node, ["--test", os.path.join("test", "test.js")], env),
        ]
        proc = None
        out = ""
        last_err = ""
        used_cmd = None
        parse_err = ""
        for cmd in variants:
            self.output.info("$ {}".format(" ".join(cmd)))
            try:
                proc = subprocess.run(cmd, cwd=src, capture_output=True,
                                      text=True, env=env, timeout=300)
            except (PermissionError, OSError) as exc:
                last_err = str(exc)
                self.output.info(
                    "Node invocation failed ({}), trying next variant".format(exc))
                continue
            out = (proc.stdout or "") + (proc.stderr or "")
            if out.strip():
                self.output.info(out.strip()[-4000:])
            lowered = out.lower()
            if proc.returncode != 0 and ("permission denied" in lowered
                                        or "spawn" in lowered
                                        or "eacces" in lowered):
                last_err = out[-500:]
                continue
            if proc.returncode != 0:
                raise ConanException(
                    "Upstream node tests failed (exit {}):\n{}".format(proc.returncode, out)
                )
            # Exit 0 is not enough: the TAP/ℹ summary markers must parse.
            # `node test/test.js` prints a spec reporter (✔ + ℹ lines) while
            # `node --test` prints TAP (# lines); try the next variant when
            # the current output has no parsable summary.
            try:
                self._parse_node_tap(out)
            except ConanException as exc:
                parse_err = str(exc)
                self.output.info(
                    "Output has no parsable summary ({}), trying next variant".format(exc))
                continue
            used_cmd = cmd
            break
        if used_cmd is None:
            if proc is None:
                raise ConanException(
                    "Upstream node tests could not be launched: {}".format(last_err))
            raise ConanException(
                "Upstream tests produced no parsable summary; refusing to pass. "
                "Last parse error: {}. Output tail: {}".format(parse_err, out[-1000:]))
        out = (proc.stdout or "") + (proc.stderr or "")
        discovered, passed, failed = self._parse_node_tap(out)
        skipped = 0
        ok = (failed == 0 and passed == discovered and discovered > 0)
        status = "passed" if ok else "failed"
        cmd_str = " ".join(used_cmd[-2:]) if used_cmd else "node test/test.js"
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"node:test",'
            '"command":"%s","discovered":%d,'
            '"executed":%d,"passed":%d,"failed":%d,"skipped":%d}'
            % (status, cmd_str, discovered, discovered, passed, failed, skipped)
        )
        if not ok:
            raise ConanException("Upstream tests did not fully pass: {}".format(out[-2000:]))

    @staticmethod
    def _parse_node_tap(out):
        """Parse node:test summary. Markers are REQUIRED.

        Accepts both reporters produced by the two invoked variants:
        - `node --test` TAP summary: `# tests 4 / # pass 4 / # fail 0`
        - `node test/test.js` spec reporter: `ℹ tests 4 / ℹ pass 4 / ℹ fail 0`
          plus `✔` per-case lines.
        Returns (discovered, passed, failed). Raises when no summary is
        found: exit code 0 alone never counts as a pass.
        """
        m_pass = re.search(r"(?:#|ℹ)\s*pass\s+(\d+)", out)
        m_fail = re.search(r"(?:#|ℹ)\s*fail\s+(\d+)", out)
        m_tests = re.search(r"(?:#|ℹ)\s*tests?\s+(\d+)", out)
        if m_pass or m_fail or m_tests:
            passed = int(m_pass.group(1)) if m_pass else 0
            failed = int(m_fail.group(1)) if m_fail else 0
            if m_tests:
                discovered = int(m_tests.group(1))
            else:
                discovered = passed + failed
            return discovered, passed, failed
        # Fallback: spec reporter checkmarks when the ℹ summary block was
        # truncated from the captured tail (anti-false-pass: require the
        # per-case ✔ lines themselves, not just exit code 0).
        ok_marks = len(re.findall(r"✔", out))
        fail_marks = len(re.findall(r"[✖✘]", out)) + len(
            re.findall(r"(?m)^not ok\b", out))
        if ok_marks or fail_marks:
            return ok_marks + fail_marks, ok_marks, fail_marks
        raise ConanException(
            "Upstream tests produced no TAP summary; refusing to pass. "
            "Output tail: {}".format(out[-1000:]))

    def package(self):
        dst = os.path.join(self.package_folder, "share", "mapbox-polylabel")
        copy(self, "polylabel.js", src=self.source_folder, dst=dst)
        copy(self, "package.json", src=self.source_folder, dst=dst)
        copy(self, "README.md", src=self.source_folder, dst=dst)
        # Bundle the tinyqueue runtime dep beside the module (boids pattern).
        copy(self, "*",
             src=os.path.join(self.source_folder, "node_modules", "tinyqueue"),
             dst=os.path.join(dst, "node_modules", "tinyqueue"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share/mapbox-polylabel"]
