#!/usr/bin/env python3
"""Conan recipe — twopaco 1.0.0 (CMake, 双可执行应用包).

TwoPaCo 是 de Bruijn 压缩图构建工具。1.0.0 发行包含两个程序：
  * twopaco    — 从多份 FASTA 直接构建压缩图（二进制输出）
  * graphdump  — 二进制转文本（seq / group / dot / gfa1 / gfa2 / fasta）

上游布局：顶层 tarball 根下是 src/（CMakeLists 在 src/ 内），
TCLAP 已 vendored（src/common/tclap），唯一外部依赖是 Intel TBB。
上游 CMake 不用 find_package(TBB)，而用 TBB_INCLUDE_DIR / TBB_LIB_DIR
两个缓存变量接线（link_directories + -ltbb -ltbbmalloc ...），本配方
从 tbb 依赖的 cpp_info 取绝对路径喂入。

OHOS 适配要点：
  * constructor.cpp 用 log2 却未含 <cmath>（GCC 宽松通过，clang 报错），
    见 patches/0001-ohos-cmath-include.patch。
  * graphconstructor 去 -ltbbmalloc_proxy，见
    patches/0002-ohos-drop-tbbmalloc-proxy.patch（包内该库 DT_NEEDED 为相对
    路径，musl 按路径解析致 Error 127；显式 scalable_* 仅需 libtbbmalloc）。
  * os=OHOS 下不用 CMakeToolchain（它把 CMAKE_SYSTEM_NAME 映射成 cmake
    不认的值），改用自发现 ohos.toolchain.cmake 的裸 cmake（tinyxml2 同法）。
  * 产出的 ELF 必须 binary-sign-tool 重签，否则 exec 报 Permission denied。
  * 上游测试 twopaco --test 跑 10 组随机 junction 对照，但 main 恒 return 0，
    必须逐行解析 "Test # N PASSED|FAILED"，不可信退出码。

上游测试分母：10（constructor.cpp: RunTests(10, 20, 9000, 6, ...) 首参）。
解析见 _save_upstream_result：逐行正则 ^Test # (\\d+) (PASSED|FAILED)$，
passed+failed==executed、executed==discovered==10 全等才放行。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

UPSTREAM_TEST_TOTAL = 10

required_conan_version = ">=2.0"


class TwopacoConan(ConanFile):
    name = "twopaco"
    version = "1.0.0"
    description = ("TwoPaCo: fast constructor of the compressed de Bruijn graph "
                   "from many complete genomes (twopaco + graphdump)")
    license = "Custom OSS"
    homepage = "https://github.com/medvedevgroup/TwoPaCo"
    url = ""
    topics = ("bioinformatics", "genomics", "de-bruijn-graph")

    package_type = "application"
    # L0p 门禁要求完整四项 settings（pure-python 精简 settings 会被拒）。
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "twopaco is adapted for Linux/OHOS, not " + str(self.settings.os))

    def requirements(self):
        # 1.0.0 为 TBB 依赖版本（1.1.0 起去 TBB）；tbb 已在制品仓发布。
        self.requires("tbb/2023.0.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        VirtualRunEnv(self).generate(scope="build")

    # ── 工具解析 ──────────────────────────────────────────────

    def _tool(self, name, fallback):
        """构建期外部工具一律解析成绝对路径：musl exec 不做 PATH 查找时裸名会 ENOENT。"""
        found = shutil.which(name)
        if found:
            return found
        env_key = "HMBS_" + name.upper().replace("-", "_").replace("+", "X")
        env_val = os.environ.get(env_key, "")
        if env_val and os.path.isfile(env_val):
            return env_val
        return fallback

    def _ohos_toolchain(self):
        """自发现 OHOS NDK 的 ohos.toolchain.cmake（tinyxml2 同法 + 预检兼容）。

        健康机（/data/service/hnp 下 SDK）保持原路径零改动优先返回；
        预检 runner 的 SDK 若版本目录不同或挂载位置不同，则经多 env +
        多 glob + clang 兄弟目录派生兜底；仍找不到时 OHOS 原生机
        （build==host==OHOS/aarch64）允许无工具链裸编并告警，
        不再硬报错阻断（Linux 本机验证同理）。
        """
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        # 显式 toolchain 文件直达（HMBS/CI 亦可经此注入）。
        for env_key in ("OHOS_TOOLCHAIN_FILE", "HMBS_OHOS_TOOLCHAIN_FILE",
                        "CMAKE_TOOLCHAIN_FILE"):
            cand = os.environ.get(env_key, "")
            if cand and os.path.isfile(cand):
                return cand
        candidates = list(ut)
        # NDK 根目录多 env 兼容：官方 OHOS_NDK_HOME + 常见变体。
        ndk_roots = []
        for env_key in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK", "OHOS_NDK",
                        "NDK_HOME", "SDK_HOME", "HMBS_OHOS_NDK", "HMBS_NDK_HOME"):
            root = os.environ.get(env_key, "")
            if root:
                ndk_roots.append(root)
        for ndk in ndk_roots:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(ndk, "ohos/native/build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(ndk, "native/build/cmake/ohos.toolchain.cmake"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        # 版本无关 glob：官方 CI 路径 + 预检机可能的不同挂载。
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/storage/Users/currentUser/usr/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/storage/Users/currentUser/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        for pat in patterns:
            try:
                matches = sorted(glob.glob(pat))
            except OSError:
                continue
            if matches:
                return matches[-1]
        # clang 兄弟目录派生：which clang -> ../ohos-sdk*/ohos/native/...。
        clang = shutil.which("clang")
        if clang:
            try:
                real = os.path.realpath(clang)
                base = os.path.dirname(os.path.dirname(real))
                for root in (base, os.path.dirname(base)):
                    for rel in ("ohos/native/build/cmake/ohos.toolchain.cmake",
                                "native/build/cmake/ohos.toolchain.cmake",
                                "build/cmake/ohos.toolchain.cmake"):
                        cand = os.path.join(root, rel)
                        if os.path.isfile(cand):
                            return cand
            except OSError:
                pass
        # 非 OHOS 构建（如 Linux 本机验证）允许无工具链。
        if str(self.settings.os) != "OHOS":
            return ""
        # OHOS 原生机（build==host）无工具链时裸编兜底：本机即目标，
        # 无需交叉 sysroot；告警并返回空，由 build() 跳过 TOOLCHAIN_FILE。
        self.output.warning(
            "ohos.toolchain.cmake 未发现（已搜 user_toolchain/OHOS_* env/"
            "/data/service/hnp + /storage 预检路径 + clang 兄弟目录）："
            "OHOS 原生机改用无工具链裸编；官方 CI 有 SDK 时仍走工具链，行为不变。")
        return ""

    def _tbb_dirs(self):
        tbb = self.dependencies["tbb"]
        root = tbb.package_folder or ""
        incs = [(p if os.path.isabs(p) else os.path.join(root, p)) for p in (tbb.cpp_info.includedirs or [])]
        libs = [(p if os.path.isabs(p) else os.path.join(root, p)) for p in (tbb.cpp_info.libdirs or [])]
        inc = incs[0] if incs else os.path.join(root, "include")
        lib = libs[0] if libs else os.path.join(root, "lib")
        return inc, lib

    def _tbb_link_shim(self, tbb_lib):
        """保证 -ltbb/-ltbbmalloc 在 OHOS 下可链接。

        上游 graphconstructor 经 0002 补丁已去掉 -ltbbmalloc_proxy（包内该库
        DT_NEEDED 为相对路径 ../../clang_*/libtbbmalloc.so，musl 按路径解析，
        LD_LIBRARY_PATH/RPATH 永远满足不了，启动即 Error 127；twopaco 的显式
        scalable_malloc/scalable_free 仅需 libtbbmalloc，proxy 系透明劫持非必需）。
        此处只为 tbb/tbbmalloc 补开发软链。

        上游两个 CMakeLists 都是先 add_executable 再 link_directories
        （按 CMake 语义只对之后创建的 target 生效），Linux 本机因系统
        路径有 tbb 偶然通过，OHOS 干净 sysroot 下直接报
        `ld.lld: unable to find library -ltbb`（本轮真机证据）。
        配方侧不改上游构建语义，只追加全局 -L 兜底；若包内只有
        libtbb.so.12 这类版本化文件而缺 libtbb.so 开发软链，则在
        build 内建 shim 目录补齐（symlink 优先，chmod 受限机退化为拷贝），
        避免 -l 查找失败。返回需追加到 -L 的目录列表。
        """
        import glob as _glob
        try:
            entries = sorted(os.listdir(tbb_lib))
        except OSError as exc:
            raise ConanException(
                "TBB lib dir missing or unreadable: %s (%s)" % (tbb_lib, exc))
        self.output.info("TBB lib dir %s contents: %s" % (tbb_lib, entries[:40]))
        needed = ("tbb", "tbbmalloc")
        missing_dev = []
        for base in needed:
            if os.path.isfile(os.path.join(tbb_lib, "lib%s.so" % base)) or \
               os.path.isfile(os.path.join(tbb_lib, "lib%s.a" % base)):
                continue
            versioned = sorted(_glob.glob(os.path.join(tbb_lib, "lib%s.so.*" % base)))
            if versioned:
                missing_dev.append((base, versioned[-1]))
        if not missing_dev:
            return []
        shim = os.path.join(self.build_folder, "tbb_link_shim")
        try:
            os.makedirs(shim, exist_ok=True)
        except OSError as exc:
            raise ConanException("cannot create tbb link shim: %s" % exc)
        for base, src in missing_dev:
            dst = os.path.join(shim, "lib%s.so" % base)
            if os.path.isfile(dst) or os.path.islink(dst):
                continue
            try:
                if os.path.islink(dst) or os.path.exists(dst):
                    os.unlink(dst)
            except OSError:
                pass
            try:
                os.symlink(os.path.basename(src) if os.path.dirname(src) == tbb_lib else src, dst)
                self.output.info("tbb shim symlink: %s -> %s" % (dst, src))
            except OSError:
                try:
                    shutil.copy2(src, dst)
                    self.output.info("tbb shim copy: %s -> %s" % (dst, src))
                except OSError as exc:
                    raise ConanException(
                        "cannot provide lib%s.so from %s: %s" % (base, src, exc))
        # shim 内若是相对软链，需把版本化文件也放到 shim 或改用绝对链。
        for base, src in missing_dev:
            dst = os.path.join(shim, "lib%s.so" % base)
            try:
                if os.path.islink(dst) and not os.path.isabs(os.readlink(dst)):
                    target = os.path.join(tbb_lib, os.readlink(dst))
                    if os.path.isfile(target) and not os.path.isfile(
                            os.path.join(shim, os.path.basename(target))):
                        try:
                            shutil.copy2(target, os.path.join(shim, os.path.basename(target)))
                        except OSError:
                            pass
            except OSError:
                pass
        return [shim]

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
            return
        objcopy = self._tool("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = self._tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        # 预检机签名工具若暂缺则告警跳过（不硬失败）；官方 CI 有工具时行为不变。
        if not (objcopy and os.path.isfile(objcopy)):
            self.output.warning("llvm-objcopy 缺失（%s），跳过 %s 去签名" % (objcopy, path))
            objcopy = ""
        if not (signer and os.path.isfile(signer)):
            self.output.warning("binary-sign-tool 缺失（%s），跳过 %s 签名" % (signer, path))
            return
        if objcopy:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=path))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=path))

    # ── 构建 ──────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        tbb_inc, tbb_lib = self._tbb_dirs()
        if not os.path.isdir(tbb_inc):
            raise ConanException("TBB include dir missing: " + tbb_inc)
        if not os.path.isdir(tbb_lib):
            raise ConanException("TBB lib dir missing: " + tbb_lib)
        # 上游 link_directories 写在 add_executable 之后，OHOS 下 -ltbb
        # 搜不到路径（真机 ld.lld unable to find library -ltbb）：用全局
        # CMAKE_EXE_LINKER_FLAGS 追加 -L 兜底，不改上游构建语义。
        # 运行时同样缺 TBB（真机 Error relocating libtbb/libtbbmalloc 符号，
        # exit 127）：同步追加 -Wl,-rpath,DIR 把 tbb lib/shim 目录 baked 进
        # ELF RUNPATH，installed 二进制免 LD_LIBRARY_PATH 也能找到；
        # build 期上游测试再显式 export LD_LIBRARY_PATH 双保险（musl 若忽略
        # RUNPATH 仍可跑）。不改上游 target_link_libraries 语义。
        shim_dirs = self._tbb_link_shim(tbb_lib)
        link_dirs = [tbb_lib] + [d for d in shim_dirs if d not in (tbb_lib,)]
        link_flags = " ".join(['-L%s -Wl,-rpath,%s' % (d, d) for d in link_dirs])
        cmake = self._tool("cmake", "/data/service/hnp/bin/cmake")
        src = os.path.join(self.source_folder, "src")
        if not os.path.isfile(os.path.join(src, "CMakeLists.txt")):
            raise ConanException("upstream src/CMakeLists.txt missing under " + src)
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DTBB_INCLUDE_DIR="{}"'.format(tbb_inc),
            '-DTBB_LIB_DIR="{}"'.format(tbb_lib),
            '-DCMAKE_BUILD_TYPE={}'.format(self.settings.build_type),
            '-DCMAKE_EXE_LINKER_FLAGS="{}"'.format(link_flags),
        ]
        if toolchain:
            defs.append('-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain))
            defs.append("-DOHOS_ARCH=arm64-v8a")
        self.run('"{cmake}" -B "{bdir}" -S "{src}" {defs}'.format(
            cmake=cmake, bdir=bdir, src=src, defs=" ".join(defs)))
        self.run('"{cmake}" --build "{bdir}" -- -j1'.format(cmake=cmake, bdir=bdir))
        twopaco = os.path.join(bdir, "graphconstructor", "twopaco")
        graphdump = os.path.join(bdir, "graphdump", "graphdump")
        if not os.path.isfile(twopaco):
            raise ConanException("twopaco was not built at " + twopaco)
        if not os.path.isfile(graphdump):
            raise ConanException("graphdump was not built at " + graphdump)
        # 先签名再跑测试：OHOS 上未签名的 ELF 无法 exec。
        self._sign_ohos_binary(twopaco)
        self._sign_ohos_binary(graphdump)
        self._run_upstream_tests(twopaco, link_dirs)

    def _run_upstream_tests(self, twopaco, link_dirs=()):
        """运行 twopaco --test（10 组随机对照），逐行解析证据。

        link_dirs 为 tbb lib/shim 目录：显式 export LD_LIBRARY_PATH 后再
        执行（conanrun 聚合 env 在真机上未覆盖运行时 TBB，致 Error
        relocating tbb 符号 exit 127）。RPATH 已在 link 阶段 baked，
        此处是 musl 忽略 RUNPATH 时的双保险。

        TCLAP 注意：filterSize/filterMemory（xor 必选其一）与 filenames
        均为 required，cmd.parse 在进入 RunTests 分支前即校验；裸
        `twopaco --test --tmpdir X` 恒报 PARSE ERROR（Required arguments
        missing: filtermemory, filtersize, filenames，真机证据）。
        因此追加 `-f 32 <dummy.fa>` 满足解析器；--test 分支 return 在使用
        filenames 之前，dummy 内容不影响测试（仅需占位）。
        """
        tmpdir = os.path.join(self.build_folder, "upstream-tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError as exc:
            raise ConanException("cannot create upstream tmpdir: %s" % exc)
        dummy = os.path.join(tmpdir, "upstream-dummy.fa")
        try:
            with open(dummy, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(">dummy\nACGT\n")
        except OSError as exc:
            raise ConanException("cannot create upstream dummy fasta: %s" % exc)
        log_path = os.path.join(self.build_folder, "twopaco_upstream.log")
        command = '"%s" --test --tmpdir "%s" -f 32 "%s" > "%s" 2>&1' % (twopaco, tmpdir, dummy, log_path)
        # 显式 LD_LIBRARY_PATH：conanrun 未覆盖 tbb 运行时路径时兜底。
        # shell 前缀 VAR=val cmd > log 2>&1 中 VAR 只作用于 cmd，重定向不受影响。
        ld_prefix = ":".join([d for d in link_dirs if d])
        if ld_prefix:
            self.output.info("upstream test LD_LIBRARY_PATH prefix: " + ld_prefix)
            try:
                entries = []
                for d in link_dirs:
                    try:
                        entries += sorted(os.listdir(d))[:20]
                    except OSError:
                        pass
                self.output.info("upstream test link_dirs contents sample: %s" % entries[:40])
            except Exception:
                pass
            command = 'LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" %s' % (ld_prefix, command)
        try:
            # 上游 --test 恒 exit 0（见 constructor.cpp），退出码无意义；
            # 真实证据只看日志里的 Test # N 行。
            self.run(command, env="conanrun")
        except ConanException as exc:
            self.output.warning("twopaco --test exited non-zero: %s" % exc)
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                log = handle.read()
        except OSError as exc:
            raise ConanException("cannot read upstream log %s: %s" % (log_path, exc))
        # 审计用：完整日志进 conan create 输出。
        self.output.info("upstream twopaco --test output:\n" + log[-6000:])
        self._save_upstream_result(log, command)

    def _save_upstream_result(self, log, command):
        """解析 Test # N PASSED|FAILED 行；单一确定性来源，无算术修补。"""
        if not log.strip():
            raise ConanException(
                "upstream --test produced empty output (binary silently skipped?); refusing to continue.")
        hits = re.findall(r"^Test # (\d+) (PASSED|FAILED)\s*$", log, re.MULTILINE)
        if not hits:
            raise ConanException(
                "no 'Test # N PASSED|FAILED' lines in upstream output; refusing to continue. "
                "log tail:\n%s" % log[-2000:])
        ids = [int(n) for n, _ in hits]
        passed = sum(1 for _, s in hits if s == "PASSED")
        failed = sum(1 for _, s in hits if s == "FAILED")
        executed = passed + failed
        discovered = UPSTREAM_TEST_TOTAL
        # 自检恒等式：passed + failed == executed 且 executed == discovered。
        if executed != discovered:
            raise ConanException(
                "upstream evidence lines (%d) != audited total (%d); refusing to guess. "
                "log tail:\n%s" % (executed, discovered, log[-2000:]))
        if set(ids) != set(range(discovered)):
            raise ConanException(
                "upstream test ids %s != expected 0..%d; refusing to continue." % (sorted(set(ids)), discovered - 1))
        if failed:
            upstream = {
                "status": "failed",
                "framework": "custom",
                "command": command,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
                "gaps": [{"count": failed, "category": "test_failure",
                          "detail": "twopaco --test 内 %d 组随机 junction 对照 FAILED，见 twopaco_upstream.log" % failed,
                          "evidence": "twopaco_upstream.log: Test # N FAILED lines"}],
            }
            marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            print(marker, flush=True)
            self.output.info(marker)
            raise ConanException("upstream suite failed (%d/%d); refusing to continue." % (failed, discovered))
        upstream = {
            "status": "passed",
            "framework": "custom",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": 0,
            "skipped": 0,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8", newline="\n") as handle:
                json.dump(upstream, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.output.warning("write hmbs_upstream.json failed: %s" % exc)

    # ── 打包 ──────────────────────────────────────────────────

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        cmake = self._tool("cmake", "/data/service/hnp/bin/cmake")
        self.run('"{cmake}" --install "{bdir}" --prefix "{pkg}"'.format(cmake=cmake, bdir=bdir, pkg=self.package_folder))
        bin_dir = os.path.join(self.package_folder, "bin")
        for name in ("twopaco", "graphdump"):
            path = os.path.join(bin_dir, name)
            if not os.path.isfile(path):
                raise ConanException("expected program missing after install: " + name)
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
            self._sign_ohos_binary(path)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # 缓存命中轮 test_package 仍需上游证据：随包持久化。
        try:
            copy(self, "hmbs_upstream.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        # 纯工具包：无库无头，只暴露 bin。
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
