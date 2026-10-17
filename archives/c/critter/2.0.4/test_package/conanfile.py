#!/usr/bin/env python3
"""Conan test_package — critter 2.0.4（OHOS / aarch64 / 图形应用）。

被适配包是应用（application）：包内只产出 bin/critter + bin/resource.dat，没有可
链接的库，因此 build() 不做事，全部校验落在 test() 里（R34：必须真正执行被测产物）。

用例构成（6 用例 / 27 项断言，逐项打印 [case]/[assert] 便于审计）
------------------------------------------------------------------
静态产物校验（本文件实现，不依赖执行环境）
  S1 packaged-layout        bin/critter 存在 + 可执行位 + bin/resource.dat 存在
  S2 elf-ohos-aarch64       ELF64/LE/EM_AARCH64=183/ET_DYN(PIE)、
                            PT_INTERP=/lib/ld-musl-aarch64.so.1、
                            NEEDED 含 gl4es 的 libGL.so.1
  S3 resource-bundle        resource.dat 为合法 zip、含 system/config.txt、条目 >= 200
  S4 runenv-contract        包导出的 runenv（LIBGL_GLES/LIBGL_EGL）经 VirtualRunEnv
                            落入 conanrun 环境脚本（gl4es 后端定位的消费契约）
运行时冒烟（test_critter.sh 单次启动，8 项断言）
  S5 run-smoke              退出码 0、gl4es 初始化、GLES 2.0 后端、gl4es 关闭、
                            引擎版本横幅、PhysFS 挂载 ./resource.dat、
                            ~/.critter/config.txt 落盘
运行时一致性（本文件在 S5 的日志上比对）
  S6 dep-versions-reported  运行时打印的 SDL/SDL_image/SDL_mixer/PhysFS/zlib/PNG
                            版本与 conan 依赖版本一致（允许适配后缀）

上游测试：无（upstream_tests_exist=false，逐文件审计见 test_package/MANIFEST.yml），
故 HMBS_UPSTREAM_TEST_RESULT 标记 status=no_tests。

平台相关处理
------------
1. OHOS 上被测二进制要按 HarmonyOS 约定签名后才能 exec，且 conan 缓存可能落在
   HMDFS（chmod 被忽略、硬链接不支持）。因此运行时先把 bin/critter 复制到可写
   工作目录、去掉旧 .codesign 段并尽力 self-sign（fceux/2.6.6、backuppc-rsync 先例）。
2. 执行统一交给 CONFIG_SHELL（bash）：OHOS 的 /bin/sh 是 mksh，无法作为 conan
   包装器启动 ELF，且会重置 LD_LIBRARY_PATH（logstalgia/1.1.4、sdcc/4.6.0 先例）。
3. 无头环境：gl4es 需要 LIBGL_GLES / LIBGL_EGL 才能 dlopen 系统 GLES3/EGL，
   这两个变量由被测包 package_info().runenv_info 导出，经 env="conanrun" 注入。
"""

import json
import os
import re
import shlex
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

# gl4es 的 GL/ gl.h 只在 __EMSCRIPTEN__/__APPLE__ 下打开 GL_GLEXT_PROTOTYPES，
# 桌面 GL 2.0/3.0 原型因此缺失——上游 game/Video.cpp 调用了 glewInit()，故链接
# 由包内静态 GLEW shim 提供；这里只断言 gl4es 自身被真正链入。
_EXPECTED_NEEDED = ("libGL.so.1",)
_EXPECTED_INTERP = "/lib/ld-musl-aarch64.so.1"
_MIN_RESOURCE_ENTRIES = 200


class CritterTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # 应用包：无可链接产物，功能校验全部在 test()。
        pass

    # ------------------------------------------------------------------
    # 运行时准备
    # ------------------------------------------------------------------
    def _writable_dir(self):
        """可写工作目录：TMPDIR/TMP 可用则用，否则退回 build_folder。

        /tmp 在本平台只读，因此逐个候选做真实写入探测（fceux/2.6.6 先例）。
        """
        for cand in (os.environ.get("TMPDIR"), os.environ.get("TMP"),
                     os.path.join(self.build_folder, "critter-test")):
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(probe)
                return cand
            except OSError:
                continue
        return self.build_folder

    @staticmethod
    def _pick_shell():
        """优先 bash：OHOS 的 /bin/sh 是 mksh，会重置 LD_LIBRARY_PATH。"""
        for cand in (os.environ.get("CONFIG_SHELL"),
                     "/data/service/hnp/bin/bash",
                     shutil.which("bash"),
                     os.environ.get("SHELL"),
                     "/bin/sh"):
            if cand and os.path.exists(cand):
                return cand
        return "/bin/sh"

    def _dependency_libdirs(self):
        """各依赖包的 lib/ 目录，交给测试脚本自行前置 LD_LIBRARY_PATH。

        不单纯依赖 conanrun 注入：包装 shell 可能重置 LD_LIBRARY_PATH，
        这里由脚本内部（bash 进程）显式前置，保证 libc++_shared.so /
        libGL.so.1 等运行时库一定能被找到。
        """
        dirs = []
        for dependency in self.dependencies.values():
            folder = getattr(dependency, "package_folder", None)
            if not folder:
                continue
            libdir = os.path.join(folder, "lib")
            if os.path.isdir(libdir) and libdir not in dirs:
                dirs.append(libdir)
        return ":".join(dirs)

    def _runenv_text(self):
        """读取 VirtualRunEnv 生成的 conanrun 环境脚本内容。"""
        import glob
        text = ""
        for pattern in ("conanrun*.sh", "conanrun*.bat"):
            for path in glob.glob(os.path.join(self.generators_folder, pattern)):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        text += handle.read()
                except OSError:
                    continue
        return text

    def _runnable_copy(self, binary, workdir):
        """复制到可写目录并尽力签名 —— HMDFS 上原位置可能不可 exec。"""
        target = os.path.join(workdir, "critter")
        try:
            shutil.copy2(binary, target)
        except OSError as exc:
            self.output.warning(f"复制被测二进制失败({exc})，退回原路径执行")
            return binary

        for tool in ("/data/service/hnp/bin/llvm-objcopy",
                     shutil.which("llvm-objcopy") or ""):
            if not tool:
                continue
            try:
                subprocess.run([tool, "--remove-section", ".codesign", target],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False,
                               timeout=15)
                break
            except Exception:
                continue
        for tool in ("/data/service/hnp/bin/binary-sign-tool",
                     shutil.which("binary-sign-tool") or ""):
            if not tool:
                continue
            try:
                proc = subprocess.run(
                    [tool, "sign", "-inFile", target, "-outFile", target,
                     "-selfSign", "1"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False, timeout=20)
                if proc.returncode == 0:
                    self.output.info(f"self-signed 被测二进制（{tool}）")
                    break
            except Exception:
                continue
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return target

    # ------------------------------------------------------------------
    # 断言辅助
    # ------------------------------------------------------------------
    def _case(self, name, pairs):
        """打印一个用例；pairs = [(ok, 描述), ...]，返回 (passed, failed)。"""
        self.output.info(f"[case] {name}")
        passed = failed = 0
        for ok, detail in pairs:
            if ok:
                passed += 1
                self.output.info(f"  [assert] OK   : {detail}")
            else:
                failed += 1
                self.output.info(f"  [assert] FAIL : {detail}")
        return passed, failed

    @staticmethod
    def _elf_info(path):
        with open(path, "rb") as handle:
            data = handle.read()
        if data[:4] != b"\x7fELF":
            raise ConanException(f"{path} 不是 ELF 文件")
        info = {
            "ei_class": data[4],
            "ei_data": data[5],
            "e_type": struct.unpack_from("<H", data, 16)[0],
            "e_machine": struct.unpack_from("<H", data, 18)[0],
        }
        # 逐字段按各自偏移读取：Elf64_Ehdr 中这些字段并不连续
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phentsize = struct.unpack_from("<H", data, 54)[0]
        phnum = struct.unpack_from("<H", data, 56)[0]
        loads, interp = [], None
        for index in range(phnum):
            base = phoff + index * phentsize
            p_type = struct.unpack_from("<I", data, base)[0]
            p_offset, p_vaddr = struct.unpack_from("<QQ", data, base + 8)
            p_filesz = struct.unpack_from("<Q", data, base + 32)[0]
            if p_type == 1:                       # PT_LOAD
                loads.append((p_offset, p_vaddr, p_filesz))
            elif p_type == 3:                     # PT_INTERP
                interp = data[p_offset:p_offset + p_filesz].split(b"\x00")[0]
        info["interp"] = interp.decode("utf-8", "replace") if interp else ""

        shoff = struct.unpack_from("<Q", data, 40)[0]
        shentsize = struct.unpack_from("<H", data, 58)[0]
        shnum = struct.unpack_from("<H", data, 60)[0]
        needed, strtab_vaddr = [], None
        for index in range(shnum):
            base = shoff + index * shentsize
            sh_type = struct.unpack_from("<I", data, base + 4)[0]
            sh_offset, sh_size = struct.unpack_from("<QQ", data, base + 24)
            if sh_type != 6:                      # SHT_DYNAMIC
                continue
            for entry in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", data, entry)
                if d_tag == 0:                    # DT_NULL
                    break
                if d_tag == 1:                    # DT_NEEDED
                    needed.append(d_val)
                elif d_tag == 5:                  # DT_STRTAB
                    strtab_vaddr = d_val
        if strtab_vaddr is not None:
            strtab_off = None
            for p_offset, p_vaddr, p_filesz in loads:
                if p_vaddr <= strtab_vaddr < p_vaddr + p_filesz:
                    strtab_off = p_offset + (strtab_vaddr - p_vaddr)
                    break
            if strtab_off is not None:
                resolved = []
                for offset in needed:
                    raw = data[strtab_off + offset:strtab_off + offset + 256]
                    resolved.append(raw.split(b"\x00")[0].decode("utf-8", "replace"))
                info["needed"] = resolved
        info.setdefault("needed", [])
        return info

    def _version_matches(self, printed, ref_version):
        if printed == ref_version:
            return True
        return ref_version.startswith(printed + ".")

    # ------------------------------------------------------------------
    # test
    # ------------------------------------------------------------------
    def test(self):
        dependency = self.dependencies[self.tested_reference_str]
        package_folder = dependency.package_folder
        bin_dir = os.path.join(package_folder, "bin")
        exe = os.path.join(bin_dir, "critter")
        resource = os.path.join(bin_dir, "resource.dat")

        total_passed = total_failed = 0
        skipped = []

        # ---- S1 packaged-layout -------------------------------------
        exists = os.path.isfile(exe)
        mode = os.stat(exe).st_mode if exists else 0
        executable = bool(mode & 0o100)
        data_ok = os.path.isfile(resource)
        passed, failed = self._case("packaged-layout", [
            (exists, f"包内 bin/critter 存在（{exe}）"),
            (executable, f"bin/critter 具可执行位（mode={oct(mode)}）"),
            (data_ok, f"包内 bin/resource.dat 存在"
                      + (f"（{os.path.getsize(resource)} 字节）" if data_ok else "")),
        ])
        total_passed += passed
        total_failed += failed

        # ---- S2 elf-ohos-aarch64 ------------------------------------
        info = self._elf_info(exe) if exists else {}
        needed = info.get("needed", [])
        passed, failed = self._case("elf-ohos-aarch64", [
            (info.get("ei_class") == 2 and info.get("ei_data") == 1,
             f"ELF64 小端（class={info.get('ei_class')} data={info.get('ei_data')}）"),
            (info.get("e_machine") == 183,
             f"e_machine=AArch64（{info.get('e_machine')}）"),
            (info.get("e_type") == 3,
             f"ET_DYN/PIE（e_type={info.get('e_type')}）"),
            (info.get("interp") == _EXPECTED_INTERP,
             f"PT_INTERP={info.get('interp') or '(缺失)'}"),
            (all(any(exp in item for item in needed) for exp in _EXPECTED_NEEDED),
             f"NEEDED 含 {', '.join(_EXPECTED_NEEDED)}（实际 {needed}）"),
        ])
        total_passed += passed
        total_failed += failed

        # ---- S3 resource-bundle -------------------------------------
        import zipfile
        entries = 0
        has_config = False
        zip_ok = False
        if data_ok:
            try:
                with zipfile.ZipFile(resource) as bundle:
                    names = bundle.namelist()
                    zip_ok = bundle.testzip() is None
                    entries = len(names)
                    has_config = "system/config.txt" in names
            except Exception as exc:
                self.output.warning(f"resource.dat 读取失败：{exc}")
        passed, failed = self._case("resource-bundle", [
            (zip_ok, "resource.dat 为合法 zip 且 CRC 校验通过"),
            (has_config, "资源包含 system/config.txt（上游资源自检入口）"),
            (entries >= _MIN_RESOURCE_ENTRIES,
             f"资源条目数 {entries} >= {_MIN_RESOURCE_ENTRIES}"),
        ])
        total_passed += passed
        total_failed += failed

        # ---- S4 runenv-contract -------------------------------------
        runenv = self._runenv_text()
        passed, failed = self._case("runenv-contract", [
            (bool(runenv), "VirtualRunEnv 已生成 conanrun 环境脚本"),
            ("LIBGL_GLES" in runenv and "/system/lib64/libGLESv3.so" in runenv
             and "LIBGL_EGL" in runenv and "/system/lib64/libEGL.so" in runenv,
             "conanrun 环境含包导出的 LIBGL_GLES/LIBGL_EGL（gl4es 后端定位）"),
        ])
        total_passed += passed
        total_failed += failed

        # ---- S5 run-smoke（shell 脚本，单次启动）--------------------
        shell = self._pick_shell()
        script = os.path.join(self.recipe_folder, "test_critter.sh")
        workdir = self._writable_dir()
        # 被测产物统一 stage 到私有目录：可写 + 已签名版本，且 resource.dat 与可
        # 执行文件同级（上游 main.cpp 以 ./resource.dat 相对路径经 PhysFS 挂载，
        # 因此两者必须同目录，否则资源包不会被挂上）。
        stagedir = os.path.join(workdir, "critter-pkg")
        os.makedirs(stagedir, exist_ok=True)
        if exists:
            self._runnable_copy(exe, stagedir)
        if data_ok:
            shutil.copy2(resource, os.path.join(stagedir, "resource.dat"))
        logfile = os.path.join(workdir, "critter-run.log")
        libdirs = self._dependency_libdirs()
        inner = "%s %s %s %s %s > %s 2>&1" % (
            shlex.quote(shell), shlex.quote(script), shlex.quote(workdir),
            shlex.quote(stagedir), shlex.quote(libdirs), shlex.quote(logfile))
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("test_critter.sh log（末 20 行）：\n"
                         + "\n".join(out.splitlines()[-20:]))

        match = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not match:
            # 脚本没跑起来：只有确认本机不能执行目标程序时才降级为跳过
            banner = "INFO: Critter" in out
            if not banner and not can_run(self):
                skipped.append("run-smoke")
                self.output.warning(
                    "run-smoke 跳过：本机无法执行 OHOS/aarch64 产物"
                    "（can_run=False）")
            else:
                total_failed += 1
                self.output.info("[case] run-smoke")
                self.output.info(
                    "  [assert] FAIL : test_critter.sh 未产出 RESULT 行"
                    "（测试脚本或执行环境异常）")
        else:
            passed, failed = int(match.group(1)), int(match.group(2))
            total_passed += passed
            total_failed += failed

        # ---- S6 dep-versions-reported（在 S5 日志上比对）------------
        expectations = (
            ("SDL", "sdl2"), ("SDL_image", "sdl2-image"),
            ("SDL_mixer", "sdl2-mixer"), ("PhysFS", "physfs"),
            ("zlib", "zlib"), ("PNG", "libpng"),
        )
        version_pairs = []
        for label, dep_name in expectations:
            ref_version = str(self.dependencies[dep_name].ref.version)
            found = re.search(rf"INFO: {re.escape(label)} Version (\S+)", out)
            printed = found.group(1) if found else ""
            version_pairs.append((
                bool(printed) and self._version_matches(printed, ref_version),
                f"{label} 运行时报告 {printed or '(缺失)'} ↔ conan 依赖 {ref_version}"))
        passed, failed = self._case("dep-versions-reported", version_pairs)
        total_passed += passed
        total_failed += failed

        # ---- 汇总 + HMBS 证据标记 ----------------------------------
        cases = 5 + (0 if "run-smoke" in skipped else 1)
        discovered = cases
        passed_cases = 0 if total_failed else cases
        self.output.info(
            f"[test] critter/2.0.4 消费者校验：{discovered} 用例、"
            f"{total_passed + total_failed} 项断言，"
            f"通过 {total_passed}、失败 {total_failed}"
            + (f"，跳过 {skipped}" if skipped else ""))
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": True,
                "passed": total_failed == 0,
                "command": "%s test_critter.sh（无头运行时冒烟）+ 静态产物校验"
                           % shell,
                "discovered": discovered,
                "passedCount": passed_cases,
                "assertions": total_passed + total_failed,
                "assertionsPassed": total_passed,
            }, ensure_ascii=False))
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "no_tests",
                "framework": "none",
                "command": "ctest (上游未注册任何测试)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "critter 2.0.4（mooflu/critter，SDL2 分支）上游无可接入的测试"
                    "套件：顶层/game/CMakeLists.txt 从未调用 enable_testing() 或 "
                    "add_test()；全仓唯一含 test 字样的 mooflu.common/tinyxml/"
                    "xmltest.cpp 从未被 tinyxml/CMakeLists.txt 编译；scripts/ 与 "
                    "tools/ 无 check 目标；.github/workflows/{native,webapp}.yml "
                    "只构建不测试（逐文件审计见 test_package/MANIFEST.yml）"
                ),
            }, ensure_ascii=False))

        if total_failed:
            raise ConanException(
                f"critter 消费者校验失败：{total_failed} 项断言未通过")
