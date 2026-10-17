#!/usr/bin/env python3
"""Conan recipe — libdbusmenu-gtk3 16.04.0 (Autotools).

libdbusmenu 16.04.0 builds two libraries:
  - libdbusmenu-glib (dbusmenu-glib-0.4.pc): pure GLib/GDBus menu model
  - libdbusmenu-gtk3 (dbusmenu-gtk3-0.4.pc): GTK3 bindings (parser, menu proxy)

OHOS 适配要点：
  - 构建系统: autotools 官方 tarball（configure 已生成）
  - 16.04.0 已迁移到 GDBus (gio)，不依赖 dbus-glib；dbus 参考实现仅在测试期
    通过 dbus-run-session（archives/d/dbus tool 包 bin/）提供会话总线，
    不进入配方依赖图（dbus 绑 glib/2.88.3，与 gtk3 生态 glib/2.84.0.1 冲突）
  - --disable-dumper：dumper 工具依赖 gtk2+x11，OHOS 均不可用
  - intltool/perl 检查降级为告警（补丁 0003），NLS 不构建
  - configure 的 DBUSMENUTESTS 探针要求 gio-unix-2.0 >= 2.24；glib 包与 conan
    合成 pc 集均无 gio-unix-2.0.pc，build() 生成 Requires: gio-2.0 的聚合 shim
    并前置 PKG_CONFIG_PATH（不引入桩头文件/桩库）
  - 上游测试跑在 dbus-test-runner（Launchpad 生态工具，未鸿蒙化）之下：
    build() 生成 dbus-test-runner shim，把 `--task gtester --parameter ...`
    形式翻译为 `dbus-run-session -- gtester ...` 后运行 glib 系测试；
    gtk 系测试需要 X display（OHOS 无 X server，gtk3 为 broadway 后端），
    属平台差异，报告见 notes.md（路径 B）
  - OHOS 下对 .so 签名
"""
import glob
import os
import shlex
import shutil
import stat
from textwrap import dedent

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibdbusmenuGtk3Conan(ConanFile):
    name = "libdbusmenu-gtk3"
    version = "16.04.0"
    description = "D-Bus menu specification — GLib menu model and GTK3 bindings (small library for exporting menus over D-Bus)"
    license = "LGPL-2.1-or-later OR LGPL-3.0-or-later"
    homepage = "https://launchpad.net/libdbusmenu"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdbusmenu-gtk3 only supports Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # 与 gtk3 生态对齐（gtk/3.24.43 及 json-glib/1.10.6 均 pin glib/2.84.0.1，
        # 顶层声明同一版本避免 R36 冲突；dbus/1.14.10.2 绑 glib/2.88.3，故不入图）
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        # json-glib 仅上游 tests/ 构建需要（dbusmenu-jsonloader）
        self.requires("json-glib/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def _configure_args(self):
        return [
            "--with-gtk=3",
            "--disable-dumper",          # dumper 需要 gtk2 + x11
            "--disable-gtk-doc",
            "--disable-introspection",  # g-ir-scanner 不在 OHOS 工具链
            "--disable-vala",  # vala default=auto errors with disabled introspection
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ]

    def build(self):
        self._ensure_tmpdir()
        self._stage_glib_build_tools()
        self._stage_intltool_stubs()
        self._stage_gio_unix_pc_shim()
        autotools = Autotools(self)
        # AC_PATH_PROG scans PATH and /data/service/hnp/bin (prepended by
        # conanbuildenv after generate()) hosts a perl-shebang glib-mkenums whose
        # interpreter /usr/bin/perl does not exist. Force the cache var to the
        # staged python-shebang wrapper.
        os.environ["GLIB_MKENUMS"] = os.path.join(self.build_folder, "conan-native-tools", "glib-mkenums")
        configure_cmd = [
            "sh",
            os.path.join(self.source_folder, "configure"),
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ] + self._configure_args()
        self.run(" ".join(shlex.quote(arg) for arg in configure_cmd))
        autotools.make(args=["-j1"])
        if cross_building(self):
            self.output.info("cross-building: skip upstream tests (target binaries not runnable on build host)")
        else:
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the D-Bus-session-dependent glib test subset.

        Upstream drives every test through `dbus-test-runner` (Launchpad
        toolchain, not ported).  We write a shim that translates the
        `--task gtester --parameter ...` invocation into
        `dbus-run-session -- gtester ...`, so each test still runs under a
        real session bus (provided by the dbus tool package's dbus-daemon on
        the target).  The gtk tests additionally need an X display
        (run-xvfb.sh) and stay unexecuted on OHOS — platform difference,
        documented in notes.md.
        """
        if not shutil.which("dbus-run-session"):
            self.output.warning(
                "dbus-run-session not found in PATH; upstream glib tests NOT run. "
                "Install the dbus/1.14.10.x tool package and expose its bin/ "
                "(e.g. conan install dbus/1.14.10.2 --requires, then activate "
                "VirtualRunEnv) before building to enable the session-bus tests."
            )
            return
        conf = self._write_session_conf()
        self._dbus_session_conf = conf
        shim_dir = os.path.join(self.build_folder, ".dbus-test-runner-shim")
        os.makedirs(shim_dir, exist_ok=True)
        save(self, os.path.join(shim_dir, "dbus-test-runner"),
             self._shim_script() % {"conf": self._dbus_session_conf,
                                    "helper": os.path.join(shim_dir, "run-tasks.sh")})
        save(self, os.path.join(shim_dir, "run-tasks.sh"), self._run_tasks_helper())
        shim = os.path.join(shim_dir, "dbus-test-runner")
        os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        path_parts = [shim_dir] + [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        os.environ["PATH"] = os.pathsep.join(path_parts)
        self._extend_library_path_for_tests()
        glib_tests = [
            "test-glib-objects-test",
            "test-glib-events",
            "test-glib-events-nogroup",
            "test-glib-layout",
            "test-glib-properties",
            "test-glib-proxy",
            "test-glib-simple-items",
            "test-glib-submenu",
        ]
        self.output.info("Running glib test subset under dbus-run-session: %s" % " ".join(glib_tests))
        # os.environ tweaks in build() do not survive into conan's conanbuild.sh-based
        # subprocess env; Autotools.make() has no env arg in conan 2.29.1, so run make
        # through self.run() with an explicit LD_LIBRARY_PATH prefix.
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        make_cmd = 'make check -j1 TESTS="%s"' % " ".join(glib_tests)
        if ld:
            make_cmd = "LD_LIBRARY_PATH=%s %s" % (shlex.quote(ld), make_cmd)
        self.run(make_cmd)

    def _shim_script(self):
        return """#!/bin/sh
# dbus-test-runner shim for OHOS.
# Translates the task forms used by libdbusmenu's generated test wrappers:
#   single-task (gtester form):
#     dbus-test-runner --task gtester --task-name test --parameter ... ./prog
#   multi-task (client/server form, possibly repeated):
#     dbus-test-runner --max-wait=0 --task ./prog1 --task-name N1 [--ignore-return]
#                      [--task ./prog2 --task-name N2 ...]
# Tasks are separated with a literal newline into $DBUS_TR_TASKS; the helper
# script written by the recipe (run-tasks.sh) starts them in parallel and
# waits, mirroring dbus-test-runner's exit-code semantics. Arguments are
# assumed to contain no whitespace or newlines (paths here never do).
tasks=
noret=0
expect=
sep=
for a in "$@"; do
    if [ -n "$expect" ]; then
        case "$expect" in
            task) tasks="$tasks$sep$a"; sep=$'\n' ;;
            taskname) ;;
            param) tasks="$tasks $a" ;;
        esac
        expect=
        continue
    fi
    case "$a" in
        --task) expect=task ;;
        --task-name) expect=taskname ;;
        --parameter) expect=param ;;
        --ignore-return) noret=1 ;;
        --*) ;;
    esac
done
DBUS_TR_TASKS="$tasks" DBUS_TR_NORET="$noret" exec dbus-run-session --config-file=%(conf)s -- sh %(helper)s
"""

    def _run_tasks_helper(self):
        return """#!/bin/sh
# Parallel task runner used by the dbus-test-runner shim (see _shim_script).
# dbus-test-runner semantics: with --ignore-return the run succeeds once every
# task has exited (individual exit codes ignored); without it, any nonzero
# task exit fails the run.
rc=0
old=$IFS
IFS=$'\n'
for t in $DBUS_TR_TASKS; do
    IFS=$old
    sh -c "exec $t" &
done
IFS=$old
if [ "$DBUS_TR_NORET" = 1 ]; then
    wait
    exit 0
fi
for p in $(jobs -p); do
    wait $p || rc=1
done
exit $rc
"""

    def package(self):
        self._ensure_tmpdir()
        Autotools(self).install()
        if self.options.shared:
            self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["dbusmenu-glib", "dbusmenu-gtk3"]
        # 上游安装布局: include/libdbusmenu-glib-0.4/ 与
        # include/libdbusmenu-gtk3-0.4/（libdbusmenu-gtk/Makefile.am: VER=3）
        self.cpp_info.includedirs = [
            "include/libdbusmenu-glib-0.4",
            "include/libdbusmenu-gtk3-0.4",
            "include",
        ]
        # MIRROR-ONLY FIX: gtk/3.24.43 and json-glib/1.10.6 declare no components in
        # this artifact repo (global package model). conan's dep::comp syntax requires
        # the "dep" part to name a direct requirement; for a global-model dependency
        # the conventional reference is <pkg>::<pkg> (component names are not
        # validated for external deps by conan 2.29 CMakeDeps).
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gio-2.0",
                                  "gtk::gtk", "json-glib::json-glib"]
        self.cpp_info.set_property("cmake_file_name", "libdbusmenu-gtk3")
        self.cpp_info.set_property("cmake_target_name", "libdbusmenu-gtk3::libdbusmenu-gtk3")
        self.cpp_info.set_property("pkg_config_name", "dbusmenu-gtk3-0.4")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _stage_glib_build_tools(self):
        """Expose glib-mkenums from the host glib package (gtk/gdk-pixbuf pattern).

        configure 通过 AC_PATH_PROG([GLIB_MKENUMS]) 在 PATH 中查找该工具，
        用于生成 libdbusmenu-glib/enum-types.[ch]。glib 包 bin/ 中的脚本是
        python 脚本，wrapper 以绝对路径调起解释器，规避 worker 间差异。
        """
        import sys
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        src = os.path.join(glib_bin, "glib-mkenums")
        if not os.path.isfile(src):
            raise FileNotFoundError(f"GLib build tool missing: {src}")
        tools_folder = os.path.join(self.build_folder, "conan-native-tools")
        os.makedirs(tools_folder, exist_ok=True)
        wrapper = os.path.join(tools_folder, "glib-mkenums")
        python = os.path.realpath(sys.executable)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\nexec {} {} \"$@\"\n".format(q(python), q(src)))
        os.chmod(wrapper, 0o755)
        path_parts = [tools_folder] + [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        os.environ["PATH"] = os.pathsep.join(path_parts)
        self.output.info(f"staged glib-mkenums wrapper -> {wrapper}")

    def _write_session_conf(self):
        """Anonymous-TCP session bus config for dbus-run-session on OHOS."""
        conf = self._dbus_session_conf
        if not os.path.isfile(conf):
            save(self, conf, dedent("""\
                <!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
                 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
                <busconfig>
                  <type>session</type>
                  <keep_umask/>
                  <listen>tcp:host=127.0.0.1,port=0</listen>
                  <auth>ANONYMOUS</auth>
                  <allow_anonymous/>
                  <policy context="default">
                    <allow send_destination="*" eavesdrop="true"/>
                    <allow eavesdrop="true"/>
                    <allow own="*"/>
                  </policy>
                  <limit name="max_incoming_bytes">1000000000</limit>
                  <limit name="max_outgoing_bytes">1000000000</limit>
                  <limit name="max_message_size">1000000000</limit>
                  <limit name="service_start_timeout">120000</limit>
                  <limit name="auth_timeout">240000</limit>
                  <limit name="max_completed_connections">100000</limit>
                  <limit name="max_incomplete_connections">10000</limit>
                  <limit name="max_connections_per_user">100000</limit>
                  <limit name="max_pending_service_starts">10000</limit>
                  <limit name="max_names_per_connection">50000</limit>
                  <limit name="max_match_rules_per_connection">50000</limit>
                  <limit name="max_replies_per_connection">50000</limit>
                </busconfig>
                """))
        return conf

    def _stage_intltool_stubs(self):
        """Stage gettext/intltool probe stubs (env-level, OHOS).

        configure (as shipped) hard-errors when intltool-update / intltool-merge /
        intltool-extract are absent. intltool is not published for OHOS and NLS is
        out of scope (patch 0003 already keeps po/ out of the build), so stage
        no-op stubs on PATH to satisfy the probes. mktemp is wrapped because of an
        hmfs quirk: a mode-700 dir inheriting setgid comes out unwritable and
        breaks config.status.
        """
        stub_dir = os.path.join(self.build_folder, "conan-native-tools")
        os.makedirs(stub_dir, exist_ok=True)

        def _stub(name, body):
            p = os.path.join(stub_dir, name)
            if not os.path.exists(p):
                save(self, p, body)
                os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        probe = "#!/system/bin/sh\n# stub (env-level): NLS tooling not available on OHOS; probes only\nexit 0\n"
        for name in ("intltool-update", "intltool-merge", "intltool-extract"):
            _stub(name, probe)
        for name in ("msgfmt", "xgettext", "msgmerge"):
            _stub(name, '#!/system/bin/sh\necho "stub-%s (GNU stub) 0.21"\nexit 0\n' % name)

        _stub("mktemp", """#!/system/bin/sh
# mktemp wrapper (env-level, OHOS hmfs quirk):
# config.status runs `umask 077 && mktemp -d ./confXXXXXX`; on hmfs a mode-700
# dir inheriting setgid comes out as drwx--S--- which denies writes even to
# its owner, breaking config.status awk subst files. Rebuild the dir world-
# writable instead (mktemp uniqueness is preserved by reusing the same name).
real=/usr/bin/mktemp
out=$("$real" "$@")
rc=$?
if [ $rc -eq 0 ] && [ -d "$out" ]; then
    if ! echo test-write-$$ > "$out/.wtest" 2>/dev/null; then
        rm -f "$out/.wtest" 2>/dev/null
        rmdir "$out" 2>/dev/null && mkdir -m 0777 "$out" || true
    else
        rm -f "$out/.wtest" 2>/dev/null
    fi
fi
printf '%s\n' "$out"
exit $rc
""")

        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        if stub_dir not in path_parts:
            os.environ["PATH"] = os.pathsep.join([stub_dir] + path_parts)

    def _stage_gio_unix_pc_shim(self):
        """Aggregate gio-unix-2.0.pc shim for the configure DBUSMENUTESTS probe.

        configure hard-errors unless `gio-unix-2.0 >= 2.24` resolves (tests
        build). Neither the glib package nor conan's synthesized pkg-config
        set ships gio-unix-2.0.pc (only glib-2.0/gio-2.0/gobject-2.0), so
        stage an aggregating shim that Requires: gio-2.0 — pkg-config
        resolves Cflags/Libs through the real module, and the unix-specific
        gio headers ship in the same glib include tree, so no stub headers or
        stub libraries are introduced.
        """
        shim_dir = os.path.join(self.build_folder, "conan-native-tools")
        os.makedirs(shim_dir, exist_ok=True)
        pc = os.path.join(shim_dir, "gio-unix-2.0.pc")
        if not os.path.exists(pc):
            glib_version = self.dependencies["glib"].ref.version
            save(self, pc, dedent("""\
                prefix={}
                Name: gio-unix-2.0
                Description: gio unix-specific headers (OHOS aggregate shim; resolves via gio-2.0)
                Version: {}
                Requires: gio-2.0
                Libs:
                Cflags:
                """).format(self.dependencies["glib"].package_folder, glib_version))
        path_parts = [p for p in os.environ.get("PKG_CONFIG_PATH", "").split(os.pathsep) if p]
        if shim_dir not in path_parts:
            os.environ["PKG_CONFIG_PATH"] = os.pathsep.join([shim_dir] + path_parts)
        self.output.info("staged gio-unix-2.0.pc aggregate shim -> %s" % pc)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        # MIRROR-ONLY FIX (env bypass): OHOS lacks a password database, so
        # dbus-run-session's default EXTERNAL-auth session config cannot start a
        # bus. The shim points dbus-run-session at an anonymous-TCP config written
        # next to the build tree instead (generated in build()).
        self._dbus_session_conf = os.path.join(tmpdir, "dbus-session.conf")
        self._ensure_tool_paths()

    def _ensure_tool_paths(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c") or ""
        bindirs = []
        if cc and os.path.sep in cc:
            bindirs.append(os.path.dirname(cc))
        bindirs.extend([
            "/data/service/hnp/bin",
            "/data/service/hnp/make.org/make_4.4.1/bin",
            "/data/service/hnp/binutils.org/binutils_2.45/bin",
        ])
        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        for bindir in reversed([p for p in bindirs if p and os.path.isdir(p)]):
            if bindir not in path_parts:
                path_parts.insert(0, bindir)
        os.environ["PATH"] = os.pathsep.join(path_parts)

        def first_tool(*names):
            for bindir in bindirs:
                for name in names:
                    candidate = os.path.join(bindir, name)
                    if os.path.isfile(candidate):
                        return candidate
            return ""

        make = first_tool("make", "gmake")
        ar = compiler_executables.get("ar") or first_tool("llvm-ar", "ar")
        ranlib = compiler_executables.get("ranlib") or first_tool("llvm-ranlib", "ranlib")
        if make:
            os.environ["MAKE"] = make
        if ar:
            os.environ["AR"] = ar
        if ranlib:
            os.environ["RANLIB"] = ranlib

    def _extend_library_path_for_tests(self):
        libdirs = [
            os.path.join(self.build_folder, "libdbusmenu-glib", ".libs"),
            os.path.join(self.build_folder, "libdbusmenu-gtk", ".libs"),
        ]
        for dep in self.dependencies.host.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for subdir in ("lib", "lib64"):
                candidate = os.path.join(str(package_folder), subdir)
                if os.path.isdir(candidate):
                    libdirs.append(candidate)
        # dbus is a tool-package used from PATH, not a graph dependency, so its own
        # lib/ and the transitive expat lib/ are not covered above.
        dbus_bin = shutil.which("dbus-run-session")
        if dbus_bin:
            libdirs.append(os.path.join(os.path.dirname(os.path.dirname(dbus_bin)), "lib"))
        current = [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs + current)

        # MIRROR-ONLY FIX (env bypass): json-glib/1.10.6 ships unsigned .so in the
        # artifact repo and the OHOS kernel rejects unsigned shared objects with EACCES
        # at load time. Signing the cache copy in place does not survive across conan
        # runs (the cache restores package folders), so copy the real files into the
        # build tree, strip any stale .codesign section, self-sign them, and put that
        # directory FIRST on the test library path.
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if os.path.isfile(signer):
            import subprocess
            objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
            signed_dir = os.path.join(self.build_folder, "test-libs-signed")
            os.makedirs(signed_dir, exist_ok=True)
            for d in list(libdirs):
                for so in glob.glob(os.path.join(d, "*.so*")):
                    if os.path.islink(so) or not os.path.isfile(so):
                        continue
                    dst = os.path.join(signed_dir, os.path.basename(so))
                    if os.path.islink(dst) or os.path.exists(dst):
                        os.remove(dst)
                    shutil.copy2(so, dst)
                    if objcopy and os.path.isfile(objcopy):
                        subprocess.run([objcopy, "--remove-section", ".codesign", dst],
                                       capture_output=True)
                    if subprocess.run([signer, "sign", "-inFile", dst, "-outFile", dst,
                                       "-selfSign", "1"], capture_output=True).returncode != 0:
                        self.output.warning("failed to self-sign %s" % dst)
            libdirs.insert(0, signed_dir)


    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        for so in sos:
            if objcopy and os.path.isfile(objcopy):
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))
