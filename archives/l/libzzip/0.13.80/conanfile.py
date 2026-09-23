#!/usr/bin/env python3
"""Conan recipe — libzzip 0.13.80 (zziplib, cmake)"""
import contextlib
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.cmake import cmake_layout


class LibzzipConan(ConanFile):
    name = "libzzip"
    version = "0.13.80"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        # filename 落盘名带 .tar.gz 后缀: codeload URL 路径末段无扩展名,
        # conan 按扩展名识别压缩格式, 否则误当 zip → BadZipFile
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="zziplib-0.13.80.tar.gz")

    def export_sources(self):
        # conandata patches 为空, 但 CI G1 门禁要求配方具备该方法; 与 aa audit/abc
        # 等无补丁配方保持一致的标准写法 (patches 有内容时由该方法导出)
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    # ── OHOS SDK 链接器宿主运行时 (lld / libxml2.so.16) ──────────────
    #
    # 线上 CI (PR #7530) 根因: SDK 的 clang 驱动在最终链接时拉起 lld,
    # lld 是动态链接的宿主 ELF, NEEDED 里有 libxml2.so.16 (正常应经其
    # RUNPATH $ORIGIN/../lib 解析到 SDK 的 llvm/lib, CI worker 加载器不展开),
    # 于是 lld 连启动都失败:
    #   Error loading shared library libxml2.so.16:
    #   (needed by .../ohos/native/llvm/bin/lld)
    # 这是 SDK 工具自身的宿主运行时问题, 不是 zlib/源码/平台识别问题。
    # 修复 (同 ls-hpack 2.3.5 已验证实现): cmake configure 之前先做真实
    # compile+link probe; 环境失败时动态定位含缺失库的工具链目录, 仅在
    # build() 作用域内给 LD_LIBRARY_PATH 前置恢复。不做任何 CMake 绕过
    # (不设 CMAKE_C_COMPILER_WORKS / 不跳过编译器检查)。
    # 注意 musl 陷阱: 加载失败时 stderr 报 Error loading/relocating 但
    # 退出码可能仍是 0 → probe 不能只看 rc, 须同时匹配 stderr 模式。

    _MISSING_LIB_PATTERNS = (
        # musl: "Error loading shared library libxml2.so.16: (needed by ...)"
        re.compile(r'error loading shared library ([^\s:]+)', re.IGNORECASE),
        # glibc: "...: error while loading shared libraries: libxml2.so.16"
        re.compile(r'error while loading shared libraries: ([^\s:]+)', re.IGNORECASE),
        # glibc: "libxml2.so.16: cannot open shared object file: ..."
        re.compile(r'([^\s:]+): cannot open shared object file', re.IGNORECASE),
    )
    _HOST_LOADER_MARKERS = (
        'error loading shared library',
        'error while loading shared libraries',
        'cannot open shared object file',
        'error relocating',
        'symbol not found',
    )

    def _get_cc(self):
        # 编译器以 Conan conf 为准 (OHOS profile [conf] 的权威来源, 指向 SDK
        # clang); 路径不存在时仅回退 basename+PATH 解析, 绝不硬编码工具链路径。
        compilers = self.conf.get(
            'tools.build:compiler_executables', default={}, check_type=dict)
        cc = compilers.get('c')
        if not cc:
            return shutil.which('clang') or 'clang'
        if os.path.isfile(cc):
            return cc
        return shutil.which(os.path.basename(cc)) or cc

    def _resolve_lld(self, cc):
        # clang 驱动最终链接时实际调用的链接器, 从工具链自身推导:
        # 先问驱动 (-print-prog-name=ld.lld), 再查编译器真实 bin 目录, 最后 PATH。
        candidates = []
        try:
            proc = subprocess.run(
                [cc, '-print-prog-name=ld.lld'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False)
            if proc.returncode == 0 and proc.stdout.strip():
                candidates.append(proc.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
        bin_dir = os.path.dirname(os.path.realpath(cc))
        candidates += [os.path.join(bin_dir, 'ld.lld'),
                       os.path.join(bin_dir, 'lld')]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return os.path.realpath(candidate)
            resolved = shutil.which(candidate)
            if resolved:
                return os.path.realpath(resolved)
        return ''

    def _missing_host_libs(self, log):
        # 从 probe 日志提取缺失宿主库文件名 (如 libxml2.so.16) — 候选目录须实际含它
        libs = []
        for pattern in self._MISSING_LIB_PATTERNS:
            libs += pattern.findall(log or '')
        return [lib for lib in dict.fromkeys(libs) if '.so' in lib]

    def _is_host_loader_failure(self, log):
        lowered = (log or '').lower()
        return any(marker in lowered for marker in self._HOST_LOADER_MARKERS)

    def _host_runtime_libdirs(self, cc, lld, missing_libs):
        """候选宿主运行时目录, 只从当前工具链与环境推导 (优先级同 ls-hpack):
          1. 配置编译器的真实 LLVM 树
          2. 解析出 lld 的真实 LLVM 树
          3. 编译器 resource-dir 树 (clang -print-resource-dir)
          4. PATH 中的工具目录
          5. 当前 LD_LIBRARY_PATH
          6. 从工具链二进制向上的有界回溯
        只返回实际包含缺失库的目录 (日志未点名库时, 接受确实放着共享库的
        工具链目录 — 覆盖纯符号重定位失败)。
        """
        candidates = []
        for tool in (cc, lld):
            if tool and os.path.sep in tool:
                llvm_root = os.path.dirname(
                    os.path.dirname(os.path.realpath(tool)))
                candidates.append(os.path.join(llvm_root, 'lib'))
        try:
            proc = subprocess.run(
                [cc, '-print-resource-dir'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False)
            if proc.returncode == 0 and proc.stdout.strip():
                # <prefix>/lib/clang/<ver> → <prefix>/lib
                candidates.append(
                    os.path.dirname(os.path.dirname(proc.stdout.strip())))
        except (OSError, subprocess.SubprocessError):
            pass
        candidates += [
            p for p in (os.environ.get('PATH') or '').split(os.pathsep) if p
        ]
        candidates += [
            p for p in (os.environ.get('LD_LIBRARY_PATH') or '').split(os.pathsep)
            if p
        ]
        # 从工具链二进制向上回溯 (覆盖经符号链接 wrapper 目录达成的 SDK 布局)
        for tool in (lld, cc):
            if not tool or os.path.sep not in tool:
                continue
            node = os.path.dirname(os.path.realpath(tool))
            for _ in range(4):
                node = os.path.dirname(node)
                if node in ('', os.path.sep):
                    break
                candidates.append(os.path.join(node, 'lib'))
                candidates.append(os.path.join(node, 'llvm', 'lib'))
        found = []
        for candidate in dict.fromkeys(candidates):
            if not os.path.isdir(candidate):
                continue
            if missing_libs:
                if any(os.path.isfile(os.path.join(candidate, lib))
                       for lib in missing_libs):
                    found.append(candidate)
                continue
            try:
                entries = os.listdir(candidate)
            except OSError:
                continue
            if any('.so' in entry for entry in entries):
                found.append(candidate)
        return found

    def _cc_link_probe(self, cc, extra_ld_library_path=None):
        """真实 compile+link probe: 用配置的 OHOS clang 编译并链接
        `int main(void) { return 0; }`。裸 `clang --version` 不够 —
        CMake 编译器检查既要编译 testCCompiler.c 又要链接它, 链接一步
        正是 lld 载入 libxml2.so.16 失败时挂掉的地方。
        返回 (returncode, 合并输出)。musl 下加载错误 rc 可能为 0,
        故输出里也要能识别失败模式 (见 _probe_failed)。
        """
        probe_dir = os.path.join(self.build_folder, 'linker-probe')
        os.makedirs(probe_dir, exist_ok=True)
        source = os.path.join(probe_dir, 'probe.c')
        binary = os.path.join(probe_dir, 'probe')
        with open(source, 'w') as fh:
            fh.write('int main(void) { return 0; }\n')
        env = os.environ.copy()
        if extra_ld_library_path:
            current = env.get('LD_LIBRARY_PATH', '')
            env['LD_LIBRARY_PATH'] = os.pathsep.join(
                p for p in (extra_ld_library_path, current) if p)
        try:
            proc = subprocess.run(
                [cc, source, '-o', binary],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, timeout=180, check=False)
        except (OSError, subprocess.SubprocessError) as error:
            return 127, str(error)
        finally:
            if os.path.exists(binary):
                try:
                    os.unlink(binary)
                except OSError:
                    pass
        return proc.returncode, (proc.stdout or '').strip()

    def _probe_failed(self, rc, log):
        # musl 陷阱: 动态库加载失败时 rc 可能仍为 0, 但 stderr 有失败标记
        return rc != 0 or self._is_host_loader_failure(log)

    def _linker_runtime_environment(self):
        """configure 之前的链接器宿主运行时门禁 (线上 CI PR #7530)。
        1) 环境原样先跑真实 compile+link probe (通过 → 不动环境);
        2) 失败且属宿主动态库问题 → 从工具链推导含缺失库的候选目录,
           逐个前置到 LD_LIBRARY_PATH 重跑 probe;
        3) 赢家目录作为 Conan Environment 返回, 只在 build() 作用域应用,
           绝不全局改 os.environ; 其余情况一律带着完整诊断 fail-closed。
        """
        if str(self.settings.os) != 'OHOS':
            return None

        cc = self._get_cc()
        lld = self._resolve_lld(cc)
        self.output.info(f'OHOS linker probe: clang={cc}')
        self.output.info(f'OHOS linker probe: lld={lld or "(unresolved)"}')

        # 1) 原样环境: 配置的 clang 能否编译+链接?
        rc, log = self._cc_link_probe(cc)
        if not self._probe_failed(rc, log):
            self.output.info(
                'OHOS linker probe: minimal C compile+link OK '
                '(ambient environment)')
            return None

        # 2) 链接失败 — 仅宿主动态库失败可用 LD_LIBRARY_PATH 恢复,
        #    其他失败立即 fail-closed
        missing_libs = self._missing_host_libs(log)
        if not self._is_host_loader_failure(log):
            raise ConanException(
                'OHOS linker probe: 配置的 C 编译器 \'{cc}\' 无法在当前'
                '环境编译+链接最小程序, 且失败不是宿主动态库问题 '
                '(lld={lld})。Probe 输出:\n{log}'.format(
                    cc=cc, lld=lld or 'unresolved', log=log or '(empty)'))

        missing = ', '.join(missing_libs) or 'unidentified library'
        self.output.warning(
            f'OHOS linker probe: 最小 C compile+link 在原样环境失败 '
            f'(rc={rc}); 正在定位 SDK 宿主运行时 ({missing}) ...')
        if log:
            self.output.info(f'OHOS linker probe output:\n{log}')
        candidates = self._host_runtime_libdirs(cc, lld, missing_libs)
        if not candidates:
            raise ConanException(
                'OHOS linker probe: 配置的 C 编译器 \'{cc}\' 无法编译+链接'
                '最小程序, 且无法从当前工具链推导出包含 {missing} 的目录 '
                '(lld={lld})。Probe 输出:\n{log}'.format(
                    cc=cc, missing=missing, lld=lld or 'unresolved',
                    log=log or '(empty)'))
        for libdir in candidates:
            rc, log = self._cc_link_probe(cc, extra_ld_library_path=libdir)
            if not self._probe_failed(rc, log):
                self.output.info(
                    'OHOS linker probe: minimal C compile+link OK with '
                    f'{libdir} prepended to LD_LIBRARY_PATH')
                env = Environment()
                env.prepend_path('LD_LIBRARY_PATH', libdir)
                return env
        raise ConanException(
            'OHOS linker probe: 配置的 C 编译器 \'{cc}\' 即使加上发现的'
            '宿主运行时也无法编译+链接最小程序。缺失库: {missing}; '
            'lld={lld}; 尝试过的候选目录: {cands}。最后一次 probe 输出:'
            '\n{log}'.format(
                cc=cc, missing=missing, lld=lld or 'unresolved',
                cands=', '.join(candidates), log=log or '(empty)'))

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        # ④ 都没有 → 返回 None：构建机本身就是 OHOS PC（本仓库 CI 即此形态），PATH 上的
        #   clang 即原生 OHOS clang（aarch64-unknown-linux-ohos），裸 cmake 原生构建即可，
        #   无交叉、无需 toolchain 文件（实测 cmake 仅报 "System is unknown" 警告）。
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        return None

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下**只有 llvm-ar，没有 llvm-ranlib**，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去。cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，
        # 于是 .o 全编得动、一造 .a 就 ENOENT，且报错**不说是哪个程序**找不到：
        #   Error running link command: no such file or directory
        # 实证：OpenCV 4.12.0、SuiteSparse 7.8.3。返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""                            # SDK 有就不用管
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到。**不能靠 -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH**：
        # ohos.toolchain 用普通 set()（非 CACHE）设了 ONLY，普通变量盖得住命令行 cache 变量，
        # 实测加了照样失败。CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 toolchain 之后、project() 之后、
        # 第一个 find_package 之前执行，这时改才压得住。
        #
        # 只给了顶层 <Pkg>_DIR 是不够的——依赖自己的 config 里还会做**嵌套 find_package**，
        # 那一层没人给得了 _DIR（实证：coal ← boost，BoostConfig.cmake 内部找 boost_headers
        # 失败，而 boost_headers-config.cmake 就在同一个 lib/cmake 下）。
        # 无依赖时返回 ""，不写这个文件——避免给纯粹无依赖的包放宽 find 语义。
        import os
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
            # bins 的 install RUNPATH: $ORIGIN 在 cmake set() 内是字面量不被展开;
            # 若经 -DCMAKE_INSTALL_RPATH="$ORIGIN/.." 传, $ORIGIN 会被 shell/cmake 双重吃掉。
            # cmake 4.1 的 file(INSTALL) 不做 RPATH rewrite → 改为链接期写死
            # -Wl,-rpath,$ORIGIN/../lib（make 生成 link.txt 时 $ 转义为 $$, 链接器收到
            # 字面 $ORIGIN）。build 树内官方测试用 LD_LIBRARY_PATH, 不依赖此 RPATH。
            f.write('set(CMAKE_EXE_LINKER_FLAGS "-Wl,-rpath,\\$ORIGIN/../lib")\n')
        return path

    def build(self):
        # glfw/libjpeg-turbo/zstd/libxml2 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain——
        # os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035：System is unknown to cmake）。
        # toolchain 为 None = OHOS PC 原生构建（见 _ohos_toolchain ④），不传 TOOLCHAIN_FILE/OHOS_ARCH。
        # 链接器宿主运行时门禁 (PR #7530): configure 前先真实 probe, lld 缺
        # libxml2.so.16 时仅在本次 build() 作用域恢复 LD_LIBRARY_PATH。
        link_env = self._linker_runtime_environment()
        with (link_env.vars(self).apply() if link_env
              else contextlib.nullcontext()):
            apply_conandata_patches(self)
            toolchain = self._ohos_toolchain()
            src = os.path.join(self.source_folder, "")
            bdir = os.path.join(self.build_folder, "build-ohos")
            defs = []
        if toolchain:
            defs += [
                '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
                "-DOHOS_ARCH=arm64-v8a",
            ]
        defs += [
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            # **configure 期就要给 INSTALL_PREFIX**，不能只靠 `cmake --install --prefix`：
            # GNUInstallDirs 的 CMAKE_INSTALL_FULL_*（如 FULL_MANDIR）是在 configure 期
            # 按当时的 prefix 算成**绝对路径**写进 install 规则的，`--prefix` 覆盖不到它。
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DBUILD_SHARED_LIBS=ON",
        ]
        if toolchain:
            _rl = self._llvm_ranlib(toolchain)
            if _rl:
                defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        defs.append("-DBUILD_SHARED_LIBS=ON")
        # zziplib 选项: 关文档/SDL 示例，开 bins（官方测试 zziptests.py 依赖 zzcat/unzzip 等）
        defs.append("-DZZIPDOCS=OFF")
        defs.append("-DZZIPSDL=OFF")
        defs.append("-DZZIPBINS=ON")
        defs.append("-DZZIPTEST=ON")
        defs.append("-DZZIPWRAP=ON")
        # 上游 zzip/CMakeLists.txt 对这三项的 ON 默认值包在 if(UNIX OR MINGW) 里,
        # OHOS 无 CMake Platform 模块 → UNIX 为假 → 全部落入 else() 的 OFF 默认。
        # OFF 时 install 不产 zziplib.pc/zzipwrap.pc、compat 头(libzzip.h 等)和
        # libtool 版本化 .so 软链。CI 已实证 OFF 下 cmake --install 失败
        # (install 清单引用 build-ohos/zzip/zziplib.pc 不存在), 故必须显式开启。
        defs.append("-DZZIP_COMPAT=ON")
        defs.append("-DZZIP_LIBTOOL=ON")
        defs.append("-DZZIP_PKGCONFIG=ON")
        # CMake 4.x 移除了 cmake_minimum_required(<3.5) 兼容: zziplib 顶层要求 3.10, 但
        # CPack/其他模块可能仍触发 deprecation 硬错
        defs.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
        # SONAME: HarmonyOS 无 CMake Platform 模块 → CMAKE_SHARED_LIBRARY_SONAME_C_FLAG
        # 为空, 上游虽设了 SOVERSION 13 (zzip/CMakeLists.txt SET_TARGET_PROPERTIES
        # ... SOVERSION ${VERNUM}), 链接器却收不到 -Wl,-soname → libzzip-0.so 无
        # DT_SONAME, CI L5a 门禁失败且下游无法按 SONAME 寻址（同 libharu E298 问题）。
        # configure 期注入 flag 即可, 零 patch。libzzipwrap 额外依赖 libzzip, 注入后
        # 其 DT_NEEDED 从相对路径 ../zzip/libzzip-0.so 变成 SONAME libzzip-0.so。
        defs.append('-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"')
        # 依赖接线（find_package/find_library/pkg-config）须按需在此手工补 -D（见 SKILL「cmake 库依赖库」）：
        #   find_package(X CONFIG) → -DX_DIR=self.dependencies["x"].package_folder+"/lib/cmake/x"
        #   find_library/find_path → 预设目标库的 find 缓存变量为依赖真实路径（绕交叉链 FIND_ROOT_PATH=ONLY）
        zpref = self.dependencies["zlib"].package_folder
        defs.append('-DZLIB_ROOT="{}"'.format(zpref))
        defs.append('-DZLIB_LIBRARY="{}/lib/libz.a"'.format(zpref))
        defs.append('-DZLIB_INCLUDE_DIR="{}/include"'.format(zpref))
        # 交叉 toolchain 下 cmake 的 try_compile 走我们刚验证过的同一
        # clang→lld 链路 (probe 通过才走到这里), 不做任何绕过。
        # probe 赢家的 LD_LIBRARY_PATH 由 with apply() 作用域生效:
        # conanbuild env 文件只覆盖 PATH/SHELL/CONFIG_SHELL (实测),
        # 不动 LD_LIBRARY_PATH, 恢复值会原样传给 cmake 子进程。
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        # 默认 ALL 构建, 不传 --target 列表: 上游用 ALL 自定义目标生成 install 阶段
        # 的派生产物（zzip/*.pc、compat 头文件、libtool/版本化 .so 软链等）。显式
        # --target 只编库和 bins 会绕过这些 ALL 目标 → install 清单引用的 zziplib.pc
        # 未生成, cmake --install 在 CI 上失败。
        # ALL 里唯一会执行交叉二进制的是 test/sfx 目标: 其命令 ./zzipsetstub 的
        # DT_NEEDED 是 SONAME libzzip-0.so.13, 构建树内无 RPATH → 127。给构建进程
        # 注入 LD_LIBRARY_PATH=build-ohos/zzip 即可解析（原生构建树通常自带 RPATH,
        # 此变量对非交叉环境无害）。**注意**: 此处是命令行内联 LD_LIBRARY_PATH=...,
        # 会覆盖 with 作用域的恢复值; 若 probe 恢复了宿主运行时, lld 由 make 继承
        # 的环境加载 libxml2.so.16, 而此处内联值只保证 zzipsetstub 自身能找到
        # libzzip-0.so.13 —— 两者作用对象不同, 无冲突。
        # 兼容恢复值: 若 link_env 存在, 把赢家目录前置到内联值里, 保证
        # cmake --build 子进程内 lld 也能加载 libxml2.so.16 (链接期需要)。
        _host_rt = ''
        if link_env is not None:
            _vars = link_env.vars(self)
            _host_rt = _vars.get('LD_LIBRARY_PATH', '')
        _lz_prefix = ':'.join(p for p in (_host_rt, os.path.join(bdir, 'zzip')) if p)
        self.run('LD_LIBRARY_PATH="{lz}" cmake --build "{b}" -j{j}'.format(
            lz=_lz_prefix, b=bdir, j=os.cpu_count() or 4))

        # ── 上游官方测试: test/zziptests.py (python unittest, 230 cases) ──
        # 运行前提（实测约束）:
        #  ① zziptests.py 须从 build 树 test/ 目录运行（tmp.test_xxx 子目录按相对路径展开）
        #  ② -b 必须传 *相对路径* ../bins —— 多个用例 (20595/65485/65486) 执行
        #    `cd tmp.x && ../{exe}`，绝对路径会被拼成 "..//abs/path" 而失败 127
        #  ③ bins 的 DT_NEEDED 是 SONAME libzzip-0.so.13 → 需 LD_LIBRARY_PATH 指向
        #    test/zzip/（复制版本化 .so + 重建 .so.13/.so 软链，无侵入）
        #  ④ 用例集 = 全部数字用例，但显式排除 test_81000（SFX: zip-stub 前缀的自解压
        #    文件非 ELF magic 开头, OHOS 内核拒绝 exec → exit 126, 属环境限制非库缺陷;
        #    fnmatch 无补集语法, 故按 def test_<name> 枚举生成精确 pattern 列表）
        testdir = os.path.join(bdir, "test")
        if os.path.isdir(testdir):
            import shutil
            zzipdir = os.path.join(bdir, "zzip")
            os.makedirs(os.path.join(testdir, "zzip"), exist_ok=True)
            for so in os.listdir(zzipdir):
                if ".so." in so:                      # libzzip-0.so.13.0.80 真实文件
                    shutil.copy2(os.path.join(zzipdir, so),
                                 os.path.join(testdir, "zzip", so))
                    stem = so.rsplit(".so", 1)[0]     # libzzip-0
                    for link in (stem + ".so.13", stem + ".so"):
                        lp = os.path.join(testdir, "zzip", link)
                        if os.path.lexists(lp):
                            os.remove(lp)
                        os.symlink(so, lp)
            self.run('cp "{src}/test/zziptests.py" "{td}/zziptests.py"'.format(
                src=self.source_folder, td=testdir))
            import re
            with open(os.path.join(self.source_folder, "test", "zziptests.py"),
                      encoding="utf-8") as f:
                # \w 含大写（CVE 用例名如 test_59770_infozipdir_CVE_2017_5977），
                # 先前 [0-9a-z_] 会漏 40 项
                names = re.findall(r"def (test_[0-9]\w*)\(", f.read())
            patterns = " ".join(n for n in sorted(names) if not n.startswith("test_81000"))
            # 测试进程的 LD_LIBRARY_PATH: test/zzip (libzzip-0.so.13) + probe 赢家
            # (宿主 lld 需要 libxml2.so.16 时, 测试里任何再链接/工具调用同样需要)
            _t_lz = ':'.join(p for p in (os.path.join(testdir, 'zzip'), _host_rt) if p)
            env = "LD_LIBRARY_PATH={}".format(_t_lz)
            testcmd = (
                'cd "{td}" && {env} python3 zziptests.py'
                ' --exeext= --topsrcdir="{src}"'
                ' --downloads=OFF'
                ' -Z /usr/bin/zip -U /usr/bin/unzip'
                ' -b ../bins'
                ' {patterns} -v'
            ).format(td=testdir, env=env, src=self.source_folder, patterns=patterns)
            self.run(testcmd)

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（zzcat/unzzip 等 CLI）——产可执行文件的包必须签 bin。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        # 工具位置自适应: SDK 机在 /data/service/hnp/bin, OHOS PC 原生机在 PATH (usr/local/bin)
        import shutil
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        explicit_libs = ['zzip-0', 'zzipfseeko-0', 'zzipmmapped-0', 'zzipwrap-0']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "zziplib")
        self.cpp_info.set_property("cmake_target_name", "zziplib::libzzip")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
