#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_package for libzzip 0.13.80 — verifies the public C API of the
# final Conan package on HarmonyOS PC (aarch64, musl, clang15).
#
# OHOS linker host runtime (PR #7530): a Conan test_package is a
# SEPARATE consumer recipe — the scoped Environment the main recipe
# applies around its own build() does NOT propagate into this recipe's
# CMake configure/compiler check. This recipe therefore runs the SAME
# discovery/probe/scoped-retry sequence as the main conanfile.py
# before cmake.configure(): a REAL minimal compile+link probe in the
# ambient environment first; only when that fails with a host-loader
# error (e.g. lld cannot load its libxml2.so.16 host dependency) are
# toolchain-derived candidate dirs that actually contain the missing
# library retried with LD_LIBRARY_PATH prepended, and only the winning
# dir is applied — via a Conan Environment scoped to
# cmake.configure()/cmake.build() (never os.environ, never a skipped
# or forced CMake compiler check). If every candidate fails the real
# probe, the recipe fails closed with full diagnostics.

import contextlib
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    # ── OHOS SDK linker host runtime (PR #7530; mirrors conanfile.py) ──
    #
    # Same behavior as the main recipe (kept deliberately in sync —
    # Conan exports test_package as an independent recipe, so the
    # helpers cannot be imported from the parent conanfile.py):
    #   * compiler from tools.build:compiler_executables (authoritative
    #     OHOS profile conf; basename+PATH fallback only), never a
    #     hardcoded toolchain path;
    #   * linker derived from the toolchain itself
    #     (-print-prog-name=ld.lld, realpath-resolved);
    #   * candidate host-runtime dirs derived ONLY from the active
    #     toolchain and current environment;
    #   * a REAL compile+link probe decides, not a --version check;
    #   * the fix is a Conan Environment scoped to the build methods.
    # musl 陷阱: 加载失败 stderr 报 Error loading/relocating 但退出码
    # 可能为 0 → probe 同时看 rc 与 stderr 模式。

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

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _get_cc(self):
        # 编译器以 Conan conf 为准 (OHOS profile 权威来源, 指向 SDK clang);
        # 路径不存在时仅回退 basename+PATH, 绝不硬编码工具链路径。
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
        # 从 probe 日志提取缺失宿主库文件名 (如 libxml2.so.16)
        libs = []
        for pattern in self._MISSING_LIB_PATTERNS:
            libs += pattern.findall(log or '')
        return [lib for lib in dict.fromkeys(libs) if '.so' in lib]

    def _is_host_loader_failure(self, log):
        lowered = (log or '').lower()
        return any(marker in lowered for marker in self._HOST_LOADER_MARKERS)

    def _host_runtime_libdirs(self, cc, lld, missing_libs):
        """候选宿主运行时目录, 只从当前工具链与环境推导 (优先级同主配方):
          1. 配置编译器的真实 LLVM 树
          2. 解析出 lld 的真实 LLVM 树
          3. 编译器 resource-dir 树 (clang -print-resource-dir)
          4. PATH 中的工具目录
          5. 当前 LD_LIBRARY_PATH
          6. 从工具链二进制向上的有界回溯
        只返回实际包含缺失库的目录 (日志未点名库时, 接受确实放着共享库的
        工具链目录)。
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
        CMake 编译器检查既要编译又要链接, 链接一步正是 lld 载入
        libxml2.so.16 失败时挂掉的地方。返回 (returncode, 合并输出)。
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
        """cmake.configure() 之前的链接器宿主运行时门禁 (PR #7530),
        与主配方同一序列 (test_package 是独立消费配方, 主配方 scoped
        Environment 不传播至此):
        1) 环境原样先跑真实 compile+link probe (通过 → 不动环境);
        2) 失败且属宿主动态库问题 → 从工具链推导含缺失库的候选目录,
           逐个前置到 LD_LIBRARY_PATH 重跑 probe;
        3) 赢家目录作为 Conan Environment 返回, 只在 build() 作用域应用;
           其余情况一律带着完整诊断 fail-closed。
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

    def build(self):
        # 链接器宿主运行时门禁 (PR #7530): test_package 独立配方, 主配方
        # 的 scoped Environment 不传播至此, 须自行恢复后再 configure/build。
        link_env = self._linker_runtime_environment()
        cmake = CMake(self)
        with (link_env.vars(self).apply() if link_env
              else contextlib.nullcontext()):
            cmake.configure()
            cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_package")
            tmpdir = os.path.join(self.build_folder, "tmp-run")
            os.makedirs(tmpdir, exist_ok=True)
            self.run(f'"{cmd}" "{tmpdir}"', env="conanrun")
