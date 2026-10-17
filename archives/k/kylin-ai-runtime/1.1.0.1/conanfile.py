#!/usr/bin/env python3
"""Conan recipe — kylin-ai-runtime 1.1.0.1 (application, CMake).

Kylin AI 运行时主守护进程（openKylin 麒麟 AI 子系统，gitee openkylin/
kylin-ai-runtime tag build/1.1.0.1-ok0.9，commit 172314c2）：gdbus 服务进程
（corespeech/config/assistant/gennlp/genaivision/coretextembedding/
coreimageembedding/corevision 8 个服务 glue 生成 + 注册），向量库/知识库
客户端接入。

OHOS 适配说明：
  - 制品仓已发布依赖（requires 全部可 conan download 校验，过 PF4/L0i）：
    openssl/spdlog/jsoncpp/curl/icu/glib/pulseaudio/libsodium/grpc(+protobuf
    传递)/nlohmann-json/libkylin-ai-system-private(KylinAiEngine 头)/
    kysdk-ai-common(KysdkAiCommon 头)。
  - 私有依赖（制品仓无配方，L0i 不能声明 requires → vendor 构建，R49
    staging 前缀，单 PR 原子交付，同 libkysdk-ai-private/1.1.0.1 先例）：
      * ai-proto（取 libkylin-ai-system-private debian/1.2.0.1-1 内嵌，
        独立 kylin-ai-proto 仓库 XML 旧）：KylinAiProto 宏 + gdbus XML×7
        + grpc vector-db protos → staging/share/...
      * libkysdk-vector-engine-client 1.2.0.0 → libkysdk-vector-engine-client.so
        （grpc++/protobuf 链接，gRPC::grpc++ 上游 config 注入）
      * kylin-ai-document-qa-service 1.2.0.0 的 document-qa-client →
        libkyai-knowledgebase-client.so（gdbus knowledgebase glue）
    两个 SHARED 库是主二进制的 DT_NEEDED，随包发布（package lib/）。
  - 0001 补丁：CMakeLists 裸 lib 名改 Conan CONFIG 目标（JsonCpp/OpenSSL/
    CURL/icu）、pulse 走 PkgConfig::LIBPULSE（增补 libpulse*.pc）、
    pkg_check 块后补 link_directories（-L 不传给 lld）、install /usr|/etc
    绝对路径越权改前缀。
  - 0002 补丁：44 处 <jsoncpp/json/...> → <json/...>。
  - 0003-0006 补丁：vendor 三件套的宏路径变量化与 install 越权修正。
  - 上游测试：test/ 下 5 个可执行（testencryption/testaes256/testenginemanager/
    testmodelstatustracker/testsystemoperation，手写 main 非 GTest），
    ENABLE_TEST=ON 真实构建 + build() 运行并逐例记录（R51 三步法）。
"""
import glob
import os
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Git


class KylinAiRuntimeConan(ConanFile):
    name = "kylin-ai-runtime"
    version = "1.1.0.1"
    description = "Kylin AI 运行时：AI 服务 gdbus 守护进程（openKylin 麒麟 AI 子系统）"
    license = "GPL-3.0-or-later"
    homepage = "https://gitee.com/openkylin/kylin-ai-runtime"
    url = "https://gitee.com/openkylin/kylin-ai-runtime"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    exports_sources = "patches/*"

    def requirements(self):
        # glib/2.88.0 钉 zlib/1.3.1、pulseaudio/17.0.1 钉 zlib/1.3.2 → 统一提升
        self.requires("zlib/1.3.2", override=True)
        # grpc/1.84.0 钉 openssl/3.5.6 → 与主构建统一到制品仓最新 3.5.8.1
        self.requires("openssl/3.5.8.1", override=True)

        self.requires("spdlog/1.17.0")
        # spdlog::spdlog 不传播 fmt::fmt（SPDLOG_FMT_EXTERNAL），消费方需显式依赖
        self.requires("fmt/12.2.0")
        self.requires("jsoncpp/1.9.8.1", transitive_headers=True, transitive_libs=True)
        self.requires("curl/8.22.0")
        self.requires("icu/76.1")
        # gio-unix-2.0.pc + gdbus-codegen + gdbus glue 头/链接
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)  # pulseaudio/17.0.1 依赖钉死 2.88.0
        self.requires("pulseaudio/17.0.1", transitive_libs=True)
        self.requires("libsodium/1.0.20", transitive_libs=True)
        # vendor vecclient 链接 grpc++/protobuf（codegen 二进制 protoc/
        # grpc_cpp_plugin 亦来自这两个包）
        self.requires("grpc/1.84.0", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann-json/3.11.2", transitive_headers=True, transitive_libs=True)
        # KylinAiEngine（aiengine 组件头，cmake_file_name=KylinAiEngine）
        self.requires("libkylin-ai-system-private/1.2.0.0", transitive_headers=True)
        # KysdkAiCommon（cmake_file_name=KysdkAiCommon）
        self.requires("kysdk-ai-common/1.1.0.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        d = self.conan_data["sources"]
        # vendor 私有依赖（制品仓无配方）。gitee 归档端点按 User-Agent 过滤，
        # 显式传 curl UA（同 kylin-ai-proto/libkysdk-ai-private 先例）。
        get(self, **d["ai-common"], headers={"User-Agent": "curl/8.0"},
            strip_root=True, destination="vendor/ai-common")
        get(self, **d["ai-proto"], headers={"User-Agent": "curl/8.0"},
            strip_root=True, destination="vendor/_sp")
        ai_proto_src = os.path.join(self.source_folder, "vendor", "_sp", "ai-proto")
        shutil.move(ai_proto_src,
                    os.path.join(self.source_folder, "vendor", "ai-proto"))
        shutil.rmtree(os.path.join(self.source_folder, "vendor", "_sp"),
                      ignore_errors=True)
        get(self, **d["vecclient"], headers={"User-Agent": "curl/8.0"},
            strip_root=True, destination="vendor/vecclient")
        get(self, **d["docqa"], headers={"User-Agent": "curl/8.0"},
            strip_root=True, destination="vendor/_dq")
        shutil.move(os.path.join(self.source_folder, "vendor", "_dq",
                                 "document-qa-client"),
                    os.path.join(self.source_folder, "vendor", "docqa-client"))
        shutil.rmtree(os.path.join(self.source_folder, "vendor", "_dq"),
                      ignore_errors=True)
        # 主源码：Git clone 固定 tag（gitee 归档端点对 conan 下载器返回 HTML
        # 反爬页，sha256 无法固定；同 kylin-ai-proto 先例）。
        git = Git(self)
        tmp = "_git_src"
        try:
            git.clone(url=d["main"]["url"], target=tmp,
                      args=["--branch", d["main"]["tag"], "--depth", "1"])
        except Exception:
            # W3/CI 预下载改写 file:// 快照时 clone 失败 → 已有内容直接用
            if not os.path.isdir(tmp):
                raise
        src = os.path.join(self.source_folder, "src")
        if os.path.isdir(src):
            shutil.rmtree(src)
        shutil.move(os.path.join(self.source_folder, tmp), src)
        for junk in (".git",):
            shutil.rmtree(os.path.join(src, junk), ignore_errors=True)
        apply_conandata_patches(self)

    # ---------- 布局辅助 ----------

    def _staging(self):
        return os.path.join(self.build_folder, "staging")

    def _dep_pkg(self, name):
        try:
            return self.dependencies[name].package_folder
        except Exception:
            for dep in self.dependencies.values():
                if getattr(dep, "ref", None) and dep.ref.name == name:
                    return dep.package_folder
        return None

    def _toolchain_file(self):
        for cand in (os.path.join(self.generators_folder, "conan_toolchain.cmake"),
                     os.path.join(self.build_folder, "generators",
                                  "conan_toolchain.cmake")):
            if os.path.isfile(cand):
                return cand
        raise SystemExit("conan_toolchain.cmake not found in generators folder")

    # ---------- generate ----------

    def generate(self):
        PkgConfigDeps(self).generate()
        CMakeDeps(self).generate()
        self._augment_pkg_configs()
        self._write_toolchain()

        # E266: OHOS SDK lld 运行时依赖 libxml2.so.16（同 libkysdk-ai-private）
        env = Environment()
        for lib_dir in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isfile(os.path.join(lib_dir, "libxml2.so.16")):
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                break
        glib_bin = os.path.join(self._dep_pkg("glib") or "", "bin")
        if os.path.isdir(glib_bin):
            env.prepend_path("PATH", glib_bin)
        env.vars(self).save_script("lld_fix")

    def _write_toolchain(self):
        staging = self._staging()
        glib_pkg = self._dep_pkg("glib")
        grpc_pkg = self._dep_pkg("grpc")
        protobuf_pkg = self._dep_pkg("protobuf")
        abseil_pkg = self._dep_pkg("abseil-cpp")
        openssl_pkg = self._dep_pkg("openssl")
        tc = CMakeToolchain(self)

        # codegen 可执行程序（gdbus-codegen / protoc / grpc_cpp_plugin）
        prog_paths = []
        if glib_pkg:
            prog_paths.append(os.path.join(glib_pkg, "bin"))
            tc.variables["KYLAI_GDBUS_CODEGEN"] = os.path.join(
                glib_pkg, "bin", "gdbus-codegen")
        if grpc_pkg:
            prog_paths.append(os.path.join(grpc_pkg, "bin"))
            tc.variables["KYLAI_GRPC_CPP_PLUGIN"] = os.path.join(
                grpc_pkg, "bin", "grpc_cpp_plugin")
        if protobuf_pkg:
            prog_paths.append(os.path.join(protobuf_pkg, "bin"))
            tc.variables["PROTOBUF_PROTOC_EXECUTABLE"] = os.path.join(
                protobuf_pkg, "bin", "protoc")
        if prog_paths:
            tc.variables["CMAKE_PROGRAM_PATH"] = ";".join(prog_paths)

        # vendor KylinAiProto（宏 + 协议 XML，装到 staging）
        tc.variables["KylinAiProto_DIR"] = os.path.join(
            staging, "share", "KylinAiProto", "cmake")
        tc.variables["KYLAI_GDBUS_PROTOCOL_DIR"] = os.path.join(
            staging, "share", "kylin-ai", "protocols", "gdbus")
        tc.variables["KYLAI_GRPC_PROTOCOL_DIR"] = os.path.join(
            staging, "share", "kylin-ai", "protocols", "grpc")

        # vecclient 子构建：gRPC 上游 config（grpc 配方 cmake_find_mode=none，
        # 同 grpc/1.84.0 test_package 注入模式）
        if grpc_pkg:
            tc.variables["gRPC_DIR"] = os.path.join(
                grpc_pkg, "lib", "cmake", "grpc")
        if protobuf_pkg:
            tc.variables["Protobuf_DIR"] = os.path.join(
                protobuf_pkg, "lib", "cmake", "protobuf")
            tc.variables["utf8_range_DIR"] = os.path.join(
                protobuf_pkg, "lib", "cmake", "utf8_range")
        if abseil_pkg:
            tc.variables["absl_DIR"] = os.path.join(
                abseil_pkg, "lib", "cmake", "absl")
        if openssl_pkg:
            tc.variables["OPENSSL_ROOT_DIR"] = openssl_pkg

        # 主构建 link_directories(${KYAI_CONAN_LIB_DIRS})：裸 -l 名的库目录
        lib_dirs = [os.path.join(staging, "lib")]
        for name in ("glib", "pulseaudio", "libsodium", "icu", "openssl",
                     "jsoncpp", "spdlog", "kysdk-ai-common",
                     "libkylin-ai-system-private"):
            pkg = self._dep_pkg(name)
            if pkg:
                lib_dirs.append(os.path.join(pkg, "lib"))
                pulse_sub = os.path.join(pkg, "lib", "pulseaudio")
                if os.path.isdir(pulse_sub):
                    lib_dirs.append(pulse_sub)
        tc.variables["KYAI_CONAN_LIB_DIRS"] = ";".join(lib_dirs)

        # header-only 组件头目录（aiengine.h / kysdk-ai-common）
        inc = []
        for name in ("openssl", "jsoncpp", "icu", "spdlog", "fmt"):
            pkg = self._dep_pkg(name)
            if pkg:
                d = os.path.join(pkg, "include")
                if os.path.isdir(d):
                    inc.append(d)
        sys_pkg = self._dep_pkg("libkylin-ai-system-private")
        if sys_pkg:
            d = os.path.join(sys_pkg, "include")
            if os.path.isdir(d):
                inc.append(d)
        # vendor vecclient 头内 #include <nlohmann/json.hpp>：主构建未链
        # nlohmann 目标 → 显式挂 include
        nl = self._dep_pkg("nlohmann-json")
        if nl:
            d = os.path.join(nl, "include")
            if os.path.isdir(d):
                inc.append(d)
        # kysdk-ai-common：制品仓已发布包头较旧（缺 ok0.3 错误码枚举），
        # 用 vendor 的 ok0.3 头目录（须排在发布包 include 之前，见 conandata 注）
        vendored = os.path.join(self.source_folder, "vendor", "ai-common", "include")
        if os.path.isdir(vendored):
            inc.insert(0, vendored)
        tc.variables["KYAI_EXTRA_INCLUDE_DIRS"] = ";".join(inc)

        # 上游 5 个手写 main 测试（非 GTest）
        tc.variables["ENABLE_TEST"] = "ON"
        tc.generate()

    def _augment_pkg_configs(self):
        """PkgConfigDeps 不覆盖的 .pc 增补：写入 generators 目录。"""
        gen = self.generators_folder

        def _copy_rewrite(pkg, pc_name, dst_name=None):
            if not pkg:
                return
            src = os.path.join(pkg, "lib", "pkgconfig", pc_name)
            if not os.path.isfile(src):
                self.output.warning(f"missing pc: {src}")
                return
            content = open(src, encoding="utf-8").read()
            content = content.replace("prefix=/",
                                      f"prefix={pkg.replace(os.sep, '/')}")
            open(os.path.join(gen, dst_name or pc_name), "w",
                 encoding="utf-8", newline="\n").write(content)

        def _write_pc(name, desc, pkg, libs, cflags_inc=""):
            content = (
                f"prefix={pkg.replace(os.sep, '/')}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: {name}\n"
                f"Description: {desc}\n"
                f"Version: 1.0\n"
                f"Libs: -L${{prefix}}/lib {libs}\n"
                f"Cflags: -I${{prefix}}/include{cflags_inc}\n")
            open(os.path.join(gen, f"{name}.pc"), "w",
                 encoding="utf-8", newline="\n").write(content)

        # gio-unix-2.0.pc：glib 配方未声明该组件（先例同法，包内自带 pc）
        _copy_rewrite(self._dep_pkg("glib"), "gio-unix-2.0.pc")

        # libpulse / libpulse-simple.pc：pulseaudio 配方无 pkg_config_name，
        # PkgConfigDeps 不生成；主构建 pkg_check_modules(LIBPULSE IMPORTED_TARGET)
        # 需要（含 pulsecommon 私有库目录）
        pulse_pkg = self._dep_pkg("pulseaudio")
        if pulse_pkg:
            sub = os.path.join(pulse_pkg, "lib", "pulseaudio")
            subflag = f" -L{sub.replace(os.sep, '/')}" if os.path.isdir(sub) else ""
            _write_pc("libpulse", "PulseAudio client",
                      pulse_pkg, f"-lpulse -lpulsecommon-17.0",
                      "")
            content = open(os.path.join(gen, "libpulse.pc")).read()
            content = content.replace(
                f"Libs: -L${{prefix}}/lib -lpulse -lpulsecommon-17.0",
                f"Libs: -L${{prefix}}/lib{subflag} -lpulse -lpulsecommon-17.0")
            open(os.path.join(gen, "libpulse.pc"), "w").write(content)
            _write_pc("libpulse-simple", "PulseAudio simple API",
                      pulse_pkg, "-lpulse-simple -lpulse -lpulsecommon-17.0")
            content = open(os.path.join(gen, "libpulse-simple.pc")).read()
            content = content.replace(
                "Libs: -L${prefix}/lib -lpulse-simple",
                f"Libs: -L${{prefix}}/lib{subflag} -lpulse-simple")
            open(os.path.join(gen, "libpulse-simple.pc"), "w").write(content)

        # glib 系列 .pc 前置 staging lib：`-lglib-2.0` 等优先命中
        # build() 合成的共享库（而非 conan 静态归档），避免进程内两份 glib
        staging_lib = self._staging_lib_dir().replace(os.sep, "/")
        for pc in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc",
                   "gmodule-2.0.pc", "gthread-2.0.pc", "gio-unix-2.0.pc"):
            path = os.path.join(gen, pc)
            if not os.path.isfile(path):
                continue
            lines = open(path, encoding="utf-8").read().splitlines()
            for i, line in enumerate(lines):
                if line.startswith("Libs:"):
                    lines[i] = f"Libs: -L{staging_lib}" + line[len("Libs:"):]
                    break
            open(path, "w", encoding="utf-8", newline="\n").write(
                "\n".join(lines) + "\n")

    # ---------- vendor 子构建 ----------

    def _ohos_cxx(self):
        """构建期需要直接调用 OHOS clang++（合成 glib 共享库时）。"""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if isinstance(compilers, dict):
            cpp = compilers.get("cpp")
            if cpp and os.path.isfile(cpp):
                return cpp
        for cand in glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++"):
            return cand
        return shutil.which("clang++")

    def _sign_elf(self, path):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer) or not os.path.isfile(path):
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if objcopy and os.path.isfile(objcopy):
            self.run(f"{shlex.quote(objcopy)} --remove-section .codesign "
                     f"{shlex.quote(path)} 2>/dev/null || true")
        self.run(shlex.join([signer, "sign", "-inFile", path,
                             "-outFile", path, "-selfSign", "1"]))
        try:
            os.chown(path, os.getuid(), os.getgid())
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _stage_shared_glib(self):
        """glib 配方只产静态库（conan center 无 shared variant）。若 vendor 客户端
        .so 与主二进制各静态链接一份 glib，同一进程会出现两份 gobject
        （各自独立的 quark/type 表）→ 启动即触发
        ``g_type_register_static: assertion failed (static_quark_type_flags)``
        并 abort。故用静态归档合成 glib/gobject/gio/gmodule/gthread 共享库，
        主构建与 vendor 客户端统一动态链接同一实例。"""
        glib = self._dep_pkg("glib")
        if not glib:
            return
        cxx = self._ohos_cxx()
        if not cxx:
            raise ConanInvalidConfiguration("clang++ not found for shared glib")
        pcre2 = self._dep_pkg("pcre2")
        out = self._staging_lib_dir()
        os.makedirs(out, exist_ok=True)
        glib_lib = os.path.join(glib, "lib")
        ffi = os.path.join(glib_lib, "libffi.a")
        intl = os.path.join(glib_lib, "libintl.a")
        glib_deps = [ffi, intl]
        if pcre2:
            pc8 = os.path.join(pcre2, "lib", "libpcre2-8.a")
            if os.path.isfile(pc8):
                glib_deps.append(pc8)
        # (组件名, 静态归档, 额外链接项)  顺序：glib → gobject → module/thread → gio
        specs = [
            ("glib-2.0", "libglib-2.0.a",
             glib_deps + ["-lpthread", "-lm", "-ldl"]),
            ("gobject-2.0", "libgobject-2.0.a",
             ["-lglib-2.0", ffi, "-lpthread", "-lm", "-ldl"]),
            ("gmodule-2.0", "libgmodule-2.0.a",
             ["-lglib-2.0", "-ldl"]),
            ("gthread-2.0", "libgthread-2.0.a",
             ["-lglib-2.0", "-lpthread"]),
            ("gio-2.0", "libgio-2.0.a",
             ["-lgobject-2.0", "-lglib-2.0", "-lpthread", "-lm", "-ldl"]),
        ]
        out_u = out.replace(os.sep, "/")
        for name, archive, extra in specs:
            arch = os.path.join(glib_lib, archive)
            if not os.path.isfile(arch):
                self.output.warning(f"shared glib: missing {arch}")
                continue
            real = os.path.join(out, f"lib{name}.so.0")
            cmd = [cxx, "-shared", "-fPIC",
                   f"-Wl,-soname,lib{name}.so.0", "-o", real,
                   "-Wl,--whole-archive", arch, "-Wl,--no-whole-archive",
                   f"-L{out_u}"] + extra
            self.run(shlex.join(cmd))
            link = os.path.join(out, f"lib{name}.so")
            if not os.path.lexists(link):
                os.symlink(os.path.basename(real), link)
            self._sign_elf(real)
            self.output.info(f"shared glib: staged {real}")

    def _cmake(self, src_dir, build_dir, extra_defs=None, install=True,
               install_prefix=None):
        toolchain = self._toolchain_file()
        cfg = (f"-DCMAKE_TOOLCHAIN_FILE={shlex.quote(toolchain)} "
               f"-DCMAKE_INSTALL_PREFIX={shlex.quote(install_prefix or self._staging())} "
               f"-DCMAKE_BUILD_TYPE={self.settings.build_type}")
        if extra_defs:
            cfg += " " + " ".join(f"-D{k}={shlex.quote(str(v))}"
                                  for k, v in extra_defs.items())
        self.run(f"cmake -S {shlex.quote(src_dir)} -B {shlex.quote(build_dir)} {cfg}")
        self.run(f"cmake --build {shlex.quote(build_dir)} -j8")
        if install:
            self.run(f"cmake --install {shlex.quote(build_dir)}")

    def _stage_vendored_pkg_configs(self):
        """vendor 两个客户端库的 .pc 复制进 generators 目录（prefix=staging），
        供主构建 pkg_check_modules(VECTOR_DB/KYAI_KNOWLEDGE_BASE_CLIENT) 发现。
        （vendor 构建发生在 build()，晚于 generate()，故在此阶段写入。）"""
        gen = self.generators_folder
        staging = self._staging().replace(os.sep, "/")
        specs = [
            # (staging pc 路径, 目标文件名, 额外 Cflags 相对 include 修正)
            ("share/pkgconfig/kysdk-vector-engine-client.pc",
             "kysdk-vector-engine-client.pc",
             [("Cflags: -I/usr/include/kysdk-vector-engine-client",
               "Cflags: -I${prefix}/include/kysdk-vector-engine-client")]),
            ("share/pkgconfig/kyai-knowledgebase-client.pc",
             "kyai-knowledgebase-client.pc",
             [("Cflags: -I/usr/include/kylin-ai",
               "Cflags: -I${prefix}/include/kylin-ai -I${prefix}/include")]),
        ]
        for rel, name, fixes in specs:
            src = os.path.join(self._staging(), rel)
            if not os.path.isfile(src):
                self.output.warning(f"staged pc missing: {src}")
                continue
            content = open(src, encoding="utf-8").read()
            for old, new in fixes:
                content = content.replace(old, new)
            # 上游 .pc 无 prefix/libdir/includedir 头（绝对 /usr 路径已由
            # fixes 改写为 ${prefix} 相对），补齐变量定义
            header = (f"prefix={staging}\n"
                      "libdir=${prefix}/lib\n"
                      "includedir=${prefix}/include\n\n")
            open(os.path.join(gen, name), "w",
                 encoding="utf-8", newline="\n").write(header + content)

    # ---------- build ----------

    def build(self):
        staging = self._staging()
        vendor = os.path.join(self.source_folder, "vendor")

        # 0) glib 共享库合成（先于 vendor/主构建，供统一动态链接）
        self._stage_shared_glib()

        # 1) ai-proto（INTERFACE + cmake 宏 + 协议 XML）→ staging
        self._cmake(os.path.join(vendor, "ai-proto"),
                    os.path.join(self.build_folder, "vendor-proto"))

        # 2) vecclient：libkysdk-vector-engine-client.so（grpc++/protobuf）
        #    OHOS 上 CMake 探测到 CMAKE_SYSTEM_NAME=HarmonyOS，而 CMake/OHOS SDK
        #    无 Platform/HarmonyOS.cmake → 平台 soname 变量为空，
        #    set_target_properties(... SOVERSION) 被忽略、链接命令无 -soname，
        #    产出 .so 缺 DT_SONAME（CI L5a）。此处按目标显式补 -Wl,-soname。
        self._cmake(os.path.join(vendor, "vecclient"),
                    os.path.join(self.build_folder, "vendor-vecclient"),
                    extra_defs={"CMAKE_SHARED_LINKER_FLAGS":
                                "-Wl,-soname,libkysdk-vector-engine-client.so"})

        # 3) docqa document-qa-client：libkyai-knowledgebase-client.so
        #    （gdbus knowledgebase glue；需 KylinAiProto 宏 + gio-unix-2.0.pc）
        self._cmake(os.path.join(vendor, "docqa-client"),
                    os.path.join(self.build_folder, "vendor-docqa"),
                    extra_defs={"CMAKE_SHARED_LINKER_FLAGS":
                                "-Wl,-soname,libkyai-knowledgebase-client.so"})

        # 4) vendor .pc 前缀改写到 generators（主构建 pkg_check_modules 用）
        self._stage_vendored_pkg_configs()

        # 5) 主构建（ENABLE_TEST=ON → test/ 5 个用例一并构建）；
        #    cmake_layout 下 source_folder=build 根而主源码在 src/ 子目录，
        #    故与 vendor 同法走显式 -S/-B 原始 cmake 命令
        self._cmake(os.path.join(self.source_folder, "src"),
                    os.path.join(self.build_folder, "main-build"),
                    extra_defs={"ENABLE_TEST": "ON"},
                    install=True, install_prefix=self.package_folder)

        # 6) 真实执行上游测试（R51 三步法：构建 ✓ → 运行 → 逐例记录）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_dir = None
        for root, _d, files in os.walk(self.build_folder):
            if "testencryption" in files and "CMakeFiles" not in root:
                test_dir = root
        if not test_dir:
            self.output.warning("上游 test 输出目录未找到，跳过运行")
            return
        tests = ["testencryption", "testaes256", "testenginemanager",
                 "testmodelstatustracker", "testsystemoperation"]
        env = dict(os.environ)
        ld = [self._staging_lib_dir()]
        for dep in self.dependencies.values():
            if dep.package_folder:
                ld.append(os.path.join(dep.package_folder, "lib"))
                sub = os.path.join(dep.package_folder, "lib", "pulseaudio")
                if os.path.isdir(sub):
                    ld.append(sub)
        for root, _d, files in os.walk(self.build_folder):
            for f in files:
                if f.endswith(".so") and "CMakeFiles" not in root:
                    ld.append(root)
        merged = ":".join(ld)
        if env.get("LD_LIBRARY_PATH"):
            merged += ":" + env["LD_LIBRARY_PATH"]
        env["LD_LIBRARY_PATH"] = merged
        self.output.info("=== 上游测试实测（R51）===")
        for t in tests:
            tbin = os.path.join(test_dir, t)
            if not os.path.isfile(tbin):
                self.output.info(f"  [SKIP] {t}: 未构建")
                continue
        failures = []
        for t in tests:
            tbin = os.path.join(test_dir, t)
            if not os.path.isfile(tbin):
                self.output.info(f"  [SKIP] {t}: 未构建")
                failures.append(f"{t}: not built")
                continue
            rc, out, detail = None, "", ""
            try:
                proc = subprocess.run([f"./{t}"], env=env, cwd=test_dir,
                                      capture_output=True, text=True,
                                      timeout=120)
                rc = proc.returncode
                out = (proc.stdout or "") + (proc.stderr or "")
            except subprocess.TimeoutExpired as exc:
                out = (exc.stdout or "") + (exc.stderr or "")
                detail = " (timeout 120s)"
            status = "PASS" if rc == 0 else "FAIL"
            tail = " | ".join(l for l in out.strip().splitlines()[-3:])
            self.output.info(f"  [{status}] {t} rc={rc}{detail}"
                             f" {tail[:200]}")
            if rc != 0:
                failures.append(f"{t}: rc={rc}{detail} {tail[:120]}")
        if failures:
            from conan.errors import ConanException
            raise ConanException(
                "上游测试失败 (R51 断言 rc=0): " + "; ".join(failures))

    def _staging_lib_dir(self):
        return os.path.join(self._staging(), "lib")

    # ---------- package ----------

    def package(self):
        # vendor 两个 SHARED 客户端库是主二进制 DT_NEEDED → 随包发布
        from conan.tools.files import copy as _copy
        for so in ("libkysdk-vector-engine-client.so*",
                   "libkyai-knowledgebase-client.so*",
                   "libglib-2.0.so*", "libgobject-2.0.so*",
                   "libgio-2.0.so*", "libgmodule-2.0.so*",
                   "libgthread-2.0.so*"):
            _copy(self, so, src=self._staging_lib_dir(),
                  dst=os.path.join(self.package_folder, "lib"))
        self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        for sub in ("bin", "lib"):
            for binary in glob.glob(os.path.join(self.package_folder, sub, "*")):
                if not os.path.isfile(binary) or os.path.islink(binary):
                    continue
                with open(binary, "rb") as h:
                    if h.read(4) != b"\x7fELF":
                        continue
                if objcopy and os.path.isfile(objcopy):
                    self.run(f"{shlex.quote(objcopy)} --remove-section .codesign "
                             f"{shlex.quote(binary)} 2>/dev/null || true")
                self.run(shlex.join(
                    [signer, "sign", "-inFile", binary, "-outFile", binary,
                     "-selfSign", "1"]))
                try:
                    os.chown(binary, os.getuid(), os.getgid())
                    os.chmod(binary, 0o755)
                except OSError:
                    pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["etc", "share"]
        # 随包发布的 vendor 客户端库（消费方与运行时需要）
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["kysdk-vector-engine-client",
                              "kyai-knowledgebase-client"]
