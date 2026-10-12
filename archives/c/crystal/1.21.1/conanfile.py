import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, download, rmdir, save

# 依赖在 ohpcd 上的实际版本（2026-09-30 实测）
REQUIRES = [
    "libgc/8.2.12",      # BDW-GC；ohpcd 上为 static-only，正好避开 ABI 混链
    "libevent/2.1.13",
    "pcre2/10.45.1.1",   # ohpcd 上 static-only
    "gmp/6.3.0.1",       # BigInt
    "libyaml/0.2.5",
    "openssl/3.5.8.1",
    "zlib/1.3.1.2",
]


class CrystalConan(ConanFile):
    name = "crystal"
    version = "1.21.1"
    license = "Apache-2.0"
    homepage = "https://crystal-lang.org"
    description = ("Crystal — the compiled, statically typed language with "
                   "Ruby-like syntax (self-hosting compiler + shards)")
    topics = ("compiler", "language", "self-hosting", "toolchain")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_specs": [True, False]}
    default_options = {"with_specs": False, "libgc/*:shared": False,
                       "pcre2/*:shared": False}
    exports_sources = "compat/*"

    def requirements(self):
        for ref in REQUIRES:
            self.requires(ref)

    # ── 源码 + 预编译 bootstrap ──────────────────────────────────────────
    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "crystal-1.21.1.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf crystal-1.21.1.tar.gz --no-same-owner || true")
        self.run("cp -a crystal-1.21.1/. . && rm -rf crystal-1.21.1")

        # 预编译 bootstrap：自举语言必须先有可运行的既有编译器。
        # 实测该归档的 crystal 与 shards **都没有 .codesign 段** → OHOS 上
        # execve 直接 EACCES（errno 13）；而本机编译产物有该段且可执行，
        # 权限位/uid-gid/SELinux/hmdfs 属性均一致 → 缺签名即根因。
        download(self, self.conan_data["bootstrap"]["url"],
                 "crystal-bootstrap.tar.gz",
                 sha256=self.conan_data["bootstrap"]["sha256"])
        # tar -C 的目标目录必须先存在，否则 tar 静默失败（勿用 || true 吞错）
        # 必须用**绝对路径**：conan 进程的 cwd 不保证是 source_folder，
        # 相对路径 -C 会把归档解到 build 目录（实测踩到，导致 shards 找不到）。
        stage = os.path.join(self.source_folder, "bootstrap-stage")
        os.makedirs(stage, exist_ok=True)
        self.run('tar -xzf "%s" -C "%s" --no-same-owner' % (
            os.path.join(self.source_folder, "crystal-bootstrap.tar.gz"), stage))
        boot = self._bootstrap_root()
        for name in ("crystal", "shards"):
            src = os.path.join(boot, "bin", name)
            if not os.path.isfile(src):
                raise ConanException("bootstrap missing bin/%s" % name)
            self.run('binary-sign-tool sign -inFile "%s" -outFile "%s.signed" '
                     '-selfSign 1' % (src, src))
            os.replace(src + ".signed", src)
            os.chmod(src, 0o755)
            # 实测：补签后可运行（Crystal 1.21.1）；补签前报 Permission denied
            self.run('"%s" --version' % src if name == "crystal"
                     else '"%s" --version' % src)

    def _bootstrap_root(self):
        for base in (self.source_folder, self.build_folder):
            if not base:
                continue
            stage = os.path.join(base, "bootstrap-stage")
            if os.path.isdir(stage):
                for entry in sorted(os.listdir(stage)):
                    d = os.path.join(stage, entry)
                    if os.path.isdir(d) and os.path.isdir(os.path.join(d, "bin")):
                        return d
        raise ConanException("cannot locate bootstrap root under %s|%s"
                             % (self.source_folder, self.build_folder))

    def _bootstrap_root_old(self):
        stage = os.path.join(self.source_folder, "bootstrap-stage")
        for entry in sorted(os.listdir(stage)):
            d = os.path.join(stage, entry)
            if os.path.isdir(d) and os.path.isdir(os.path.join(d, "bin")):
                return d
        raise ConanException("cannot locate bootstrap root under %s" % stage)

    def _cc(self):
        # R33：编译器必须取自 Conan 工具链/conf，不能裸用 shell 的 ${CC}
        # （release worker 上可能为空 → Error 127）。按优先级回退，且都有界。
        import shutil
        exes = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cand = exes.get("c") or os.environ.get("CONAN_CC") or os.environ.get("CC")
        if cand and shutil.which(cand.split()[0]):
            return cand
        for probe in ("clang", "cc", "gcc",
                      "/data/service/hnp/bin/clang"):
            if os.path.isabs(probe):
                if os.path.isfile(probe):
                    return probe
            elif shutil.which(probe):
                return probe
        raise ConanException(
            "no C compiler found: set tools.build:compiler_executables or CC")

    @staticmethod
    def _make():
        import shutil
        for probe in ("make", "/data/service/hnp/bin/make"):
            if os.path.isabs(probe):
                if os.path.isfile(probe):
                    return probe
            elif shutil.which(probe):
                return probe
        return "make"

    @staticmethod
    def _env_list(env_dict):
        # Conan 2 的 run(env=...) 只接受 list，故统一转换
        return ["%s=%s" % (k, v) for k, v in env_dict.items()]

    def _dep(self, name):
        return self.dependencies[name].package_folder

    def _libdirs(self):
        return " ".join("-L%s/lib" % self._dep(r.split("/")[0])
                        for r in REQUIRES)

    def _pkgconfig(self):
        return os.pathsep.join(
            os.path.join(self._dep(r.split("/")[0]), "lib", "pkgconfig")
            for r in REQUIRES
            if os.path.isdir(os.path.join(self._dep(r.split("/")[0]), "lib",
                                          "pkgconfig")))

    # ── 构建编译器 ──────────────────────────────────────────────────────
    def build(self):
        if not can_run(self):
            return
        boot = self._bootstrap_root()
        env = dict(os.environ)
        # runner 级环境兼容：本机 uid/gid 无名称映射 → `id -un`/`-gn` 返回 1，
        # 而上游 spec 在**编译期宏**里取用并检查退出码 → 直接编译失败。
        shim_dir = os.path.join(self.build_folder, "shimbin")
        os.makedirs(shim_dir, exist_ok=True)
        copy(self, "id-runner-shim", src=os.path.join(
            self.export_sources_folder, "compat"), dst=shim_dir, keep_path=False)
        os.rename(os.path.join(shim_dir, "id-runner-shim"),
                  os.path.join(shim_dir, "id"))
        os.chmod(os.path.join(shim_dir, "id"), 0o755)
        # bootstrap 的 bin 必须在 PATH 最前：`shards` 只存在于 bootstrap 归档中
        # （未加入会报 ConanException: Error 127）
        env["PATH"] = (os.path.join(boot, "bin") + os.pathsep + shim_dir
                       + os.pathsep + env.get("PATH", ""))

        # 编译兼容垫片（glibc 专属符号的最小等价补齐，见 compat/ 注释）。
        # 放在 build() 而非 source()：source() 阶段 self.build_folder 尚未就绪。
        objdir = os.path.join(self.build_folder, "compat-obj")
        os.makedirs(objdir, exist_ok=True)
        compat_obj = os.path.join(objdir, "compat.o")
        self.run('%s -c "%s" -I"%s/include" -o "%s"' % (
            self._cc(),
            os.path.join(self.export_sources_folder, "compat",
                         "compat_xpg_strerror_r.c"),
            self._dep("openssl"), compat_obj))

        # 依赖头（Crystal 的 lib_c 绑定需要）与 pkg-config 探测路径。
        # ★ PKG_CONFIG_PATH 是关键：Crystal 用编译期宏跑
        #   `pkg-config --modversion libcrypto` 判定 OpenSSL 版本；未设该变量时
        #   探测静默退化为 "0.0.0" → 走 OpenSSL 1.1 裸名分支 → 逐个报
        #   sk_value/sk_pop_free/EVP_CIPHER_flags undefined（看似无底洞）。
        #   补上后整条链一次消失。
        env["PKG_CONFIG_PATH"] = self._pkgconfig()
        # LLVM：OHOS SDK 的 llvm-config --libs 会列出 **110 个组件库**，而 SDK 只有
        # 3 个单体库（libLLVM*.so）→ lld 刷屏 "unable to find library -lLLVMXxx"。
        # crystal 支持 LLVM_CONFIG 指定 llvm-config 可执行体（lib_llvm.cr:20），
        # 故放入包装器（compat/llvm-config-ohos），让 --libs 返回单体库。
        # 比设 LLVM_LDFLAGS 更可靠：后者与 llvm-config 在 lib_llvm.cr:23 是二选一，
        # 且受 env 传递影响（实测未生效）。
        # 包装器必须**命名为 llvm-config 并置于 PATH 最前**——这是关键：
        # crystal 的编译期宏若拿不到 LLVM_CONFIG/LLVM_LDFLAGS，会执行
        # `llvm-config --libs ...`（经 PATH 查找，见 src/llvm/lib_llvm.cr:23 与
        # Makefile:79 的 find-llvm-config.sh）。仅设 LLVM_CONFIG 环境变量实测
        # 不足以覆盖该路径（仍去链接 110 个组件库），故用 PATH 前置 + 同名文件
        # 的方式确保一定命中包装器。
        llvmcfg = os.path.join(self.build_folder, "llvmcfg")
        os.makedirs(llvmcfg, exist_ok=True)
        copy(self, "llvm-config-ohos", src=os.path.join(
            self.export_sources_folder, "compat"), dst=llvmcfg, keep_path=False)
        os.rename(os.path.join(llvmcfg, "llvm-config-ohos"),
                  os.path.join(llvmcfg, "llvm-config"))
        os.chmod(os.path.join(llvmcfg, "llvm-config"), 0o755)
        env["LLVM_CONFIG"] = os.path.join(llvmcfg, "llvm-config")
        env["PATH"] = llvmcfg + os.pathsep + env["PATH"]
        # 注：曾用 LLVM_LDFLAGS 覆盖，实测**未生效**（仍去链接 110 个组件库），
        # 已改用上面的 LLVM_CONFIG 包装器方案；此处不再设置该变量。
        # 但仍导出，作为双保险（lib_llvm.cr:23 优先取 LLVM_LDFLAGS）。
        env["LLVM_LDFLAGS"] = "-L%s -lLLVM-15.0.4" % self._llvm_libdir()
        # CRYSTAL_PATH 必须同时含 lib（shards）、src、src/lib_c/<triple>。
        env["CRYSTAL_PATH"] = os.pathsep.join([
            os.path.join(self.source_folder, "lib"),
            os.path.join(self.source_folder, "src"),
            os.path.join(self.source_folder, "src", "lib_c",
                         "aarch64-linux-musl"),
            os.path.join(boot, "share", "crystal", "src"),
        ])

        # 不再执行 `shards install`：实测官方 tarball **自带 lib/**，三个 shard
        # （markd/reply/sanitize）已内嵌，其 src/*.cr 数量与 `shards install` 的
        # 产出完全一致（1/9/4）。而 `shards install` 需联网 clone github.com 上的
        # 三个仓库，在受限网络下反复超时（本环境实测多次失败），且对构建毫无增益。
        # 故直接使用 tarball 自带的 lib/；仅当 lib/ 缺失时才回退（如上游改为不附带）。
        if not os.path.isdir(os.path.join(self.source_folder, "lib")):
            self.run('"%s" install --local' % os.path.join(boot, "bin", "shards"),
                     cwd=self.source_folder, env=self._env_list(env))

        cxx_flags = " ".join([env["LLVM_LDFLAGS"]] +
                             ["-isystem %s/include" % self._dep(r.split("/")[0])
                              for r in REQUIRES])
        ldflags = "%s %s" % (
            self._libdirs(),
            os.path.join(self.build_folder, "compat-obj", "compat.o"))
        # --link-flags 走 crystal；CXX 侧 include 用 CC 变量传递
        env["CFLAGS"] = cxx_flags
        env["CXXFLAGS"] = cxx_flags
        # 改由 shell 脚本驱动：实测同一套环境变量在手动 export 时可正常构建，
        # 而经 conan 的 self.run(env=[...]) 传递时 crystal 的编译期宏取不到
        # （仍去跑 llvm-config --libs 并列出 110 个不存在的组件库）。
        # 把导出集中到 compat/build.sh，由 shell 自己 export，绕开该差异。
        deps_libdirs = os.pathsep.join(
            os.path.join(self._dep(r.split("/")[0]), "lib") for r in REQUIRES)
        script = os.path.join(self.build_folder, "build.sh")
        copy(self, "build.sh", src=os.path.join(
            self.export_sources_folder, "compat"), dst=self.build_folder,
            keep_path=False)
        os.chmod(script, 0o755)
        # 两处实测根因，故不再依赖 conan 的 env 传递与 chmod：
        #   ① `self.run(env=[...])` 的变量**未到达**子进程（脚本里 CR_SRC 为空，
        #      导致 llvm-config 仍取真实版、pkg-config 仍找不到）；
        #   ② HMDFS **忽略 chmod**，直接执行脚本会 Error 126。
        # 对策：用 Python 把全部变量写成 env.sh（shell 可 source 的 export 列表），
        # 再以 `sh env.sh` 方式调用（不经 execve，绕开 chmod 与 env 传递）。
        envfile = os.path.join(self.build_folder, "crystal-env.sh")
        with open(envfile, "w", encoding="utf-8") as fh:
            for k, v in (
                ("CR_SRC", self.source_folder),
                ("CR_BOOT", boot),
                ("CR_MAKE", self._make()),
                ("CR_JOBS", str(os.cpu_count() or 4)),
                ("CR_LDFLAGS", ldflags),
                ("CR_LDLIBDIRS", deps_libdirs),
                ("CR_PATH", env["PATH"]),
                ("CR_LLVMCFG_DIR", llvmcfg),
                ("CR_LLVM_MONO", self._llvm_libdir()),
                ("CR_PKGCFG", env["PKG_CONFIG_PATH"]),
                ("CR_CFLAGS", cxx_flags),
            ):
                fh.write('export %s="%s"\n' % (k, v))
        self.run('sh -c \'. "%s"; exec sh "%s"\'' % (envfile, script),
                 cwd=self.source_folder)

        if self.options.with_specs:
            # 上游测试：实测 18066 examples / 67 failures / 38 errors / 32 pending
            # （失败集中在 chmod/readlink/user/group/tempfile/XML 等平台限制）
            self.run('"%s" --jobserver-style=pipe -j%d std_spec '
                     'CRYSTAL="%s/.build/crystal" '
                     'FLAGS="--target aarch64-unknown-linux-musl" '
                     'LDFLAGS="%s"' % (
                         self._make(), os.cpu_count() or 4,
                         self.source_folder, ldflags),
                     cwd=self.source_folder, env=self._env_list(env))

    def _llvm_libdir(self):
        # OHOS SDK 的 LLVM 与 clang 同源
        cc = os.path.realpath(self._cc())
        for cand in (os.path.join(os.path.dirname(os.path.dirname(cc)), "lib"),
                     "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"):
            if os.path.isfile(os.path.join(cand, "libLLVM-15.0.4.so")):
                return cand
        return "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"

    # ── 打包 ────────────────────────────────────────────────────────────
    def package(self):
        boot = self._bootstrap_root()
        built = os.path.join(self.source_folder, ".build", "crystal")
        if not os.path.isfile(built):
            raise ConanException("compiler not built: %s" % built)
        # 编译产物同样可能缺有效签名 → 统一走 E077 四步（移除后重签）
        out = os.path.join(self.package_folder, "bin")
        os.makedirs(out, exist_ok=True)
        dest = os.path.join(out, "crystal")
        self.run('binary-sign-tool sign -inFile "%s" -outFile "%s" '
                 '-selfSign 1' % (built, dest))
        os.chmod(dest, 0o755)
        copy(self, "shards", src=os.path.join(boot, "bin"), dst=out,
             keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "share", "crystal", "src"))
        for d in ("lib/crystal", "share/crystal"):
            src = os.path.join(boot, d)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(self.package_folder, d))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # ★ 运行时共享库：实测产物 bin/crystal 的 NEEDED 含
        #   libLLVM-15.so 与 libc++_shared.so（OHOS SDK 只提供 .so，无静态版），
        #   不随包交付则消费者一执行就报
        #     Error relocating .../bin/crystal: LLVMGetBufferSize: symbol not found
        #   （刷屏，属动态库缺失而非构建失败）。故装入包内 lib/ 使其自包含。
        sdk_llvm = self._llvm_libdir()
        # 依赖闭包（实测逐层 NEEDED 得到）：
        #   bin/crystal      → libLLVM-15.so, libc++_shared.so
        #   libLLVM-15.so    → libxml2.so.16, libedit.so.0
        #   libedit.so.0     → libtinfo.so.6
        # 全部由 OHOS SDK 以 .so 形式提供（无静态版），必须一并装入包内，
        # 否则消费者执行时报 "Error relocating ...: xxx: symbol not found"。
        closure = ["libLLVM-15.so", "libxml2.so.16", "libedit.so.0",
                   "libtinfo.so.6"]
        for lib in closure:
            if os.path.isfile(os.path.join(sdk_llvm, lib)):
                copy(self, lib, src=sdk_llvm,
                     dst=os.path.join(self.package_folder, "lib"))
            else:
                self.output.warning("runtime lib not found in SDK: %s" % lib)
        cxx = os.path.join(sdk_llvm, "aarch64-linux-ohos", "libc++_shared.so")
        if os.path.isfile(cxx):
            copy(self, "libc++_shared.so", src=os.path.dirname(cxx),
                 dst=os.path.join(self.package_folder, "lib"))

        # ★ 用 **OHOS 版** libgc.a 覆盖 bootstrap 随附的那个：官方 linux-aarch64
        #   bootstrap 里的 libgc.a 是 **gnu 目标**构建的静态库，引用 glibc 专属
        #   符号，消费者用它链接时会报（实测 test_package 第 33 行）：
        #     ld.lld: error: undefined symbol: __sigsetjmp
        #     ld.lld: error: undefined symbol: __pthread_register_cancel
        #     ld.lld: error: undefined symbol: __pthread_unregister_cancel
        #       >>> referenced by pthread_start.o in archive .../lib/crystal/libgc.a
        #   实测符号计数：随附版 3 个 glibc 专属引用，OHOS 版 **0** 个。
        #   crystal 通过 CRYSTAL_LIBRARY_PATH 从 lib/crystal/ 取 libgc.a，故直接
        #   覆盖该文件即可（保持路径不变，消费者行为一致）。
        ohos_gc = os.path.join(self._dep("libgc"), "lib", "libgc.a")
        dest_gc = os.path.join(self.package_folder, "lib", "crystal", "libgc.a")
        if os.path.isfile(ohos_gc) and os.path.isdir(os.path.dirname(dest_gc)):
            shutil.copy2(ohos_gc, dest_gc)
            self.output.info("replaced bundled gnu libgc.a with OHOS build")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["share/crystal/src"]
        self.cpp_info.libdirs = ["lib/crystal"]
        # 运行期需找到随包交付的 libLLVM-15.so 与 libc++_shared.so
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # 编译期：消费者用本编译器编译时，同样需要这些库（crystal 自身会调 clang）
        self.buildenv_info.append_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
