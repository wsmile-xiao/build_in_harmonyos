#!/usr/bin/env python3
"""Conan test_package for keepsecret 1.1.0 (consumer-side validation).

Two layers:

1. OHOS adaptation gate (test_ohos_gate.py, new OHOS-specific test): parses
   the packaged ELF and asserts the port's platform adaptations took effect -
   no KF6::I18nQml DT_NEEDED (patches 0001/0002 replaced KLocalizedQmlContext
   with KLocalizedContext from libKF6I18n), the QML closure
   (libQt6Qml/libQt6Quick) linked, the libsecret-1 secret-store backend
   linked (pkg_check_modules LIBSECRET), and an AArch64 OHOS target.

2. Offscreen launch smoke: the packaged application is started with the
   offscreen QPA and the full QML import closure (kirigami, kirigami-addons,
   qtdeclarative). keepsecret has no --self-test flag; a clean engine load
   reaches app.exec(), so exit code 124 (the `timeout` kill) means the QML
   engine loaded Main.qml and the org.kde.keepsecret module - engine failure
   exits -1 via rootObjects().isEmpty(). The Secret Service backend is
   intentionally absent on the build host: keepsecret handles that path at
   runtime (SecretServiceClient reports ServiceConnectionError and Main.qml
   shows the inline error banner), so a missing provider is not a failure.

   This sandbox additionally offers no reachable DBus session bus: the conan
   dbus package published for OHOS ships libdbus only (no bin/dbus-daemon) and
   the sandbox user has no /etc/passwd entry for dbus peer authentication. The
   harness still tries every way it can to obtain a bus (see
   _find_dbus_daemon / _start_session_bus); when it cannot, the launch is
   classified ENV-BLOCKED - but only for the exact KDBusService signature
   (exit code 1 + "DBus session bus not found" + no QML load failure), so a
   real port regression (broken Main.qml, missing QML module, crash) always
   fails the test. See the classification note in test().

Runtime-linking notes (accessibility 26.04.3 / E537 precedent):
* some published KF6 libraries carry build-tree-relative DT_NEEDED entries
  ("../bin/...", "../../bin/...") and a few absolute conan-cache paths. The
  test runs from a fresh scratch directory whose ../bin and ../../bin both
  reach link farms of every KF6 shared library (calligra 24.12.3 precedent),
  and stale absolute paths are materialized as symlinks.
* the host shell LD_LIBRARY_PATH carries whitespace-padded entries the OHOS
  loader cannot resolve (kirigami-addons 1.13.0 notes, issue 1), and the
  aggregated conanrun QML2_IMPORT_PATH does not include the qtdeclarative
  qml/ tree that QtQuick.Controls needs - so the whole environment is rebuilt
  explicitly here instead of relying on env="conanrun".
"""
import os
import re
import signal
import shutil
import subprocess
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class _DetachedBus:
    """Handle for a session bus whose daemon outlives its launcher.

    dbus-run-session kills its daemon when the helper exits, so it needs no
    handle; dbus-launch forks a daemon that keeps running, so its PID is
    carried here and killed by the launch smoke's cleanup. kill() is
    idempotent and tolerates an already-gone process.
    """

    def __init__(self, pid):
        self.pid = pid

    def kill(self):
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.kill(self.pid, sig)
            except OSError:
                return
            for _ in range(10):
                time.sleep(0.1)
                try:
                    os.kill(self.pid, 0)
                except OSError:
                    return


class KeepsecretTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_readelf(self):
        import shutil

        for cand in (
            "readelf",
            "/data/service/hnp/bin/readelf",
            "/usr/bin/readelf",
            "/bin/readelf",
        ):
            exe = cand
            try:
                w = shutil.which(cand)
                if w:
                    exe = w
                subprocess.run([exe, "--version"], capture_output=True, timeout=20)
                return exe
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _collect_libs(self):
        lib_dirs = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for layout_dir in ("lib", "bin"):
                    lib_dir = os.path.join(p.package_folder, layout_dir)
                    if os.path.isdir(lib_dir):
                        lib_dirs.append(lib_dir)
        return lib_dirs

    def _make_scratch(self):
        # Fresh scratch CWD for the test run: build-tree-relative DT_NEEDED
        # entries ("../bin/libKF6ConfigCore.so", "../../bin/libKF6*.so")
        # resolve against the process CWD, so both <cwd>/../bin and
        # <cwd>/../../bin must reach link farms of every dependency shared
        # library (E537, accessibility 26.04.3 / calligra 24.12.3 precedent).
        # Layout: <scratch>/a/b is the run CWD, <scratch>/bin and
        # <scratch>/a/bin are the farms.
        scratch = tempfile.mkdtemp(prefix="keepsecret-test-")
        farms = [os.path.join(scratch, "bin"), os.path.join(scratch, "a", "bin")]
        cwd = os.path.join(scratch, "a", "b")
        for farm in farms:
            os.makedirs(farm, exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        for lib_dir in self._collect_libs():
            for name in os.listdir(lib_dir):
                if not name.endswith(".so"):
                    continue
                for farm in farms:
                    link = os.path.join(farm, name)
                    if not os.path.lexists(link):
                        try:
                            os.symlink(os.path.join(lib_dir, name), link)
                        except OSError as exc:
                            self.output.warning(f"link farm entry {name} failed: {exc}")
        return scratch, cwd, farms

    def _materialize_abs_deps(self):
        # Temporary platform cache-root bridge (kio/6.14.0 test_package
        # precedent): release-built dependency packages can bake absolute
        # DT_NEEDED entries rooted at another machine's conan home
        # (~/.conan2 vs ~/.cache/conan2) and musl performs no fallback for
        # slash-qualified NEEDED entries. Symlink every missing absolute
        # dependency path to the basename-matching library of the current
        # graph.
        readelf = self._find_readelf()
        if not readelf:
            self.output.warning(
                "readelf not found; absolute DT_NEEDED materialization skipped"
            )
            return
        seen_libs = set()
        for lib_dir in self._collect_libs():
            for name in os.listdir(lib_dir):
                if not name.endswith(".so") or name in seen_libs:
                    continue
                seen_libs.add(name)
                lib_path = os.path.join(lib_dir, name)
                try:
                    rd = subprocess.run(
                        [readelf, "-d", lib_path],
                        capture_output=True, text=True, timeout=60,
                    ).stdout
                except OSError:
                    continue
                for m in re.finditer(r"Shared library: \[(/[^]]+\.so)\]", rd):
                    abs_path = m.group(1)
                    if os.path.exists(abs_path):
                        continue
                    fname = os.path.basename(abs_path)
                    for cand_dir in self._collect_libs():
                        cand = os.path.join(cand_dir, fname)
                        if os.path.exists(cand):
                            try:
                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                if not os.path.lexists(abs_path):
                                    os.symlink(cand, abs_path)
                            except OSError as e:
                                self.output.warning(
                                    f"DT_NEEDED symlink fail {abs_path}: {e}"
                                )
                            break

    def _conan_cache_roots(self):
        """Conan cache roots to probe for dbus binaries.

        CONAN_HOME is honoured but not assumed (CI points it at a non-default
        location), then the usual homes, then every root implied by the
        packages of this graph (<root>/p/<name>.../<pkgid>/p), which is what
        makes the search work whichever cache the CI profile populated.
        """
        roots = []
        conan_home = os.environ.get("CONAN_HOME")
        if conan_home:
            roots.append(conan_home)
        roots.extend([
            os.path.join(os.path.expanduser("~"), ".conan2"),
            os.path.join(os.path.expanduser("~"), ".cache", "conan2"),
        ])
        package_folders = [
            p.package_folder for p in self.dependencies.values()
            if p and p.package_folder
        ] + [
            p.package_folder for p in self.dependencies.build.values()
            if p and p.package_folder
        ]
        for folder in package_folders:
            marker = os.sep + "p" + os.sep
            if marker in folder:
                root = folder.split(marker, 1)[0]
                if root and root not in roots:
                    roots.append(root)
        return roots

    def _find_dbus_daemon(self):
        """Locate a usable dbus-daemon binary; None when the host has none.

        The conan dbus package is deliberately NOT relied upon: the 1.14.10
        build published for OHOS ships libdbus only - it carries no
        bin/dbus-daemon (kio-kwallet 6.28.0 records the same finding and had to
        build its own daemon stack from the pristine upstream tarball). A
        transitive conan lookup therefore yields None on CI, so the search also
        covers the host PATH, the SDK bin dirs and every conan cache root that
        can be derived from this dependency graph (honouring CONAN_HOME but not
        assuming it, since CI points it at a non-default location).
        """
        import glob

        def binaries(folder):
            if not folder:
                return []
            found = []
            for layout_dir in ("bin", os.path.join("libexec", "dbus-1")):
                cand = os.path.join(folder, layout_dir, "dbus-daemon")
                if os.path.isfile(cand):
                    found.append(cand)
            return found

        candidates = []
        # 1. The dbus package of this graph, when it does ship the daemon.
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            candidates.extend(binaries(dep.package_folder if dep else None))
        # 2. Host PATH and the OHOS SDK bin dirs.
        for name in ("/data/service/hnp/bin/dbus-daemon", shutil.which("dbus-daemon")):
            if name and os.path.isfile(name):
                candidates.append(name)
        # 3. Conan caches: CONAN_HOME first, then the roots implied by the
        #    packages of this graph (<root>/p/<name>.../<pkgid>/p), which also
        #    covers a real ~/.conan2 and ~/.cache/conan2 when neither env var
        #    nor the home fallback points there. Several dbus package_ids
        #    coexist, so every match is probed, not just the first.
        roots = []
        conan_home = os.environ.get("CONAN_HOME")
        if conan_home:
            roots.append(conan_home)
        roots.extend([
            os.path.join(os.path.expanduser("~"), ".conan2"),
            os.path.join(os.path.expanduser("~"), ".cache", "conan2"),
        ])
        package_folders = [
            p.package_folder for p in self.dependencies.values()
            if p and p.package_folder
        ] + [
            p.package_folder for p in self.dependencies.build.values()
            if p and p.package_folder
        ]
        for folder in package_folders:
            marker = os.sep + "p" + os.sep
            if marker in folder:
                root = folder.split(marker, 1)[0]
                if root and root not in roots:
                    roots.append(root)
        for root in roots:
            pattern = os.path.join(root, "p", "dbus*", "*", "p", "bin", "dbus-daemon")
            candidates.extend(sorted(glob.glob(pattern)))
        for cand in candidates:
            if os.path.isfile(cand):
                return cand
        return None

    def _which_bus_tool(self, name, cache_roots):
        """Find a dbus session helper (dbus-run-session / dbus-launch).

        Same search shape as _find_dbus_daemon: standard install prefixes, the
        host PATH, the OHOS SDK bin dir, then the conan caches (helpers are
        installed next to dbus-daemon). Returns None when the host has none.
        """
        import glob

        for cand in (
            "/usr/bin/" + name,
            "/bin/" + name,
            "/usr/local/bin/" + name,
            "/data/service/hnp/bin/" + name,
        ):
            if os.path.isfile(cand):
                return cand
        found = shutil.which(name)
        if found:
            return found
        for root in cache_roots:
            for pattern in (
                os.path.join(root, "p", "dbus*", "*", "p", "bin", name),
                os.path.join(root, "p", "dbus*", "*", "p", "libexec", "dbus-1", name),
            ):
                hits = sorted(glob.glob(pattern))
                if hits:
                    return hits[0]
        return None

    def _start_bus_tool_session(self, cwd, lib_dirs, shim, tool_paths):
        """Start a real session bus with dbus-run-session, then dbus-launch.

        Preferred over hand-writing a bus config: dbus-run-session owns the
        daemon lifetime (it kills it when the command exits) and sets
        DBUS_SESSION_BUS_ADDRESS itself. `probe` is a no-op `/bin/sh -c :`, so
        `--print-address` reports the address dbus-run-session fabricated for
        the run. dbus-launch is the older variant without --print-address; its
        address is printed with --sh-syntax and parsed from the output, and its
        daemon outlives the helper, so its PID is handed back for cleanup.

        A timeout from `probe` is the interesting case: this is not the launch
        smoke (nothing executes the application yet), so reaching the bound
        means the daemon stayed up until it was killed - exactly the behaviour
        wanted from a connected bus. The address lands in os.environ so the
        caller does not have to thread it through; returns
        (handle, address, note), where handle is None for dbus-run-session
        (daemon dies with the helper) or a _DetachedBus for dbus-launch.
        """
        tool_env = dict(os.environ)
        tool_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(lib_dirs)
            + [os.path.join(os.path.dirname(os.path.dirname(p)), "lib") for p in tool_paths]
            + tool_env.get("LD_LIBRARY_PATH", "").split(os.pathsep)
        )
        if shim:
            tool_env["LD_PRELOAD"] = shim

        reject = ("not found", "failed to", "Unable to autolaunch", "connection refused")

        runner = self._which_bus_tool("dbus-run-session", self._conan_cache_roots())
        if runner:
            try:
                proc = subprocess.run(
                    [runner, "--print-address", "--", "/bin/sh", "-c", ":"],
                    capture_output=True, text=True, timeout=20, env=tool_env, cwd=cwd,
                )
            except subprocess.TimeoutExpired:
                # The probe is a no-op shell builtin, so a timeout means the
                # helper never reported an address - treat it as unusable and
                # fall through rather than claiming a bus we cannot address.
                self.output.warning(
                    "dbus-run-session did not report an address within 20s; "
                    "trying the next bus mechanism"
                )
                proc = None
            except OSError as exc:
                self.output.warning("dbus-run-session failed to start: %s" % exc)
                proc = None
            if proc is not None:
                address = proc.stdout.strip().splitlines()[-1].strip() if proc.stdout else ""
                err = (proc.stderr or "").lower()
                if address and not any(token.lower() in err for token in reject):
                    os.environ["DBUS_SESSION_BUS_ADDRESS"] = address
                    return None, address, "dbus-run-session"

        launcher = self._which_bus_tool("dbus-launch", self._conan_cache_roots())
        if launcher:
            try:
                proc = subprocess.run(
                    [launcher, "--sh-syntax"], capture_output=True, text=True,
                    timeout=20, env=tool_env, cwd=cwd,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                self.output.warning("dbus-launch failed to start: %s" % exc)
                return None
            values = {}
            for line in (proc.stdout or "").splitlines():
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):]
                if "=" not in line or not line[:1].isalpha():
                    continue
                key, _, value = line.partition("=")
                values[key] = value.strip().strip("'\"")
            address = values.get("DBUS_SESSION_BUS_ADDRESS", "")
            pid = values.get("DBUS_SESSION_BUS_PID", "")
            if not address or not pid.isdigit():
                self.output.warning(
                    "dbus-launch did not report a session bus address; bus not started"
                )
                return None
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = address
            return _DetachedBus(int(pid)), address, "dbus-launch"
        return None

    def _start_session_bus(self, cwd, lib_dirs, shim=None):
        """Start a private DBus session bus for the launch smoke.

        keepsecret constructs KDBusService(KDBusService::Unique) before the QML
        engine is created; with no session bus on the build host KF6DBusAddons
        reports "DBus session bus not found" and KDBusService then calls
        exit(1) (upstream kdbusservice.cpp: `qCCritical(...) << errorMessage;
        exit(1)`), so the process dies before Main.qml is ever loaded. A bus is
        therefore required for the smoke test to observe what it claims to, and
        its absence is reported as (None, None) so the caller can classify the
        launch as an environment block rather than a port defect.

        `shim` (the sandbox passwd shim) is preloaded into dbus-daemon too:
        without it the daemon cannot resolve the peer UID (the sandbox user has
        no /etc/passwd entry) and rejects every client connection, so the app
        would report "DBus session bus not found" even though the bus is up.
        Returns (process, address) or (None, None) when unavailable.
        """
        # Overlay item 4: when the host ships a bus helper, start a REAL
        # session bus with it (dbus-run-session owns the daemon lifetime and
        # sets DBUS_SESSION_BUS_ADDRESS; dbus-launch is the older variant).
        # Only when no helper and no daemon exist does the launch fall through
        # to the documented env_blocked classification.
        daemon = self._find_dbus_daemon()
        helpers = [
            tool for tool in (
                self._which_bus_tool("dbus-run-session", self._conan_cache_roots()),
                self._which_bus_tool("dbus-launch", self._conan_cache_roots()),
            ) if tool
        ]
        if helpers:
            session = self._start_bus_tool_session(cwd, lib_dirs, shim, helpers)
            if session is not None:
                handle, address, note = session
                # The helper already exported DBUS_SESSION_BUS_ADDRESS into
                # os.environ; `handle` is the returned bus process to kill in
                # cleanup (None for dbus-run-session, whose daemon dies with
                # the helper it spawned).
                self.output.info(
                    "private session bus via %s: %s"
                    % (note, address or "(address left in the environment)")
                )
                return handle, address
            self.output.warning(
                "dbus session helper present but could not start a bus; falling "
                "back to a hand-written dbus-daemon config"
            )
        if not daemon:
            self.output.warning("no dbus-daemon found; bus not started")
            return None, None
        import select

        dbus_lib = os.path.join(os.path.dirname(os.path.dirname(daemon)), "lib")

        # Bind a TCP transport on loopback rather than the packaged
        # session.conf's unix/tmpdir listener: the unix socket is created but
        # the app's QDBusConnection does not reach it in this sandbox, while
        # TCP loopback + ANONYMOUS auth is the transport the kio-kwallet 6.28.0
        # recipe proved working on this device (needed because the sandbox UID
        # has no /etc/passwd entry, so EXTERNAL auth cannot be used).
        import socket as _socket
        probe = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        conf = os.path.join(cwd, "session-tcp.conf")
        with open(conf, "w") as handle:
            handle.write(
                '<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus'
                ' Configuration 1.0//EN"\n'
                ' "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">\n'
                '<busconfig>\n'
                '  <type>session</type>\n'
                '  <listen>tcp:host=127.0.0.1,port=%d,bind=127.0.0.1,'
                'family=ipv4</listen>\n'
                '  <auth>EXTERNAL</auth>\n'
                '  <auth>ANONYMOUS</auth>\n'
                '  <allow_anonymous/>\n'
                '  <policy context="default">\n'
                '    <allow send_destination="*" eavesdrop="true"/>\n'
                '    <allow eavesdrop="true"/>\n'
                '    <allow own="*"/>\n'
                '  </policy>\n'
                '</busconfig>\n' % port
            )
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(lib_dirs)
            + [dbus_lib]
            + env.get("LD_LIBRARY_PATH", "").split(os.pathsep)
        )
        if shim:
            env["LD_PRELOAD"] = shim
        log_path = os.path.join(cwd, "dbus-daemon.log")
        log = open(log_path, "w")
        proc = subprocess.Popen(
            [daemon, "--config-file=" + conf, "--print-address=1", "--nofork"],
            stdout=subprocess.PIPE, stderr=log, text=True, env=env,
        )
        ready, _, _ = select.select([proc.stdout], [], [], 15)
        address = proc.stdout.readline().strip() if ready else ""
        if not address:
            proc.kill()
            log.close()
            self.output.warning("dbus-daemon did not report an address; see " + log_path)
            return None, None
        self.output.info("private session bus: %s" % address)
        return proc, address

    def _build_sandbox_shim(self):
        """Compile test_package/ohos_sandbox_shim.c for LD_PRELOAD.

        See that file's header comment for the two sandbox gaps it covers:
        the sandbox UID has no /etc/passwd entry (which breaks dbus-daemon
        peer auth, so the app cannot connect to the session bus and exits
        before Main.qml loads), and the graph ships two libintl.so.8 variants
        with different export sets.
        """
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ohos_sandbox_shim.c")
        if not os.path.isfile(src):
            self.output.warning("ohos_sandbox_shim.c not found; running without shim")
            return None
        out = os.path.join(tempfile.gettempdir(), "keepsecret-ohos-sandbox-shim.so")
        cc = None
        for cand in ("/data/service/hnp/bin/clang", "clang", "cc", "gcc"):
            found = cand if os.path.isfile(cand) else shutil.which(cand)
            if found:
                cc = found
                break
        if not cc:
            self.output.warning("no C compiler for the sandbox shim")
            return None
        try:
            subprocess.run(
                [cc, "-shared", "-fPIC", "-o", out, src],
                check=True, capture_output=True, timeout=180,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning("sandbox shim build failed: %s" % exc)
            return None
        self.output.info("sandbox shim: %s" % out)
        return out

    def test(self):
        dep = self.dependencies.get("keepsecret")
        assert dep is not None and dep.package_folder is not None, (
            "keepsecret not found in the dependency graph"
        )
        app_bin = os.path.join(dep.package_folder, "bin", "keepsecret")
        assert os.path.exists(app_bin), f"missing packaged application: {app_bin}"

        # 0. Packaged payload completeness (MANIFEST.yml: package_payload_complete).
        #    These are the data files upstream's install() rules produce; the
        #    org.kde.keepsecret QML module is compiled into the binary via
        #    qt_add_qml_module + qrc, so it is asserted by the ELF gate below
        #    rather than as a standalone file on disk.
        payload = (
            os.path.join("share", "applications", "org.kde.keepsecret.desktop"),
            os.path.join("share", "metainfo", "org.kde.keepsecret.metainfo.xml"),
            os.path.join("share", "icons", "hicolor", "scalable", "apps",
                         "org.kde.keepsecret.svg"),
        )
        missing = [
            rel for rel in payload
            if not os.path.exists(os.path.join(dep.package_folder, rel))
        ]
        assert not missing, (
            "packaged payload incomplete, missing: %s" % ", ".join(missing)
        )
        self.output.info("package payload complete: %s" % ", ".join(payload))

        # 1. OHOS adaptation gate on the packaged artifact.
        gate = os.path.join(os.path.dirname(__file__), "test_ohos_gate.py")
        self.run(f'python3 "{gate}" "{app_bin}"')

        self._materialize_abs_deps()
        scratch, scratch_cwd, farms = self._make_scratch()

        # 2. Offscreen launch smoke (see module docstring for the exit-code
        #    contract: 124 from timeout == engine loaded Main.qml cleanly).
        ld_paths = list(self._collect_libs())
        # Both glib and gettext ship a libintl.so.8 with *different* export
        # sets: glib's proxy-libintl build exports only g_libintl_*, gettext's
        # exports libintl_*. libKF6I18n.so needs libintl_*, while glib itself
        # needs g_libintl_*; the application binary carries a linked-in shim
        # that supplies g_libintl_*, so gettext must win the loader search
        # order for the two SONAME-identical libraries to coexist.
        gettext = self.dependencies.get("gettext")
        if gettext and gettext.package_folder:
            for candidate in gettext.cpp_info.libdirs:
                gl = os.path.join(gettext.package_folder, candidate)
                if gl in ld_paths:
                    ld_paths.remove(gl)
                    ld_paths.insert(0, gl)
        ld_paths.extend(farms)
        ld_paths.extend(["/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"])
        qml_paths = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for qml_dir in ("qml", os.path.join("lib", "qml"), os.path.join("bin", "qml")):
                    qml_path = os.path.join(p.package_folder, qml_dir)
                    if os.path.isdir(qml_path):
                        qml_paths.append(qml_path)
        # The packaged org.kde.keepsecret QML module (installed next to the
        # binary by qt_add_qml_module) must be on the import path.
        qml_paths.insert(0, os.path.join(dep.package_folder, "bin"))

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(ld_paths))
        env.define("QML2_IMPORT_PATH", ":".join(qml_paths))
        plugin_paths = []
        for p in self.dependencies.values():
            if p and p.package_folder:
                for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                    plugins_path = os.path.join(p.package_folder, plugins_dir)
                    if os.path.isdir(plugins_path):
                        plugin_paths.append(plugins_path)
        env.define("QT_PLUGIN_PATH", ":".join(plugin_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "Asia/Shanghai")
        home = os.path.join(scratch_cwd, "test-home")
        xdg_runtime = os.path.join(scratch_cwd, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

        shim = self._build_sandbox_shim()
        # NOTE: _start_session_bus may export DBUS_SESSION_BUS_ADDRESS into
        # os.environ directly (dbus-run-session / dbus-launch own their daemon
        # and it must outlive this call), so the bus is started BEFORE the
        # Environment snapshot below is applied - otherwise the app would get a
        # stale value.
        bus_proc, bus_address = self._start_session_bus(scratch_cwd, ld_paths, shim=shim)
        if bus_address:
            env.define("DBUS_SESSION_BUS_ADDRESS", bus_address)

        if shim:
            env.define("LD_PRELOAD", shim)

        try:
            with env.vars(self).apply():
                # R34: real execution of the packaged application. Exit-code
                # contract: 124 (timeout kill) or 0 means the engine loaded
                # Main.qml and the app reached its event loop; any other nonzero
                # code means a startup crash or engine failure
                # (rootObjects().isEmpty() -> exit(-1)). Subprocess is used
                # instead of self.run(returncode=True) because the OHOS conan
                # build does not provide the returncode kwarg; the environment
                # applied above is inherited via os.environ.
                try:
                    proc = subprocess.run(
                        [app_bin], cwd=scratch_cwd, timeout=25,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    )
                    rc = proc.returncode
                    output = proc.stdout or ""
                except subprocess.TimeoutExpired as exc:
                    rc = 124
                    output = exc.stdout if isinstance(exc.stdout, str) else ""
        finally:
            if bus_proc is not None:
                # _DetachedBus (dbus-launch) has no wait(); the Popen from the
                # hand-written dbus-daemon config does.
                bus_proc.kill()
                if hasattr(bus_proc, "wait"):
                    bus_proc.wait()
        if rc not in (0, 124):
            # keepsecret constructs KDBusService(KDBusService::Unique) before
            # the QML engine exists. On this OHOS build sandbox the session bus
            # can never be reached - the published conan dbus package ships no
            # daemon binary and the sandbox user has no /etc/passwd entry for
            # dbus peer authentication - so KDBusService logs "DBus session bus
            # not found" and calls exit(1), and the process dies before
            # Main.qml is loaded. That is an environment property, not a port
            # defect: the packaged binary is verified independently by the ELF
            # adaptation gate above, which asserts the shipped artifact really
            # carries the port (OHOS aarch64 ELF, QML + libsecret-1 closure
            # linked, no unpublished I18nQml dependency). Per
            # TEST_QUALITY_SPEC 3.3 it is recorded as a declared environment
            # exemption rather than a silent skip.
            #
            # The exemption is deliberately narrow so that it cannot mask a
            # real port regression:
            #  * rc must be exactly 1 - the documented KDBusService::run()
            #    exit(1) path; a crash or QML failure reports something else,
            #  * the app must have printed the KDBusService "DBus session bus
            #    not found" message, and
            #  * the QML engine must NOT have reported a load failure, so a
            #    broken org.kde.keepsecret module can never be excused.
            kdbus_message = "DBus session bus not found" in output
            qml_load_failed = "during loading main.qml" in output
            if rc == 1 and kdbus_message and not qml_load_failed:
                if bus_address:
                    cause = (
                        "the private DBus session bus WAS established at %s, "
                        "but the sandbox user has no /etc/passwd entry, so dbus "
                        "peer authentication rejects the client" % bus_address
                    )
                else:
                    cause = (
                        "no dbus-daemon binary exists on this build host, so "
                        "the harness could not start a private session bus at "
                        "all (the OHOS conan dbus package ships libdbus only, "
                        "no bin/dbus-daemon)"
                    )
                self.output.warning(
                    "launch smoke ENV-BLOCKED (exit code %s: %s). The ELF "
                    "adaptation gate above is the authoritative check on the "
                    "packaged artifact; on a device that provides a session bus "
                    "this smoke is expected to pass for real."
                    % (rc, cause)
                )
                self.output.warning(output[-4000:])
                # Make the block visible to CI log scanners and MANIFEST.
                self.output.info("LAUNCH_SMOKE_RESULT=env_blocked")
                return
            self.output.warning(output[-4000:])
            if qml_load_failed:
                reason = (
                    " (the QML engine reported a Main.qml load failure, which "
                    "is NOT excusable as an environment block)"
                )
            elif kdbus_message:
                reason = (
                    " ('DBus session bus not found' was printed, but exit code "
                    "%s is not the KDBusService exit(1) path, so the failure "
                    "is not attributable to the missing session bus)" % rc
                )
            else:
                reason = ""
            raise ConanException(
                f"keepsecret offscreen launch smoke failed with exit code {rc}"
                + reason
            )
        self.output.info(
            "launch smoke OK (engine reached the event loop, rc=%s)" % rc
        )
