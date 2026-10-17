#!/usr/bin/env python3
"""Conan recipe for rtorrent 0.16.2 on HarmonyOS."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    replace_in_file,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class RtorrentConan(ConanFile):
    name = "rtorrent"
    version = "0.16.2"
    description = "rTorrent BitTorrent client"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rakshasa/rtorrent"
    url = "https://github.com/rakshasa/rtorrent"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.compiler.cppstd = "17"

        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rtorrent supports Linux and OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("libtorrent/0.16.17", transitive_headers=True, transitive_libs=True)
        self.requires("ncurses/6.5")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")
        self.test_requires("cppunit/1.15.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if self.settings.build_type == "Debug":
            tc.configure_args.append("--enable-debug")
        else:
            tc.configure_args.append("--disable-debug")

        tc.configure_args.append("--disable-extra-debug")

        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
            tc.configure_args.append("--disable-execinfo")
            # libtorrent 0.16.17 uses LT_SMP_CACHE_BYTES in align_cacheline but doesn't define it;
            # the pre-built package's config.h is not shipped, so provide it here.
            tc.extra_cxxflags.append("-DLT_SMP_CACHE_BYTES=64")
        self._generate_compat_headers()
        tc.generate()
        if self.settings.os == "OHOS":
            self._generate_autoreconf_environment()
            self._write_configure_compiler_wrapper()

    def _generate_compat_headers(self):
        """Generate compatibility headers for libtorrent 0.16.17 API changes.

        libtorrent 0.16.17 moved/replaced several headers and APIs that
        rtorrent 0.16.2 expects. These shim headers provide the old paths
        and namespaces on top of the new API.
        """
        import textwrap
        # Write to the build folder root (parent of generators folder)
        # so they are found via '-I.' in the autotools include path.
        base_dir = os.path.dirname(self.generators_folder) or self.generators_folder
        base = os.path.join(base_dir, "torrent")
        net_dir = os.path.join(base, "net")
        os.makedirs(net_dir, exist_ok=True)

        headers = {
            os.path.join(base, "compat.h"): textwrap.dedent("""\
                #ifndef RTORRENT_LIBTORRENT_COMPAT_H
                #define RTORRENT_LIBTORRENT_COMPAT_H
                #include <torrent/runtime/socket_manager.h>
                #include <torrent/runtime/runtime.h>
                #include <torrent/runtime/network_manager.h>
                #include <torrent/throttle.h>
                #include <torrent/hash_string.h>
                #include <torrent/utils/option_strings.h>
                #include <torrent/utils/string_manip.h>
                #include <torrent/common.h>
                #include <torrent/system/thread.h>
                #include <torrent/system/callbacks.h>
                #include <functional>
                #include <list>
                #include <string>
                #include <utility>
                namespace torrent {
                using runtime::total_handshakes;
                using runtime::version;
                using ThrottlePair = std::pair<Throttle*, Throttle*>;
                inline void set_main_thread_slots(std::function<void()> fn) {
                    main_thread::set_client_callback(std::move(fn));
                }
                inline std::string option_as_string(option_enum opt, unsigned int value) {
                    return option_to_str(opt, value);
                }
                inline const char* hash_string_from_hex_c_str(const char* hex, HashString& hash) {
                    utils::transform_from_hex(hex, hex + HashString::size() * 2, hash.begin(), hash.end());
                    return hex + HashString::size() * 2;
                }
                inline std::string hash_string_to_hex_str(const HashString& hash) {
                    std::string result(HashString::size() * 2, '\\0');
                    utils::transform_to_hex(hash.begin(), hash.end(), result.begin(), result.end());
                    return result;
                }
                inline std::list<std::string>* encoding_list() {
                    static std::list<std::string> instance;
                    return &instance;
                }
                inline tracker::DhtController* dht_controller() {
                    return runtime::network_manager()->dht_controller();
                }
                inline bool is_inactive() {
                    return main_thread::thread()->is_inactive();
                }
                class ConnectionManagerCompat {
                public:
                    uint32_t size()                       { return runtime::socket_manager()->size(); }
                    uint32_t max_size()                   { return runtime::socket_manager()->max_size(); }
                    void     set_max_size(uint32_t)         { /* no-op: socket_manager manages limits */ }
                    void     inc_socket_count()           { runtime::socket_manager()->add_unmanaged_socket(); }
                    void     dec_socket_count()           { runtime::socket_manager()->remove_unmanaged_socket(); }
                    std::function<void(void*)>& address_throttle() { static std::function<void(void*)> dummy; return dummy; }
                };
                inline ConnectionManagerCompat* connection_manager() {
                    static ConnectionManagerCompat instance;
                    return &instance;
                }
                }
                #endif
                """),
            os.path.join(base, "poll.h"): textwrap.dedent("""\
                #ifndef RTORRENT_COMPAT_POLL_H
                #define RTORRENT_COMPAT_POLL_H
                #include <torrent/system/poll.h>
                namespace torrent { using Poll = system::Poll; }
                #endif
                """),
            os.path.join(base, "error.h"): textwrap.dedent("""\
                #ifndef RTORRENT_COMPAT_ERROR_H
                #define RTORRENT_COMPAT_ERROR_H
                #include <torrent/exceptions.h>
                #endif
                """),
            os.path.join(base, "connection_manager.h"): textwrap.dedent("""\
                #ifndef RTORRENT_COMPAT_CONNECTION_MANAGER_H
                #define RTORRENT_COMPAT_CONNECTION_MANAGER_H
                #include "compat.h"
                #endif
                """),
            os.path.join(net_dir, "network_config.h"): textwrap.dedent("""\
                #ifndef RTORRENT_COMPAT_NET_NETWORK_CONFIG_H
                #define RTORRENT_COMPAT_NET_NETWORK_CONFIG_H
                #include <torrent/runtime/network_config.h>
                #include <torrent/runtime/runtime.h>
                namespace torrent::config {
                    using torrent::runtime::network_config;
                    using torrent::runtime::NetworkConfig;
                }
                namespace torrent { using runtime::total_handshakes; }
                #endif
                """),
            os.path.join(net_dir, "network_manager.h"): textwrap.dedent("""\
                #ifndef RTORRENT_COMPAT_NET_NETWORK_MANAGER_H
                #define RTORRENT_COMPAT_NET_NETWORK_MANAGER_H
                #include <torrent/runtime/network_manager.h>
                #include "network_config.h"
                namespace torrent::net {
                    using torrent::runtime::network_manager;
                    using torrent::runtime::NetworkManager;
                    using torrent::config::NetworkConfig;
                }
                #endif
                """),
        }
        for path, content in headers.items():
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)

    @property
    def _configure_compiler_wrapper_path(self):
        return os.path.join(
            self.generators_folder, "rtorrent-clang-conftest.sh"
        )

    @property
    def _configure_sign_events_path(self):
        return os.path.join(
            self.generators_folder, "rtorrent-conftest-sign-events.txt"
        )

    def _write_configure_compiler_wrapper(self):
        tools = {
            "awk": "/system/bin/awk",
            "chmod": "/system/bin/chmod",
            "readelf": "/data/service/hnp/bin/llvm-readelf",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS configure signing tools are missing: {}".format(missing)
            )

        runtime_libdirs = []
        for dependency in self.dependencies.values():
            runtime_libdirs.extend(
                dependency.cpp_info.aggregated_components().libdirs
            )
        runtime_rpath = ":".join(dict.fromkeys(runtime_libdirs))
        if not runtime_rpath:
            raise ConanInvalidConfiguration(
                "OHOS configure probes require dependency runtime directories"
            )

        os.makedirs(self.generators_folder, exist_ok=True)
        with open(self._configure_sign_events_path, "w", encoding="utf-8"):
            pass
        script = """#!/system/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  printf 'RTORRENT_CC_MISSING_COMPILER\\n' >&2
  exit 90
fi
real_compiler=$1
shift
readelf=@READELF@
signer=@SIGNER@
awk_tool=@AWK@
chmod_tool=@CHMOD@
runtime_rpath=@RUNTIME_RPATH@
events=@EVENTS@
probe_mode=${RTORRENT_CONFIGURE_PROBES:-0}

output=a.out
expect_output=0
compile_only=0
for argument in "$@"; do
  if [ "$expect_output" -eq 1 ]; then
    output="$argument"
    expect_output=0
    continue
  fi
  case "$argument" in
    -o) expect_output=1 ;;
    -o?*) output=${argument#-o} ;;
    -c|-E|-S) compile_only=1 ;;
  esac
done
if [ "$expect_output" -ne 0 ]; then
  printf 'RTORRENT_CC_MISSING_OUTPUT\\n' >&2
  exit 91
fi
case "$output" in
  /*) ;;
  *) output="$(pwd)/$output" ;;
esac
name=${output##*/}
is_conftest=0
case "$name" in
  conftest*) is_conftest=1 ;;
esac

if [ "$probe_mode" -eq 1 ] && [ "$is_conftest" -eq 1 ] && [ "$compile_only" -eq 0 ]; then
  "$real_compiler" "$@" "-Wl,-rpath,$runtime_rpath"
else
  "$real_compiler" "$@"
fi

if [ "$probe_mode" -ne 1 ] || [ "$is_conftest" -ne 1 ] || [ "$compile_only" -ne 0 ] || [ ! -f "$output" ]; then
  exit 0
fi
elf_type=$("$readelf" -h "$output" 2>/dev/null | "$awk_tool" '$1 == "Type:" {print $2; exit}')
case "$elf_type" in
  EXEC|DYN) ;;
  *) exit 0 ;;
esac
"$signer" sign -inFile "$output" -outFile "$output" -selfSign 1
"$chmod_tool" 755 "$output"
printf '%s\\n' "$output" >> "$events"
"""
        replacements = {
            "@READELF@": tools["readelf"],
            "@SIGNER@": tools["signer"],
            "@AWK@": tools["awk"],
            "@CHMOD@": tools["chmod"],
            "@RUNTIME_RPATH@": runtime_rpath,
            "@EVENTS@": self._configure_sign_events_path,
        }
        for marker, value in replacements.items():
            script = script.replace(marker, shlex.quote(value))
        with open(
            self._configure_compiler_wrapper_path,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(script)

    def _validate_configure_signing(self):
        if self.settings.os != "OHOS":
            return
        try:
            with open(self._configure_sign_events_path, encoding="utf-8") as handle:
                events = [line.strip() for line in handle if line.strip()]
        except OSError as error:
            raise ConanInvalidConfiguration(
                "configure conftest signing evidence is missing"
            ) from error
        if not any(os.path.basename(path).startswith("conftest") for path in events):
            raise ConanInvalidConfiguration(
                "configure produced no signed conftest executable"
            )

    def _generate_autoreconf_environment(self):
        automake_root = self.dependencies.build["automake"].package_folder
        libtool_root = self.dependencies.build["libtool"].package_folder
        if not automake_root or not libtool_root:
            raise ConanException("Autotools build-tool packages are unavailable")

        perl = shutil.which("perl") or "perl"
        shell = shutil.which("bash") or shutil.which("sh") or "sh"

        automake_bin = os.path.join(automake_root, "bin")
        automake_data = os.path.join(
            automake_root, "share", "automake-1.18"
        )
        aclocal_data = os.path.join(
            automake_root, "share", "aclocal"
        )
        aclocal_versioned = os.path.join(
            automake_root, "share", "aclocal-1.18"
        )
        libtoolize = os.path.join(libtool_root, "bin", "libtoolize")
        libtool_share = os.path.join(libtool_root, "share")
        libtool_sources = {
            "build-aux": os.path.join(libtool_share, "libtool", "build-aux"),
            "libltdl": os.path.join(libtool_share, "libtool", "libltdl"),
            "m4": os.path.join(libtool_share, "aclocal"),
        }
        libtool_data = os.path.join(self.generators_folder, "libtool-data")
        required = [
            os.path.join(automake_bin, ".aclocal-real"),
            os.path.join(automake_bin, ".automake-real"),
            automake_data,
            aclocal_data,
            aclocal_versioned,
            libtoolize,
            *libtool_sources.values(),
        ]
        missing = [path for path in required if not os.path.exists(path)]
        if missing:
            raise ConanException(
                "Autotools package content is missing: " + ", ".join(missing)
            )

        if os.path.isdir(libtool_data):
            shutil.rmtree(libtool_data)
        os.makedirs(libtool_data)
        for name, source in libtool_sources.items():
            shutil.copytree(
                source, os.path.join(libtool_data, name), symlinks=False
            )

        env = Environment()
        env.define(
            "ACLOCAL",
            shlex.join(
                [
                    perl,
                    os.path.join(automake_bin, ".aclocal-real"),
                    "--automake-acdir=" + aclocal_versioned,
                    "--system-acdir=" + aclocal_data,
                ]
            ),
        )
        env.define(
            "AUTOMAKE",
            shlex.join(
                [
                    perl,
                    os.path.join(automake_bin, ".automake-real"),
                    "--libdir=" + automake_data,
                ]
            ),
        )
        env.define("LIBTOOLIZE", shlex.join([shell, libtoolize]))
        env.prepend_path("PERL5LIB", automake_data)
        env.prepend_path("ACLOCAL_PATH", aclocal_versioned)
        env.prepend_path("ACLOCAL_PATH", aclocal_data)
        env.prepend_path(
            "ACLOCAL_PATH", os.path.join(libtool_root, "share", "aclocal")
        )
        env.define_path("_lt_pkgdatadir", libtool_data)
        env.vars(self).save_script("rtorrent_autoreconf")

    def build(self):
        apply_conandata_patches(self)
        # Fix lambda return types: change -> auto to -> torrent::Object
        # for proper std::function conversion in command_tracker.cc
        tracker_src = os.path.join(self.source_folder, "src", "command_tracker.cc")
        if os.path.isfile(tracker_src):
            replace_in_file(
                self, tracker_src,
                ") -> auto { return tracker->state()",
                ") -> torrent::Object { return tracker->state()",
            )
            # Fix chrono return types: add .count() for std::chrono::seconds
            # to int64_t conversion for torrent::Object compatibility
            for method in ["interval", "time_next", "time_last"]:
                replace_in_file(
                    self, tracker_src,
                    method + "(); });",
                    method + "().count(); });",
                )
        build_env = ["conanbuild"]
        if self.settings.os == "OHOS":
            build_env.append("rtorrent_autoreconf")
        self.run(
            "autoreconf --install --force --verbose",
            cwd=self.source_folder,
            env=build_env,
        )
        if self.settings.os == "OHOS":
            replace_in_file(
                self, os.path.join(self.source_folder, "configure"),
                "umask 077", "umask 022",
            )
            # Fix thread_worker.cc: callback(nullptr, ...) → callback(false, ...)
            # for libtorrent 0.16.17 Thread::callback API change
            worker_src = os.path.join(self.source_folder, "src", "thread_worker.cc")
            if os.path.isfile(worker_src):
                replace_in_file(
                    self, worker_src,
                    "callback(nullptr, ",
                    "callback(false, ",
                )

        autotools = Autotools(self)
        self._configure(autotools)
        self._validate_configure_signing()
        if self.settings.os == "OHOS":
            config_h = os.path.join(self.build_folder, "config.h")
            if os.path.isfile(config_h):
                replace_in_file(
                    self, config_h,
                    "#define PACKAGE ",
                    "#include <torrent/compat.h>\n#define PACKAGE ",
                )
        autotools.make(args=["-j1"])
        if can_run(self):
            test_args = ["-j1"]
            with self._test_environment().vars(self).apply():
                autotools.make(target="check", args=test_args)
        else:
            self.output.info("Cross-building: upstream CppUnit tests skipped")

    def _configure(self, autotools):
        if self.settings.os != "OHOS":
            autotools.configure()
            return

        configure_shell = shutil.which("bash") or shutil.which("sh") or "sh"
        wrapper_shell = "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(self._configure_compiler_wrapper_path):
            raise ConanInvalidConfiguration(
                "OHOS configure compiler wrapper was not generated"
            )
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        real_cc = (
            compiler_executables.get("c", "clang")
            if compiler_executables else "clang"
        )
        real_cxx = (
            compiler_executables.get("cpp", "clang++")
            if compiler_executables else "clang++"
        )
        configure_cc = shlex.join(
            [wrapper_shell, self._configure_compiler_wrapper_path, real_cc]
        )
        configure_cxx = shlex.join(
            [wrapper_shell, self._configure_compiler_wrapper_path, real_cxx]
        )
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        command = shlex.join([configure_shell, configure])
        if configure_args:
            command = "{} {}".format(command, configure_args)
        command = (
            "CONFIG_SHELL={} SHELL={} PWD={} "
            "RTORRENT_CONFIGURE_PROBES=1 CC={} CXX={} {}"
        ).format(
            shlex.quote(configure_shell),
            shlex.quote(configure_shell),
            shlex.quote(self.build_folder),
            shlex.quote(configure_cc),
            shlex.quote(configure_cxx),
            command,
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def _test_environment(self):
        env = Environment()
        if self.settings.os == "Windows":
            loader_path = "PATH"
        else:
            loader_path = "LD_LIBRARY_PATH"
        for dependency in self.dependencies.values():
            cpp_info = dependency.cpp_info.aggregated_components()
            for libdir in cpp_info.libdirs:
                env.prepend_path(loader_path, libdir)
        return env

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
