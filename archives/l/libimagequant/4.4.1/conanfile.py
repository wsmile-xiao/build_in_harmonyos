#!/usr/bin/env python3
"""Conan recipe — libimagequant 4.4.1 (Rust core, C API static library).

pngquant 的量化核心库：4x 版本上游已将实现迁移为 Rust（workspace:
imagequant lib + imagequant-sys C FFI staticlib），C 消费接口
libimagequant.h 保持不变（pngquant/GIMP 的链接形态）。

构建形态（上游 imagequant-sys/README.md "Building statically" 章节）:
    cargo build --release -p imagequant-sys
    → target/<triple>/release/libimagequant_sys.a
测试形态（上游 workspace）:
    cargo test --release --workspace --tests
    → 21 项全部真跑（lib 16 + ffi 4 + c_test 1；c_test 内部串跑
      test.c 的 5 个 C 断言函数）

工具链处理（rust-toolchain/1.97.1 + cbindgen 0.28.0 先例）：
- OHOS 宿主上 rust-toolchain 的 cargo/rustc 与 librustc_driver.so 需
  代码签名才能执行（HMDFS 执行标签限制）；openssl 3.5.6.1.1 归档
  relink 出私有 libssl.so/libcrypto.so 供 cargo 运行时。
- Cargo registry 走 rsproxy.cn 镜像（crates.io 直连超时）。
- C 侧链接器统一为 conan profile 的 clang（aarch64-unknown-linux-ohos）。
"""
import hashlib
import json
import os
import re
import shlex
import subprocess

import certifi
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs, cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

# 上游 workspace 测试规模（本地 rustc 1.97.1 aarch64-OHOS 实测全过）：
#   imagequant lib  单元测试 16 项（attr/pal/remap/rows/lib）
#   imagequant-sys  ffi 测试   4 项（imagequant-sys/src/ffi.rs）
#   c_test          C 集成     1 项（test.c 串跑 5 个断言函数）
UPSTREAM_TEST_DISCOVERED = 21
UPSTREAM_TEST_FRAMEWORK = "cargo-test"
UPSTREAM_TEST_COMMAND = "cargo test --release --workspace --tests --no-fail-fast"


class LibimagequantConan(ConanFile):
    name = "libimagequant"
    version = "4.4.1"
    description = "Palette quantization library that powers pngquant (Rust core, C API)"
    license = "GPL-3.0-or-later"
    homepage = "https://pngquant.org/lib/"
    url = "https://github.com/ImageOptim/libimagequant"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libimagequant requires Linux or OHOS, got {self.settings.os}")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"libimagequant 4.4.1 recipe targets armv8 (aarch64-unknown-linux-ohos), "
                f"got {self.settings.arch}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # Rust runtime（cbindgen 0.28.0 模式：签名私有拷贝 + openssl relink）
    # ------------------------------------------------------------------
    def _sign_tool(self):
        cc = self._cc()
        sign_tool = os.path.join(os.path.dirname(cc), "binary-sign-tool")
        if os.path.isfile(sign_tool):
            return sign_tool
        return None

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return (compilers.get("c")
                or os.environ.get("CC")
                or "clang")

    def _prepare_rust_runtime(self, env):
        """准备可执行的 cargo/rustc（OHOS 需签名）与 cargo 运行时 libssl。

        rust-toolchain 包内二进制在 HMDFS 上无执行标签（E046 同类），
        用 binary-sign-tool 对私有拷贝签名；librustc_driver*.so 同样处理。
        cargo 依赖 libssl.so/libcrypto.so（OPENSSL_3.0.0 符号），系统
        libssl 过旧，从 openssl conan 包的静态归档 relink 出私有 .so
        （cbindgen 0.28.0 同款方案）。
        """
        import shutil
        rust = self.dependencies.build["rust-toolchain"].package_folder
        openssl = self.dependencies.build["openssl"].package_folder
        runtime = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(runtime, exist_ok=True)

        sign_tool = self._sign_tool()
        cc = self._cc()

        # 1) openssl 静态归档 → 私有 libssl.so/libcrypto.so（cargo 运行时）
        from pathlib import Path
        for name in ("crypto", "ssl"):
            soname = f"lib{name}.so"
            dst = os.path.join(runtime, soname)
            if os.path.isfile(dst):
                continue
            matches = [str(p) for p in Path(openssl).rglob(f"lib{name}.a")]
            if not matches:
                raise ConanException(f"lib{name}.a not found in openssl package")
            cmd = [cc, "-shared", "-Wl,-z,relro,-z,now",
                   "-Wl,-soname," + soname,
                   "-Wl,--whole-archive", matches[0], "-Wl,--no-whole-archive",
                   "-ldl", "-pthread"]
            if name == "ssl":
                cmd += ["-L" + runtime, "-lcrypto"]
            cmd += ["-o", dst]
            self.run(shlex.join(cmd), env=["conanbuild", "liq_env"])

        # 2) 签名 cargo / rustc / librustc_driver 私有拷贝
        cargo = os.path.join(runtime, "cargo")
        rustc = os.path.join(runtime, "rustc")
        if not (os.path.isfile(cargo) and os.path.isfile(rustc)):
            if sign_tool is None:
                # 无签名工具：直接探测包内二进制是否可执行（Linux worker 可直接用）
                pkg_cargo = os.path.join(rust, "bin", "cargo")
                pkg_rustc = os.path.join(rust, "bin", "rustc")
                if os.access(pkg_cargo, os.X_OK) and os.access(pkg_rustc, os.X_OK):
                    return pkg_cargo, pkg_rustc, rust
                raise ConanInvalidConfiguration(
                    "binary-sign-tool unavailable and rust-toolchain binaries "
                    "not directly executable on this filesystem")
            for tool in ("cargo", "rustc"):
                src = os.path.join(rust, "bin", tool)
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", src,
                     "-outFile", os.path.join(runtime, tool), "-selfSign", "1"],
                    capture_output=True, timeout=300)
                if result.returncode or not os.path.isfile(os.path.join(runtime, tool)):
                    raise ConanException(
                        "signing %s failed: %s" % (
                            tool, result.stderr.decode(errors="replace")[-2000:]))
                os.chmod(os.path.join(runtime, tool), 0o755)
            # librustc_driver*.so 同样需要签名（rustc 的动态库依赖）
            for driver in os.listdir(os.path.join(rust, "lib")):
                if driver.startswith("librustc_driver") and driver.endswith(".so"):
                    src = os.path.join(rust, "lib", driver)
                    dst = os.path.join(runtime, driver)
                    if os.path.isfile(dst):
                        continue
                    result = subprocess.run(
                        [sign_tool, "sign", "-inFile", src,
                         "-outFile", dst, "-selfSign", "1"],
                        capture_output=True, timeout=300)
                    if result.returncode:
                        raise ConanException(
                            "signing %s failed: %s" % (
                                driver, result.stderr.decode(errors="replace")[-2000:]))
                    os.chmod(dst, 0o755)

        # 3) libc++_shared.so：driver NEEDED libc++_shared；OHOS 环境
        #    LD_LIBRARY_PATH 里的 /data/storage/el1/bundle/libs/arm64
        #    带了不兼容副本（Electron 应用自带），会把系统库遮蔽掉；
        #    且 HMDFS 拷贝的 .so 需签名才能被动态加载器加载。
        #    从 /system/lib64 取正确副本，签名后放 runtime（搜索最前）。
        libcxx = os.path.join(runtime, "libc++_shared.so")
        if not os.path.isfile(libcxx):
            import shutil
            source = None
            for candidate in ("/system/lib64/libc++_shared.so",
                              "/usr/lib/libc++_shared.so"):
                if os.path.isfile(candidate):
                    source = candidate
                    break
            if source is None:
                raise ConanInvalidConfiguration(
                    "libc++_shared.so not found on this system")
            if sign_tool is not None:
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", source,
                     "-outFile", libcxx, "-selfSign", "1"],
                    capture_output=True, timeout=300)
                if result.returncode:
                    raise ConanException(
                        "signing libc++_shared.so failed: %s" %
                        result.stderr.decode(errors="replace")[-2000:])
                os.chmod(libcxx, 0o755)
            else:
                shutil.copy2(source, libcxx)

        # 3) rustc sysroot：签名拷贝放 runtime/，通过符号链接树保持
        #    <sysroot>/bin/rustc 布局让 rustc 自行推导 sysroot（指向真实
        #    rustlib）。在 runtime 下建 bin/ 结构并把签名 rustc/cargo 挪进去。
        bin_dir = os.path.join(runtime, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        final_cargo = os.path.join(bin_dir, "cargo")
        final_rustc = os.path.join(bin_dir, "rustc")
        if not os.path.isfile(final_cargo):
            os.rename(cargo, final_cargo)
            os.rename(rustc, final_rustc)
        # lib → 真实 rust lib 的 rustlib 子目录（rustc 以 driver .so 的
        # 所在目录为 <sysroot>/lib 推 sysroot：签名 driver 放
        # runtime/lib/ 真实文件，rustlib 用目录符号链接挂进同一 lib/，
        # sysroot=runtime）
        lib_dir = os.path.join(runtime, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        rustlib_link = os.path.join(lib_dir, "rustlib")
        if not os.path.exists(rustlib_link):
            os.symlink(os.path.join(rust, "lib", "rustlib"), rustlib_link)
        # driver 从 runtime 根挪到 runtime/lib/（sysroot 推导依赖）
        for driver in os.listdir(runtime):
            if driver.startswith("librustc_driver") and driver.endswith(".so"):
                src = os.path.join(runtime, driver)
                dst = os.path.join(lib_dir, driver)
                if not os.path.exists(dst):
                    os.rename(src, dst)
        # 4) rustc sysroot 推导：rustc 以自身 exe 路径上两级为 sysroot
        #    （字面 dirname，不解析 ..），签名拷贝放 <runtime>/bin/、
        #    lib 符号链接放 <runtime>/lib，使 sysroot=runtime。
        #    注意 liq_env 脚本生成的路径含 conan/../../ 前缀会导致
        #    rustc 推导出错误 sysroot，故返回 realpath 归一后的路径。
        return (os.path.realpath(final_cargo),
                os.path.realpath(final_rustc), rust)

    def _rust_target(self):
        if str(self.settings.os) != "OHOS":
            return None
        return "aarch64-unknown-linux-ohos"

    def _write_environment(self):
        """生成 liq_env 脚本（cargo 运行时环境）。"""
        cc = self._cc()
        cxx = self.conf.get("tools.build:compiler_executables", default={}).get(
            "cpp", "clang++")
        cargo, rustc, rust = self._prepare_rust_runtime(None)
        target = self._rust_target()
        runtime = os.path.join(self.build_folder, "rust-runtime")

        env = Environment()
        # 清理可能干扰交叉构建的外部变量（cbindgen 同款清单）
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
                    "CARGO_BUILD_TARGET", "RUSTC_BOOTSTRAP", "RUSTUP_TOOLCHAIN"):
            env.unset(key)
        env.define("CARGO", cargo)
        env.define("RUSTC", rustc)
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("RUSTFLAGS", f"-C linker={cc}")
        if target:
            env.define(f"CARGO_TARGET_{target.upper().replace('-', '_')}_LINKER", cc)
        env.define("CARGO_HOME", os.path.join(self.build_folder, "cargo-home"))
        env.define("CARGO_TARGET_DIR", os.path.join(self.build_folder, "target"))
        env.define("CARGO_BUILD_JOBS", str(min(build_jobs(self), 2)))
        env.define("CARGO_NET_RETRY", "10")
        env.define("CARGO_HTTP_TIMEOUT", "600")
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        ca = certifi.where()
        env.define("CARGO_HTTP_CAINFO", ca)
        env.define("SSL_CERT_FILE", ca)
        env.define("CURL_CA_BUNDLE", ca)
        # cargo/rustc 运行时库搜索路径：relink openssl + libc++ 在
        # runtime 根，签名 driver 在 runtime/lib（sysroot 推导布局）
        env.prepend_path("LD_LIBRARY_PATH", runtime)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(runtime, "lib"))
        env.prepend_path("PATH", os.path.dirname(cargo))
        env.vars(self, scope=None).save_script("liq_env")

        # .cargo/config.toml：rsproxy 镜像 + linker + CA
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        config = (
            '[source.crates-io]\n'
            'replace-with = "rsproxy-sparse"\n'
            '[source.rsproxy-sparse]\n'
            'registry = "sparse+https://rsproxy.cn/index/"\n'
            '[net]\nretry = 10\n'
            '[http]\ntimeout = 600\ncainfo = "%s"\n' % ca
        )
        if target:
            config += f'\n[target.{target}]\nlinker = "{cc}"\n'
        with open(os.path.join(cargo_home, "config.toml"), "w", encoding="utf-8") as f:
            f.write(config)
        return cargo, rustc

    # ------------------------------------------------------------------
    # build()
    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        cargo, rustc = self._write_environment()
        target = self._rust_target()

        # 上游 tarball 不含 Cargo.lock（tag 归档未提交 lock），不能 --locked
        build_cmd = [cargo, "build", "--release", "-p", "imagequant-sys"]
        if target:
            build_cmd += ["--target", target]
        self.run(" ".join(shlex.quote(p) for p in build_cmd),
                 cwd=self.source_folder, env=["conanbuild", "liq_env"])

        # 上游测试在 test_package 阶段跑（HMBS 标记只在 test_package
        # stdout 被采集——tlsx/scooter 先例）；build() 只产库。

    def _static_lib(self):
        target = self._rust_target()
        if target:
            return os.path.join(self.build_folder, "target", target,
                                "release", "libimagequant_sys.a")
        return os.path.join(self.build_folder, "target", "release",
                            "libimagequant_sys.a")

    def package(self):
        lib = self._static_lib()
        if not os.path.isfile(lib):
            raise ConanException(f"build output not found: {lib}")
        copy(self, "libimagequant_sys.a", src=os.path.dirname(lib),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # 规范化包内库名为 libimagequant.a（上游 Makefile static 安装名）
        os.rename(os.path.join(self.package_folder, "lib", "libimagequant_sys.a"),
                  os.path.join(self.package_folder, "lib", "libimagequant.a"))
        copy(self, "libimagequant.h", src=os.path.join(self.source_folder, "imagequant-sys"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["imagequant"]
        self.cpp_info.set_property("pkg_config_name", "imagequant")
        # Rust std 线程运行时（rayon/thread_local 特性默认启用）
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
