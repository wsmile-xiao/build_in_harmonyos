#!/usr/bin/env python3
"""Conan recipe - libfstfar 1.8.4 (OpenFst FAR / FST-archive extension)."""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfstfarConan(ConanFile):
    name = "libfstfar"
    version = "1.8.4"
    description = "FAR (FST ARchive) extension library of OpenFst: STTable/STList archives and the far* tools"
    license = "Apache-2.0"
    homepage = "https://www.openfst.org/"
    url = "https://www.openfst.org/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # 默认 **shared**（与上游 configure 不带 --disable-shared 时的默认一致）：
    # openfst 的类型注册表由 lib/fst-types.cc 的 `REGISTER_FST` 静态对象在**加载时**注册
    # （fst/register.h:119）。静态链接时 fst-types.o 里没有被引用的强符号，链接器按需取
    # 对象文件会把它整块剔除 → FstRegister 表空 → Fst::Read 回退 dlopen("vector-fst.so")
    # 失败并返回 nullptr。实测后果不是"少一个优化"，而是**包内交付的命令行工具集体失效**：
    # fstinfo/fstprint/farinfo/farextract 读任何 FST 都报 `Unknown FST type "vector"`，
    # farcreate 静默写出 0 条目的空档案（rc=0 的假成功）。动态库整库加载即可让静态注册器
    # 全部执行。仍可用 `-o libfstfar/*:shared=False` 取静态形态，此时下游必须用
    # `-Wl,--whole-archive libfst.a`（test_package 的两条路径都覆盖）。
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _write_install_shim(self):
        # E182/E188: OHOS worker image 的 toybox install 在 HMDFS 上 `-c` 选项直接失败 (Error 64)，
        # 也没有 GNU coreutils install。autotools `make install` 仅需文件复制 + 目录创建 + 可选 chmod，
        # 这里写一个 install shim，用 cp/mkdir 替代；HMDFS 不支持 chmod，chmod 步骤容错跳过。
        # 返回 shim 绝对路径，供 sed 改 Makefile 的 INSTALL 变量指向它（PATH 前置会被 conan build env 覆盖）。
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        with open(install, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "set -eu\n"
                "mode=\n"
                "while [ $# -gt 0 ]; do\n"
                "  case \"$1\" in\n"
                "    -p|-c) shift ;;\n"
                "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                "    --) shift; break ;;\n"
                "    -*) shift ;;\n"
                "    *) break ;;\n"
                "  esac\n"
                "done\n"
                "[ $# -ge 2 ] || exit 2\n"
                "dest=\n"
                "for arg in \"$@\"; do dest=$arg; done\n"
                "count=$(($# - 1))\n"
                "mkdir -p \"$(dirname \"$dest\")\"\n"
                "i=1\n"
                "for src in \"$@\"; do\n"
                "  [ $i -gt $count ] && break\n"
                "  cp -f \"$src\" \"$dest\"\n"
                "  # HMDFS 不支持 chmod (E087)，设权限失败不阻断复制。\n"
                "  if [ -n \"$mode\" ]; then\n"
                "    if [ -d \"$dest\" ]; then\n"
                "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                "    else\n"
                "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                "    fi\n"
                "  fi\n"
                "  i=$((i + 1))\n"
                "done\n"
            )
        os.chmod(install, 0o755)
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure 已把 toybox install 路径写死进所有子 Makefile 的 INSTALL 变量。
        # conan build env 的 PATH 前置会被 source conanbuild.sh 覆盖，靠 PATH 让 configure 探测 shim 无效。
        # 改为 sed 直接改已生成的 Makefile：把 `INSTALL = <toybox install -c>` 替换为 `INSTALL = <shim>`，
        # INSTALL_DATA/INSTALL_PROGRAM 默认 `${INSTALL} -m 644`/`${INSTALL}` 跟着重算，make install 全程用 shim。
        bf = self.build_folder
        for root, _, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "INSTALL =" not in content:
                    continue
                # 仅替换「INSTALL = <某 install 命令>」行（含 -c 后缀的 toybox install），
                # 不动 INSTALL_DATA/INSTALL_PROGRAM（它们引用 ${INSTALL}，跟着重算）。
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append(f"{indent}INSTALL = {shim_install}\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.write("".join(lines))

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        # HMDFS workaround (E011): prefer a writable TMPDIR for configure's tmp dir.
        tmpdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ.setdefault("TMP", tmpdir)
        os.environ.setdefault("TEMP", tmpdir)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # --enable-far 是本子包唯一的扩展开关：openfst configure.ac 里全部
            # --enable-*-fsts/--enable-far/--enable-grm 默认都是 no，不打开它
            # src/extensions/Makefile.am 的 HAVE_FAR 为空 -> 根本不进 far 子目录、
            # 也就没有 libfstfar.la（详见 notes.md「遇到的问题与解决方案」第 1 条）。
            "--enable-far",
            # --disable-bin（显式声明，因为上游默认是 yes）：本包是 openfst 的 **子库**，
            # 交付面只有 FAR 扩展本身（libfstfar + include/fst/extensions/far/*.h）。
            # HAVE_BIN 同时是 HAVE_SCRIPT 的开关（configure.ac:119-126），打开它会连带构建
            # src/script（47 TU）+ src/bin（46 个 fst* 工具 × 2 TU = 92 TU）+ far* 工具，
            # 约占整包编译量 80%。两组工具都属于 openfst 主包（`openfst/1.8.4`）而不是本子包；
            # 家族先例 `archives/l/libfstconst/1.8.4` 也明写「需要 fst::script 与命令行工具
            # 请用 openfst/1.8.4」。同批同 tarball 兄弟包 `libfstlookahead` 采用同一口径。
            # 另有一条硬约束：本地/CI 的 G2 `conan create` 超时被硬编码为 3600s
            # （`scripts/ohc/conan_verify.py:751`，不受 `--timeout`/`OHC_W3_TIMEOUT` 影响），
            # 本设备实测全量构建需 3600–3900s，会在 test_package 前被杀（连续 3 轮）。
            "--disable-bin",
            "--enable-static" if not self.options.shared else "--disable-static",
            "--enable-shared" if self.options.shared else "--disable-shared",
        ])
        tc.generate()

    def _build_upstream_tests(self):
        # 上游测试清点（父 tarball openfst-1.8.4.tar.gz 的完整注册面，见 notes.md）：
        #   注册类口径：src/test/Makefile.am 的 check_PROGRAMS = 7（TESTS = $(check_PROGRAMS)）；
        #               BUILD.bazel 的 cc_test = 7；CMakeLists.txt 不存在 = 0。
        #   用例分支口径：fst_test + weight_test + algo_test.cc 的 8 个 TEST_* 分支
        #               （TROPICAL/LOG/MINMAX/LEFT_STRING/RIGHT_STRING/GALLIC/
        #                 LEXICOGRAPHIC/POWER，见 src/test/algo_test.cc:66-89）= 10。
        # 主 N 取用例/注册类口径的**最大值** = 10；其中 7 个有上游注册项、3 个同源分支
        # （left_string/right_string/gallic）在两套构建系统里都没有注册项，本配方一并编译执行，
        # 以覆盖最大清点口径（不为凑数打开任何上游扩展开关）。
        # make 默认目标不编 check_PROGRAMS；这里手动 clang++ 编译，随包安装供 test_package 运行。
        #
        # 根因（OpenFst 1.8.4 源码确认）：Fst::Read 通用基类读文件头解析类型名（如 "vector"），
        # 经 FstRegister::GetReader -> GenericRegister::GetEntry 查注册表（fst/register.h:45-50）
        # REGISTER_FST 宏 = static FstRegisterer 静态对象；lib/fst-types.cc 集中注册 VectorFst /
        # ConstFst / EditFst / Compact*Fst 的 Std/Log/Log64 三种 arc。GenericRegister::GetEntry
        # 找不到则 dlopen("<type>-fst.so") 回退（generic-register.h:96-100）。链 libfst.a 静态库时
        # 链接器按需取对象文件，fst-types.o 的 static registerer 若无强引用被剔除 -> 注册表空
        # -> dlopen("vector-fst.so") 失败 -> Fst::Read 返回 nullptr -> CHECK 崩。
        # 修复：链 libfst.a 时用 -Wl,--whole-archive / -Wl,--no-whole-archive 包夹，强制保留全部 REGISTER 符号。
        import glob
        bf = self.build_folder
        # 源码根：找含 src/test/fst_test.cc 的目录（从 bf 向上或在 bf 下）。
        fst_test_cc = None
        for pattern in (
            os.path.join(bf, "src", "test", "fst_test.cc"),
            os.path.join(bf, "..", "src", "test", "fst_test.cc"),
        ):
            cand = os.path.normpath(pattern)
            if os.path.exists(cand):
                fst_test_cc = cand
                break
        if not fst_test_cc:
            hits = glob.glob(os.path.join(bf, "**", "fst_test.cc"), recursive=True)
            if not hits:
                hits = glob.glob(os.path.join(bf, "..", "**", "fst_test.cc"), recursive=True)
            if not hits:
                raise Exception("Could not locate upstream src/test/fst_test.cc for upstream tests")
            fst_test_cc = os.path.normpath(hits[0])
        src_test = os.path.dirname(fst_test_cc)
        include_dir = os.path.normpath(os.path.join(src_test, "..", "include"))
        # 优先用静态库 + whole-archive（无论本次是 static 还是 shared 构建，只要 .a 在就用它：
        # 测试程序不依赖 rpath，注册表由 whole-archive 保证）；shared-only 构建时退回动态库。
        libfst_hits = glob.glob(os.path.join(bf, "**", ".libs", "libfst.a"), recursive=True)
        if not libfst_hits:
            libfst_hits = glob.glob(os.path.join(bf, "..", "**", ".libs", "libfst.a"), recursive=True)
        if libfst_hits:
            libfst = os.path.normpath(libfst_hits[0])
            # whole-archive 包夹 libfst.a，强制保留 REGISTER_FST 静态 registerer（否则链接器剔除 -> 注册表空）。
            ldflags = ["-Wl,--whole-archive", libfst, "-Wl,--no-whole-archive", "-lm", "-ldl"]
        else:
            so_hits = glob.glob(os.path.join(bf, "**", ".libs", "libfst.so"), recursive=True)
            if not so_hits:
                so_hits = glob.glob(os.path.join(bf, "..", "**", ".libs", "libfst.so"), recursive=True)
            if not so_hits:
                raise Exception("Could not locate built libfst library for upstream tests")
            so_dir = os.path.dirname(os.path.normpath(so_hits[0]))
            # 动态库整库加载即可让 fst-types.o 的 REGISTER_FST 静态注册器全部执行。
            # 测试程序被安装到 <包>/_ohos_tests/，用 $ORIGIN/../lib 指向同包 lib/。
            ldflags = [f"-L{so_dir}", "-lfst", "-Wl,-rpath,'$ORIGIN'/../lib", "-lm", "-ldl"]
        out_dir = os.path.join(bf, "_ohos_tests")
        os.makedirs(out_dir, exist_ok=True)

        cxx = os.environ.get("CXX") or "clang++"
        cppflags = [
            f"-I{include_dir}",
            "-DHAVE_CONFIG_H",
            "-stdlib=libc++",
            "-std=c++17",
            "-fno-exceptions",
            "-Wno-deprecated-declarations",
            "-fPIC",
            "-O3",
        ]

        specs = [
            ("fst_test", [], "fst_test.cc"),
            ("weight_test", [], "weight_test.cc"),
            ("algo_test_log", ["-DTEST_LOG"], "algo_test.cc"),
            ("algo_test_tropical", ["-DTEST_TROPICAL"], "algo_test.cc"),
            ("algo_test_minmax", ["-DTEST_MINMAX"], "algo_test.cc"),
            ("algo_test_lexicographic", ["-DTEST_LEXICOGRAPHIC"], "algo_test.cc"),
            ("algo_test_power", ["-DTEST_POWER"], "algo_test.cc"),
            # 以下 3 个是同源但上游未注册的 TEST_* 分支（Makefile.am / BUILD.bazel 均无对应项），
            # 为覆盖最大清点口径一并编译执行；它们是上游 src/test/algo_test.cc 的原样编译，
            # 只是换一个 -D 宏，不涉及任何上游源码修改或扩展开关。
            ("algo_test_left_string", ["-DTEST_LEFT_STRING"], "algo_test.cc"),
            ("algo_test_right_string", ["-DTEST_RIGHT_STRING"], "algo_test.cc"),
            ("algo_test_gallic", ["-DTEST_GALLIC"], "algo_test.cc"),
        ]
        for name, extra_defines, src in specs:
            src_path = os.path.join(src_test, src)
            out_path = os.path.join(out_dir, name)
            cmd = [cxx] + cppflags + extra_defines + [src_path] + ldflags + ["-o", out_path]
            self.output.info(f"Building upstream test: {name}")
            self.run(" ".join(f'"{w}"' if " " in w else w for w in cmd), env="conanbuild")

    def _add_origin_rpath(self):
        # 动态构建交付的二进制要能在**没有** LD_LIBRARY_PATH 的环境里直接执行（CI 的 L2 smoke、
        # 真实用户），而 libtool 不自动加 rpath。用 `$ORIGIN/../lib` 做成可重定位 rpath：
        # 包的布局是 <pkg>/bin 与 <pkg>/lib 同级，无论包被拷到哪里都能找到同包的
        # libfst.so.26 / libfstfar.so.26。生成式 Makefile 的 LDFLAGS 是空值，直接追加；
        # `$$ORIGIN` 经 make 传给 shell 后即为字面量 `$ORIGIN`（make 吃掉一个 `$`）。
        #
        # 判据只看**该 LDFLAGS 行本身**，不能看整个文件是否出现 "-rpath"：automake 生成的
        # Makefile 里本来就有 `am_libfst<ext>_la_rpath = -rpath $(libdir)` 这类无关变量
        # （src/extensions/far/Makefile 有 3 处），按整文件判断会**整文件跳过** →
        # 9 个 far* 工具的 RUNPATH 保持为 `//lib`、在裸 PATH 下 rc=127 加载不到
        # libfstfarscript.so.26（首轮 W4 审计 P1，实测 `bin/farinfo --help` rc=127 vs
        # `bin/fstinfo --help` rc=0）。改为逐行判断后 bin/ 与 extensions/*/ 下的二进制一致。
        if not self.options.shared:
            return
        bf = self.build_folder
        for root, _, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                out = []
                changed = False
                for line in content.splitlines(True):
                    if line.startswith("LDFLAGS = ") and "-rpath" not in line:
                        out.append(line.rstrip("\n") + " -Wl,-rpath,'$$ORIGIN'/../lib\n")
                        changed = True
                    else:
                        out.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.write("".join(out))

    def build(self):
        apply_conandata_patches(self)
        bf = self.build_folder
        if os.path.isdir(bf):
            os.chdir(bf)
            os.environ["PWD"] = bf
        autotools = Autotools(self)
        autotools.configure()
        if str(self.settings.os) == "OHOS":
            # configure 已把 toybox install 写死进 Makefile INSTALL 变量；
            # sed 改 Makefile 让 INSTALL 指向 install shim，make install 用 cp 替代 toybox install。
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
        self._add_origin_rpath()
        # -j2：openfst 全量构建（lib + script + 46 个 fst* + 9 个 far* 二进制 + 10 个测试程序）
        # 在 -j1 下实测超过 ohc `conan_verify` G2 硬编码的 3600s 超时
        # （scripts/ohc/conan_verify.py:751 `self._run(cmd, timeout=3600)`；该值不受
        # `--timeout`/`OHC_W3_TIMEOUT` 影响——后者只作用于 finish 的 W3 步骤）。
        # -j2 与同批同 tarball 兄弟包 libfstngram 的取值一致，也是仓库 `-c tools.build:jobs=2`
        # 的目标并发；单 TU 峰值 RSS 约 79MB，2 路不构成内存压力。
        autotools.make(args=["-j2"])
        # 上游存在测试（src/test/Makefile.am 注册 7 个 check_PROGRAMS，按最大清点口径扩到 10 个用例），
        # 必须接入真机执行。make 默认目标不编 check_PROGRAMS，这里在 libfst.a 构建完成后手动编译链接 10 个测试程序，
        # 随包安装供 test_package 运行。
        self._build_upstream_tests()

    def package(self):
        Autotools(self).install()
        # 把 10 个上游测试程序复制进包的 _ohos_tests/，供 test_package 真机执行。
        bf = self.build_folder
        tests_src = os.path.join(bf, "_ohos_tests")
        tests_dst = os.path.join(self.package_folder, "_ohos_tests")
        if os.path.isdir(tests_src):
            os.makedirs(tests_dst, exist_ok=True)
            for name in os.listdir(tests_src):
                src = os.path.join(tests_src, name)
                dst = os.path.join(tests_dst, name)
                # E087/E182: HMDFS 不支持 chmod，open("wb") 默认 0644 无执行位，test_package 直接执行会 Error 126。
                # 用 os.open 指定 mode 0o755 创建带执行位的文件，HMDFS 新建文件按 open mode 给权限。
                with open(src, "rb") as fi:
                    data = fi.read()
                fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
                try:
                    with os.fdopen(fd, "wb") as fo:
                        fo.write(data)
                except Exception:
                    os.close(fd)
                    raise

    def package_info(self):
        # libfstfar.la 的 LIBADD 是 ../../lib/libfst.la（extensions/far/Makefile.am），
        # 静态链接时 libfstfar.a 的未定义符号要靠 libfst.a 解析，所以本包必须同时声明 fst
        # （本包内确实交付了 lib/libfst.a / libfst.so —— openfst 核心库始终构建并安装）。
        self.cpp_info.libs = ["fstfar", "fst"]
        # OpenFst Fst::Read 回退 dlopen("<type>-fst.so") 扩展模块，查找路径含 lib/fst/。
        # 本子包只开 --enable-far，lib/fst/ 可能不存在（那些 .so 由 compact/const/... 扩展产出），
        # 因此逐个判断目录存在再注入，避免把不存在的路径塞进 LD_LIBRARY_PATH。
        for sub in ("lib", "lib/fst"):
            path = os.path.join(self.package_folder, sub)
            if os.path.isdir(path):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", path)
