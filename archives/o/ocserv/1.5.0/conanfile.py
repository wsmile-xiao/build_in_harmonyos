#!/usr/bin/env python3
"""Conan recipe for ocserv 1.5.0 — Meson project (VPN server, executable).

ocserv is the OpenConnect VPN server. Upstream uses the Meson build system
(since 1.3.0; the 1.5.0 release tarball ships meson.build only). This recipe
cross-builds the ocserv/ocserv-worker/occtl/ocpasswd executables for
HarmonyOS PC (aarch64, musl, clang 15).

Key adaptation notes:
- Dependencies taken from the ohpcd registry: gnutls, libev, readline
  (nettle/libtasn1/libgcrypt/gpg-error/gmp/libunistring come transitively
  from gnutls). talloc/llhttp/protobuf-c/pcl/ccan/inih/gnulib are bundled
  in the ocserv source tree (-Dlocal-*=true), matching the upstream CI
  recipe (`.gitlab-ci.yml` uses -Dlocal-protobuf=true -Dlocal-talloc=true).
- protobuf-c code generation: protoc/protoc-c are unavailable on the OHOS
  build host and in CI. The recipe ships pre-generated ipc/ctl/cfg pb-c
  files via patches/0001-ohos-adaptation.patch (generated with protoc
  3.21.12 + protoc-gen-c 1.5.2 on the device), satisfying the meson
  fallback "fs.exists('ipc.pb-c.c')" branch in src/meson.build.
- getpass(3) is not provided by OHOS musl; patches add an __OHOS__
  replacement for ocpasswd.
- tests/meson.build upstream assumes gnutls headers in the default system
  include path; with a conan-prefixed gnutls the dependency must be
  propagated explicitly into test_base_deps.
- meson is vendored (official 1.11.2 source) and invoked in-process via
  `python3 -c` + mesonmain.main() — the same proven approach as
  astroterm/1.0.9 (no meson executable on the OHOS/CI PATH, no meson
  package resolvable from the remotes).

R38: ocserv is a command-line tool package (executables), commands.json
declares the binaries at the software level.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import MesonToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class OcservConan(ConanFile):
    name = "ocserv"
    version = "1.5.0"
    description = "OpenConnect VPN server (Cisco AnyConnect/OpenConnect protocol)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/ocserv/ocserv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def requirements(self):
        # W0 verified on ohpcd registry via `conan download --only-recipe`.
        # gnutls transitively provides nettle/libtasn1/libgcrypt/
        # libgpg-error/gmp/libunistring.
        self.requires("gnutls/3.8.10")
        self.requires("libev/4.33")
        # readline enables occtl (management CLI). It transitively pulls
        # ncursesw for terminal handling.
        self.requires("readline/8.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # vendored meson (astroterm/1.0.9 proven approach)
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(
            self,
            **self.conan_data["meson_source"],
            strip_root=True,
            destination=mv,
        )

    # ------------------------------------------------------------------
    # vendored meson invocation helpers (astroterm/1.0.9 proven pattern)
    # ------------------------------------------------------------------
    _PY_HOME = "/data/service/hnp/python.org/python_3.12"
    _PY_LIB = "/data/service/hnp/python.org/python_3.12/lib"

    def _meson_cmd(self, meson_argv):
        py = os.environ.get("HMBS_PYTHON3") or "python3"
        mv = os.path.join(self.source_folder, "meson-vendor")
        argv_lit = json.dumps(["meson"] + list(meson_argv))
        mv_lit = json.dumps(mv)
        script = (
            "import sys;"
            f"sys.path.insert(0,{mv_lit});"
            f"sys.argv={argv_lit};"
            "from mesonbuild import mesonmain;"
            "rc=mesonmain.main();"
            "sys.exit(rc or 0)"
        )
        return py, ["-c", f"'{script}'"]

    def _meson_env(self, extra=None):
        env = {"PATH": os.environ.get("PATH", "")}
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        if os.path.isdir(self._PY_HOME):
            env["PYTHONHOME"] = self._PY_HOME
        ll = os.environ.get("LD_LIBRARY_PATH", "")
        if os.path.isdir(self._PY_LIB):
            env["LD_LIBRARY_PATH"] = (self._PY_LIB + ":" + ll).strip(":")
        for k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra:
            env.update(extra)
        return [f"{k}={v}" for k, v in env.items()]

    def _dep_pkgconfig_dirs(self):
        dirs = []
        for dep_name in ("gnutls", "libev", "readline", "ncurses"):
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            # conan packages may ship .pc either in lib/ or lib/pkgconfig/
            for sub in ("lib", "lib/pkgconfig"):
                pkg_dir = os.path.join(dep.package_folder, sub)
                if any(f.endswith(".pc") for f in os.listdir(pkg_dir)) \
                        if os.path.isdir(pkg_dir) else False:
                    dirs.append(pkg_dir)
                    break
        # gnutls transitive deps (nettle, libtasn1, libgcrypt, ...)
        try:
            gnutls = self.dependencies["gnutls"]
            for dep in gnutls.dependencies.values():
                for sub in ("lib", "lib/pkgconfig"):
                    pkg_dir = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(pkg_dir) and any(
                            f.endswith(".pc") for f in os.listdir(pkg_dir)):
                        dirs.append(pkg_dir)
                        break
        except Exception:
            pass
        return dirs

    def _dep_lib_dirs(self):
        dirs = []
        for dep_name in ("gnutls", "libev", "readline", "ncurses"):
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            # gnutls deps (nettle etc.) are transitive — collect them too
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                dirs.append(lib_dir)
        # gnutls transitive deps (nettle, libtasn1, libgcrypt, ...)
        try:
            gnutls = self.dependencies["gnutls"]
            for dep in gnutls.dependencies.values():
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    dirs.append(lib_dir)
        except Exception:
            pass
        return dirs

    def _dep_include_dirs(self):
        dirs = []
        for dep_name in ("libev", "readline"):
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            for inc_dir in dep.cpp_info.includedirs:
                if os.path.isdir(inc_dir):
                    dirs.append(inc_dir)
        return dirs

    def generate(self):
        tc = MesonToolchain(self)
        # Application package: executables only, no shared libs produced.
        tc.project_options["default_library"] = "static"
        # Bundled subprojects (upstream .gitlab-ci.yml recipe):
        # talloc/llhttp/protobuf-c/pcl compiled from src/ tree.
        tc.project_options["local-talloc"] = "true"
        tc.project_options["local-llhttp"] = "true"
        tc.project_options["local-protobuf"] = "true"
        tc.project_options["local-pcl"] = "true"
        # Optional deps disabled (not available in the ohpcd registry,
        # not required for core VPN server functionality).
        tc.project_options["pam"] = "disabled"
        tc.project_options["radius"] = "disabled"
        tc.project_options["gssapi"] = "disabled"
        tc.project_options["liboath"] = "disabled"
        tc.project_options["libnl"] = "disabled"
        tc.project_options["maxmind"] = "disabled"
        tc.project_options["geoip"] = "disabled"
        tc.project_options["lz4"] = "disabled"
        tc.project_options["seccomp"] = "disabled"
        tc.project_options["systemd"] = "disabled"
        tc.project_options["utmp"] = "disabled"
        tc.project_options["libwrap"] = "disabled"
        tc.project_options["sock-diag"] = "disabled"
        tc.project_options["oidc-auth"] = "disabled"
        tc.project_options["compression"] = "disabled"
        tc.project_options["namespaces"] = "disabled"
        # Keep AnyConnect client compatibility (core feature, no extra deps)
        tc.project_options["anyconnect-compat"] = "enabled"
        # cc.find_library('ev'/'readline') does not read pkg-config files:
        # inject include/lib paths via cflags/ldflags so meson's
        # has_headers checks pass with conan-prefixed packages.
        for inc in self._dep_include_dirs():
            tc.extra_cflags.append(f"-I{inc}")
        for lib in self._dep_lib_dirs():
            tc.extra_ldflags.append(f"-L{lib}")
        # readline needs ncursesw symbols (tputs) at link time.
        tc.extra_ldflags.append("-lncursesw")
        tc.generate()
        self._inject_meson_archiver()
        # MesonToolchain sets pkg_config_path (and the conanbuild env
        # PKG_CONFIG_PATH) to the generators folder. Copy the dependency
        # .pc files there, rewriting prefix= to the package folder so
        # -I/-L flags resolve correctly (conan nettle ships prefix=/).
        pkg_dirs = self._dep_pkgconfig_dirs()
        for pc_dir in pkg_dirs:
            for f in os.listdir(pc_dir):
                if not f.endswith(".pc"):
                    continue
                src_pc = os.path.join(pc_dir, f)
                dst_pc = os.path.join(self.generators_folder, f)
                # derive the owning package folder from the pc dir:
                # …/<hash>/p/lib/pkgconfig or …/<hash>/p/lib → …/<hash>/p
                owner = pc_dir
                for _ in range(3):
                    if os.path.basename(owner) == "p":
                        break
                    owner = os.path.dirname(owner)
                if os.path.basename(owner) != "p":
                    owner = os.path.dirname(pc_dir)
                with open(src_pc, encoding="utf-8") as h:
                    lines = h.readlines()
                out = []
                for line in lines:
                    stripped = line.strip()
                    # Rewrite prefix= only when it is the conan-relative
                    # "/" (would resolve to -I//include); keep absolute
                    # prefixes pointing at the right cache folder, and
                    # rewrite absolute prefixes pointing elsewhere (e.g.
                    # /storage/.../usr/local) to the cache folder.
                    if stripped == "prefix=/":
                        out.append(f"prefix={owner}\n")
                    elif stripped.startswith("prefix=") and not \
                            stripped.startswith("prefix=" + owner):
                        out.append(f"prefix={owner}\n")
                    else:
                        out.append(line)
                with open(dst_pc, "w", encoding="utf-8") as h:
                    h.writelines(out)
        self._pkg_dirs = pkg_dirs

    def _inject_meson_archiver(self):
        """Ensure the cross/native file carries ar/ranlib; OHOS toolchain
        wrappers do not provide plain `ar` on PATH for meson to probe."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        cross_file = os.path.join(
            self.generators_folder, "conan_meson_cross.ini"
        )
        for nf in (native_file, cross_file):
            if not ar or not os.path.isfile(nf):
                continue
            with open(nf, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" in content or "[binaries]" not in content:
                continue
            binaries = "[binaries]\nar = '%s'\n" % ar
            if ranlib:
                binaries += "ranlib = '%s'\n" % ranlib
            with open(nf, "w", encoding="utf-8") as handle:
                handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        apply_conandata_patches(self)
        extra = {}
        pkg_dirs = getattr(self, "_pkg_dirs", None) or []
        if pkg_dirs:
            extra["PKG_CONFIG_PATH"] = ":".join(pkg_dirs)
        env = self._meson_env(extra)
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        py, margs = self._meson_cmd(
            ["setup", sdir, bdir, "--prefix=/", "--native-file", nf]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=env)
        ninja = os.environ.get("HMBS_NINJA") or "ninja"
        self.run(f'"{ninja}" -C "{bdir}" -j2', env=env)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream C unit tests (meson test).

        Full upstream suite includes ~100 shell script tests that require
        root/namespaces/cwrap/openconnect client — not runnable in the
        conan sandbox. The C unit tests exercise string handling, config
        parsing, protobuf message formatting, HTTP escaping and CSTP
        framing, which are the platform-relevant parts.
        """
        c_unit_tests = [
            "str-test", "str-test2", "json-escape", "ban-ips",
            "port-parsing", "human_addr", "valid-hostname", "url-escape",
            "html-escape", "ipv4-prefix", "ipv6-prefix", "proxyproto-v1",
            "proxyproto-v2", "cstp-recv", "config-inherit",
        ]
        env = self._meson_env()
        # /tmp is read-only on OHOS (E002): config-inherit honours TMPDIR.
        # Test binaries link libgnutls.so → libtasn1/libgcrypt/...:
        # collect LD_LIBRARY_PATH across ALL direct+transitive deps.
        # NOTE: Conan 2 self.run(env=[...]) does NOT propagate vars to the
        # child process on this platform (astroterm/1.0.9 evidence), so the
        # vars are injected at process level via os.environ instead.
        lib_dirs = []
        seen = set()
        stack = list(self.dependencies.values())
        while stack:
            dep = stack.pop(0)
            key = str(dep.ref)
            if key in seen:
                continue
            seen.add(key)
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                lib_dirs.append(lib_dir)
            try:
                stack.extend(dep.dependencies.values())
            except Exception:
                pass
        os.environ["TMPDIR"] = self.build_folder
        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            combined = ":".join(lib_dirs)
            os.environ["LD_LIBRARY_PATH"] = (
                combined + ":" + existing if existing else combined
            )
        self.output.info(
            "test LD_LIBRARY_PATH: %s" % os.environ.get("LD_LIBRARY_PATH")
        )
        ok = skip = fail = 0
        failed = []
        for t in c_unit_tests:
            exe = os.path.join(self.build_folder, "tests", t)
            if not os.path.isfile(exe):
                failed.append(f"{t}(missing)")
                continue
            ret = self.run(
                f'"{exe}"', env=env, ignore_errors=True
            )
            if ret == 0:
                ok += 1
            elif ret == 77:
                skip += 1
            else:
                fail += 1
                failed.append(f"{t}(rc={ret})")
        summary = (
            f"upstream C unit tests: Ok={ok} Skip={skip} Fail={fail}"
            + (f" failed={failed}" if failed else "")
        )
        self.output.info("=== " + summary + " ===")
        if fail:
            raise ConanInvalidConfiguration(summary)

    def package(self):
        pkg = self.package_folder
        bdir = self.build_folder
        copy(self, "ocserv", src=os.path.join(bdir, "src"),
             dst=os.path.join(pkg, "bin"))
        copy(self, "ocserv-worker", src=os.path.join(bdir, "src"),
             dst=os.path.join(pkg, "bin"))
        copy(self, "occtl", src=os.path.join(bdir, "src", "occtl"),
             dst=os.path.join(pkg, "bin"))
        copy(self, "ocpasswd", src=os.path.join(bdir, "src", "ocpasswd"),
             dst=os.path.join(pkg, "bin"))
        # firewall helper script (nftables backend)
        copy(self, "ocserv-fw", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(pkg, "libexec"))
        # sample config
        copy(self, "sample.config", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(pkg, "share", "doc", "ocserv"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
