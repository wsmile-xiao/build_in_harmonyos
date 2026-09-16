#!/usr/bin/env python3
"""Conan recipe — wolfmqtt 1.19.0 (Autotools + libtool)

wolfMQTT is a portable MQTT 3.1.1/v5 client library in C from wolfSSL.
TLS support is enabled by upstream default (ENABLE_MQTT_TLS) and is wired
to the published wolfssl package. Upstream ships no configure script in
GitHub archives (configure.ac + autogen.sh only), so the recipe bootstraps
via autoreconf with automake/libtool tool_requires.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WolfmqttConan(ConanFile):
    name = "wolfmqtt"
    version = "1.19.0"
    description = "wolfMQTT 1.19.0 — MQTT 3.1.1/v5 client library in C with TLS via wolfSSL"
    license = "GPL-2.0-only"
    homepage = "https://github.com/wolfSSL/wolfMQTT"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # TLS is enabled by upstream default (ENABLE_MQTT_TLS) and hard-requires
        # libwolfssl (AC_CHECK_LIB in configure.ac).
        self.requires("wolfssl/5.7.0")

    def build_requirements(self):
        # GitHub archive 不含 configure（只是 git tree 快照），须 autoreconf 自举；
        # LT_INIT 需要 libtoolize；CI 设备缺 automake/libtool，经 build profile 解析。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # examples are network demo programs, not part of the library deliverable
        tc.configure_args.append("--disable-examples")
        # configure requires <prefix>/lib + <prefix>/include and adds -L/-I itself
        wolfssl = self.dependencies["wolfssl"]
        tc.configure_args.append(f"--with-libwolfssl-prefix={wolfssl.package_folder}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)

        # Source tarball (GitHub archive) lacks pre-built configure;
        # generate from configure.ac via autoreconf.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("Source tree has no configure (GitHub archive), running autoreconf")
            autotools.autoreconf()

        # E007: Replace config.guess/config.sub with OHOS-aware versions
        # autoreconf installs config.guess from automake/1.18 (2024-07-27),
        # which doesn't recognize HarmonyOS and fails to guess build type.
        self._replace_config_for_ohos()

        # E490: HMDFS adaptation paths may lose exec bits on autotools helper
        # scripts; restore them before configure (knowledge: restore-known-
        # autotools-script-modes).
        for _sub in ("build-aux", ""):
            for _script in ("configure", "config.guess", "config.sub",
                            "install-sh", "missing", "compile", "depcomp",
                            "ltmain.sh"):
                _path = os.path.join(self.source_folder, _sub, _script)
                if os.path.exists(_path):
                    os.chmod(_path, 0o755)

        # HMDFS getcwd 修复（adms/2.3.7 同款组合）：conan 建树后父目录对
        # getcwd() 不可达，autoconf 严格 pwd 判定报 "working directory cannot
        # be determined"。shell pwd 内建走逻辑路径，故预置 PWD；再给生成的
        # configure 的 ac_pwd 判定加 $PWD 回退；临时目录 umask 077→022
        # （E011：HMDFS setgid 目录 077 连属主都不可写）。
        os.environ["PWD"] = self.build_folder
        _configure = os.path.join(self.source_folder, "configure")
        with open(_configure) as f:
            _cfg = f.read()
        _cfg = _cfg.replace(
            "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n \"$ac_pwd\" &&",
        )
        _cfg = _cfg.replace("umask 077", "umask 022")
        with open(_configure, "w") as f:
            f.write(_cfg)

        autotools.configure()
        autotools.make(args=["-j1"])

    def _replace_config_for_ohos(self):
        """Replace config.guess/config.sub with OHOS-aware versions (E007).

        automake/1.18 installs the aux scripts into build-aux/ (its default
        AC_CONFIG_AUX_DIR when configure.ac does not set one); fall back to
        the source root for layouts that keep them there. The stock
        config.guess cannot guess HarmonyOS and additionally fails on this
        platform while compiling its probe dummy (HMDFS permission).
        """
        for _sub in ("build-aux", ""):
            _dir = os.path.join(self.source_folder, _sub)
            _guess = os.path.join(_dir, "config.guess")
            _sub_path = os.path.join(_dir, "config.sub")
            if not os.path.isfile(_guess) and not os.path.isfile(_sub_path):
                continue

            ohos_config_guess = (
                '#!/bin/sh\n'
                '# OHOS-aware config.guess (self-contained)\n'
                'machine=$(uname -m 2>/dev/null || echo unknown)\n'
                'system=$(uname -s 2>/dev/null || echo unknown)\n'
                'case "$system" in\n'
                '    HarmonyOS|OHOS)\n'
                '        echo "${machine}-unknown-linux-ohos"\n'
                '        ;;\n'
                '    *)\n'
                '        echo "${machine}-unknown-linux-gnu"\n'
                '        ;;\n'
                'esac\n'
                'exit 0\n'
            )
            with open(_guess, "w") as f:
                f.write(ohos_config_guess)
            os.chmod(_guess, 0o755)

            ohos_config_sub = (
                '#!/bin/sh\n'
                '# OHOS-aware config.sub (self-contained)\n'
                '# Always pass through the input triplet\n'
                'if [ $# -eq 0 ] || [ -z "$1" ]; then\n'
                '    echo "aarch64-unknown-linux-ohos"\n'
                '    exit 0\n'
                'fi\n'
                'echo "$1"\n'
                'exit 0\n'
            )
            with open(_sub_path, "w") as f:
                f.write(ohos_config_sub)
            os.chmod(_sub_path, 0o755)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["wolfmqtt"]
        # TLS is enabled in this build (upstream default). Consumers must get
        # the same macro so public headers expose the same struct layout/ABI.
        self.cpp_info.defines = ["ENABLE_MQTT_TLS"]
        # Public headers (mqtt_types.h) include <wolfssl/options.h> — declare
        # the usage dependency so tooling knows consumers need wolfssl too.
        self.cpp_info.requires = ["wolfssl::wolfssl"]
