#!/usr/bin/env python3
"""Conan recipe — libkysdk-genai 1.1.0.1.

麒麟 AI 生成式 AI NLP 客户端库（openKylin，上游仓库 libkysdk-genai-nlp）：
  - 产物：libkysdk-genai-nlp.so（SHARED，SONAME libkysdk-genai-nlp.so）
    + include/kylin-ai/genai/text/（chat/chatmessage/config/error/result 头文件）
    + share/pkgconfig/kysdk-genai-nlp.pc
  - 构建系统：CMake（C++17），gdbus 协议 glue 由 kylin_ai_generate_gdbus_proto_code
    宏（KylinAiProto）在 configure 期调用 gdbus-codegen 生成（gennlpserviceglue.c/h）。

OHOS 适配要点：
  - 制品仓依赖：kysdk-ai-common/1.1.0.1（find_package(KysdkAiCommon) +
    pkg kysdk-ai-common）、libkysdk-ai-private/1.1.0.1（kyai 系列）、
    glib/2.88.0.1（gio-unix-2.0.pc + gdbus-codegen）、jsoncpp/1.9.8、
    json-glib/1.10.6、openssl/3.5.8.1。
  - 私有依赖 KylinAiProto（L0i 限制：不能 requires 未发布配方）：上游
    find_package(KylinAiProto REQUIRED) + kylin_ai_generate_gdbus_proto_code 宏，
    但制品仓无 KylinAiProto 配方（libkysdk-ai-private package() 未导出）。
    参照 libkysdk-ai-private 的 vendor 方式：获取 libkylin-ai-system-private
    debian/1.2.0.1-1 归档内嵌 ai-proto，构建到 build_folder/staging，
    generate() 经 CMakeToolchain 注入 KylinAiProto_DIR（staging/share/
    KylinAiProto/cmake）与 KYLAI_GDBUS_CODEGEN / KYLAI_GDBUS_PROTOCOL_DIR
    （0003/0004 补丁把宏硬编码路径变量化）。
  - 0001 补丁：jsoncpp 头文件 include 前缀 <jsoncpp/json/..> → <json/..>
    （制品仓 jsoncpp 头在 include/json/，同 libkysdk-ai-private 0002）。
  - 0002 补丁：find_package(jsoncpp) → find_package(JsonCpp CONFIG REQUIRED) +
    target jsoncpp → JsonCpp::JsonCpp；pkg_check_modules(GIO/JSON) 后补
    link_directories（-L 不传给 lld 则 -lgio-2.0/-ljson-glib-1.0 等找不到，
    同 libkysdk-ai-private 0001）；补 AI_COMMON_INCLUDE_DIRS/kylin-ai 头文件
    前缀（上游依赖系统 /usr/include/kylin-ai）；install(DIRECTORY usr/ DESTINATION
    /usr) 越权 → DESTINATION .（配合 conan package() --prefix 落到包内 share/）；
    注入 SONAME（CMake 无 OHOS 平台模块，VERSION/SOVERSION 不生成 -Wl,-soname）。
  - json-glib 冲突：json-glib/1.10.6 配方 requires glib/2.84.0.1，与
    libkysdk-ai-private 要求的 glib/2.88.0.1 冲突 → override glib/2.88.0.1，
    json-glib 在本配方图内按 --build=missing 重编一次（meson，数分钟，缓存复用）。
  - OHOS 动态链接器要求签名 ELF：SDK lld 产物自带 .codesign 段，签名前 objcopy
    移除（package() 内 _sign_installed_elfs，同 libkysdk-ai-private）。
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Git

_OFFICIAL_REPO = "https://gitee.com/openkylin/libkysdk-genai-nlp.git"


class LibkysdkGenaiConan(ConanFile):
    name = "libkysdk-genai"
    version = "1.1.0.1"
    description = "Kylin AI 生成式 AI NLP 客户端库（libkysdk-genai / 上游 libkysdk-genai-nlp）"
    license = "GPL-3.0-or-later"
    homepage = "https://gitee.com/openkylin/libkysdk-genai-nlp"
    url = "https://gitee.com/openkylin/libkysdk-genai-nlp"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    exports_sources = "patches/*"

    def requirements(self):
        # 主 CMakeLists：find_package(OpenSSL REQUIRED) / find_package(KysdkAiCommon
        # REQUIRED) / find_package(JsonCpp CONFIG REQUIRED) / pkg_check_modules
        # (GIO gio-unix-2.0) / pkg_check_modules(JSON json-glib-1.0)；
        # libkysdk-ai-private 为 W0 确认的系列依赖（kyai 族，提供 kyai-config.pc）。
        self.requires("kysdk-ai-common/1.1.0.1", transitive_headers=True)
        self.requires("libkysdk-ai-private/1.1.0.1")
        # glib：libkysdk-ai-private 需 glib/2.88.0.1（gio-unix + gdbus-codegen）；
        # json-glib/1.10.6 配方 pin glib/2.84.0.1 → override 统一到 2.88.0.1
        # （json-glib 在本图按 --build=missing 重编一次）。
        self.requires("glib/2.88.0.1", override=True,
                      transitive_headers=True, transitive_libs=True)
        self.requires("jsoncpp/1.9.8", transitive_headers=True, transitive_libs=True)
        self.requires("json-glib/1.10.6", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/3.5.8.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 主源码：gitee 归档端点(/repository/archive/...)对 conan Python urllib
        # 下载器返回 HTML 反爬页（sha256 每次不同无法固定），改用 Git clone 官方源
        # + --branch upstream/1.1.0.1 --depth 1 + 固定 commit（R39 合规官方源）。
        # export_conandata_patches 已把 patches/ 放进 source 目录（目标 "." 非空），
        # 故克隆到临时子目录再搬回（同 kysdk-ai-common）。
        git = Git(self)
        tmp = "_git_src"
        clone_args = ["--branch", self.conan_data["sources"]["tag"], "--depth", "1"]
        try:
            git.clone(url=self.conan_data["sources"]["url"], target=tmp, args=clone_args)
        except Exception:
            # W3/CI 预下载会把 conandata.yml 的 URL（含备用字段）全部改写成 file://
            # 快照，clone 报 invalid gitfile format，回退用硬编码官方源常量。
            git = Git(self)
            git.clone(url=_OFFICIAL_REPO, target=tmp, args=clone_args)
        for item in os.listdir(os.path.join(self.source_folder, tmp)):
            shutil.move(os.path.join(self.source_folder, tmp, item), self.source_folder)
        shutil.rmtree(os.path.join(self.source_folder, tmp), ignore_errors=True)

        # vendored 私有依赖（制品仓无 KylinAiProto 配方）：libkylin-ai-system-private
        # debian/1.2.0.1-1 内嵌 ai-proto（KylinAiProtoConfig/Functions/Generate +
        # 协议 XML 含 gennlpservice.xml，与 libkysdk-genai 1.1.0.1 期望匹配）。
        # gitee 归档按 User-Agent 过滤，显式传 curl UA（同 libkysdk-ai-private）。
        get(self, **self.conan_data["sources"]["kylin-ai-system"],
            headers={"User-Agent": "curl/8.0"}, strip_root=True,
            destination="vendor/kylin-ai-system")
        ai_proto_src = os.path.join(self.source_folder, "vendor",
                                    "kylin-ai-system", "ai-proto")
        ai_proto_dst = os.path.join(self.source_folder, "vendor", "kylin-ai-proto")
        if os.path.isdir(ai_proto_src):
            shutil.move(ai_proto_src, ai_proto_dst)
            shutil.rmtree(os.path.dirname(ai_proto_src), ignore_errors=True)

    def _staging_dir(self):
        return os.path.join(self.build_folder, "staging")

    def generate(self):
        # R33：编译器/链接标志从 Conan 控制，不依赖 ambient LDFLAGS。
        # CMake 在 configure 期读取进程环境 LDFLAGS 注入 CMAKE_*_LINKER_FLAGS；
        # 本机/CI shell 若已 export LDFLAGS=-L$DEFAULT_PREFIX/lib，会把
        # /usr/local/lib 的共享 glib 误链进产物（实测 libkysdk-genai-nlp.so
        # NEEDED 出现 libgio-2.0.so.0 等）。显式清空，保证只链 Conan 依赖。
        os.environ["LDFLAGS"] = ""
        os.environ.setdefault("CFLAGS", "-fPIC -O2")
        os.environ.setdefault("CXXFLAGS", "-fPIC -O2")

        PkgConfigDeps(self).generate()
        CMakeDeps(self).generate()
        self._augment_glib_unix_pkg_config()
        tc = CMakeToolchain(self)
        glib_bin = None
        glib_dep = self.dependencies.get("glib")
        if glib_dep and glib_dep.package_folder:
            glib_bin = os.path.join(glib_dep.package_folder, "bin")
            tc.variables["CMAKE_PROGRAM_PATH"] = glib_bin
        staging = self._staging_dir()
        if glib_bin:
            tc.variables["KYLAI_GDBUS_CODEGEN"] = os.path.join(glib_bin, "gdbus-codegen")
        tc.variables["KYLAI_GDBUS_PROTOCOL_DIR"] = os.path.join(
            staging, "share", "kylin-ai", "protocols", "gdbus")
        # 不覆盖 CMAKE_PREFIX_PATH（会屏蔽 CMakeDeps 生成的 JsonCpp/OpenSSL 等
        # Config），而是用 KylinAiProto_DIR 直接定位 vendor 装到 staging 的 Config。
        tc.variables["KylinAiProto_DIR"] = os.path.join(
            staging, "share", "KylinAiProto", "cmake")
        tc.generate()

        # E266: OHOS SDK lld 运行时依赖 libxml2.so.16，CI 沙箱库搜索路径找不到 → 链接
        # 静默失败；补 LD_LIBRARY_PATH（同 libkysdk-ai-private）。
        env = Environment()
        for lib_dir in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isfile(os.path.join(lib_dir, "libxml2.so.16")):
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                break
        if glib_bin:
            env.prepend_path("PATH", glib_bin)
        env.vars(self).save_script("lld_fix")

    def _augment_glib_unix_pkg_config(self):
        # glib 配方 cpp_info 未声明 gio-unix-2.0 组件，PkgConfigDeps 不生成转发
        # gio-unix-2.0.pc（主 CMakeLists 的 pkg_check_modules(GIO REQUIRED
        # gio-unix-2.0) 需要它）。从 glib 包内复制该 .pc 到 generators 并改写
        # prefix（同 libkysdk-ai-private）。
        glib_folder = self.dependencies["glib"].package_folder
        src = os.path.join(glib_folder, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(src):
            return
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        prefix = glib_folder.replace(os.sep, "/")
        content = open(src, encoding="utf-8").read()
        content = content.replace("prefix=/", f"prefix={prefix}")
        open(dst, "w", encoding="utf-8", newline="\n").write(content)

    def _toolchain_file(self):
        candidates = [
            os.path.join(self.generators_folder, "conan_toolchain.cmake"),
            os.path.join(self.build_folder, "generators", "conan_toolchain.cmake"),
        ]
        for cand in candidates:
            if os.path.isfile(cand):
                return cand
        raise SystemExit("conan_toolchain.cmake not found in generators folder")

    def _cmake(self, src_dir, build_dir, extra_defs=None):
        toolchain = self._toolchain_file()
        staging = self._staging_dir()
        cfg = f"-DCMAKE_TOOLCHAIN_FILE={shlex.quote(toolchain)} " \
              f"-DCMAKE_INSTALL_PREFIX={shlex.quote(staging)} " \
              f"-DCMAKE_BUILD_TYPE={self.settings.build_type}"
        if extra_defs:
            cfg += " " + " ".join(f"-D{k}={shlex.quote(v)}" for k, v in extra_defs.items())
        self.run(f"cmake -S {shlex.quote(src_dir)} -B {shlex.quote(build_dir)} {cfg}")
        self.run(f"cmake --build {shlex.quote(build_dir)} -j$(nproc)")
        self.run(f"cmake --install {shlex.quote(build_dir)}")

    def build(self):
        # 1) 主源码补丁（0001 jsoncpp include 前缀；0002 find_package(JsonCpp
        #    CONFIG) + JsonCpp::JsonCpp + link_directories + AI_COMMON include +
        #    usr install DESTINATION . + SONAME；0003/0004 经 base_path 应用到
        #    vendor/kylin-ai-proto）
        apply_conandata_patches(self)
        # 2) 构建 vendor kylin-ai-proto → staging（INTERFACE + cmake 宏 + 协议 XML）
        proto_src = os.path.join(self.source_folder, "vendor", "kylin-ai-proto")
        self._cmake(proto_src, os.path.join(self.build_folder, "vendor-proto"))
        # 3) 主构建（顶层 add_library kysdk-genai-nlp SHARED；ENABLE_TEST 保持
        #    OFF —— 上游 tests/testGenAiNlp.cpp 是交互式程序（g_main_loop_run +
        #    std::getchar 等键盘输入）+ 依赖真实 AI 云服务认证，OHOS CI 无法运行，
        #    可运行测试见 test_package）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing installed ELFs")
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        for binary in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            with open(binary, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            if os.path.isfile(objcopy):
                self.run(
                    f"{shlex.quote(objcopy)} --remove-section .codesign "
                    f"{shlex.quote(binary)} 2>/dev/null || true"
                )
            self.run(shlex.join(
                [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"]
            ))
            try:
                os.chown(binary, os.getuid(), os.getgid())
                os.chmod(binary, 0o755)
            except OSError:
                pass

    def package_info(self):
        # 上游未导出 CMake config（仅 install lib/include/pc）；为下游 CMakeDeps
        # 消费方定义稳定的 find_package 名与 target（conan 侧生成，非上游产物）。
        self.cpp_info.set_property("cmake_file_name", "KysdkGenAiNlp")
        self.cpp_info.set_property("cmake_target_name", "KysdkGenAiNlp::KysdkGenAiNlp")
        self.cpp_info.set_property("pkg_config_name", "kysdk-genai-nlp")
        self.cpp_info.libs = ["kysdk-genai-nlp"]
        self.cpp_info.includedirs = ["include"]
