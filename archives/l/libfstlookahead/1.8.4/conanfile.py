#!/usr/bin/env python3
"""Conan recipe - libfstlookahead 1.8.4 (OpenFst LookAheadFst extension)."""
import glob
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfstlookaheadConan(ConanFile):
    name = "libfstlookahead"
    version = "1.8.4"
    description = "LookAheadFst extension library of OpenFst: label/weight look-ahead FSTs for composition filtering"
    license = "Apache-2.0"
    homepage = "https://www.openfst.org/"
    url = "https://www.openfst.org/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        for root, _, files in os.walk(self.build_folder):
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
            # 本包只交付 LookAheadFst 扩展（libfstlookahead + arc/ilabel/olabel_lookahead-fst 模块），
            # 按上游 configure.ac 的扩展开关最小化启用；其余扩展保持上游默认 no。
            "--enable-lookahead-fsts",
            # 上游 configure.ac 的 bin 默认为 **yes**（fst::script + 37 个 fst* 命令行），必须显式关掉：
            # ①本包是库包，交付物是 libfstlookahead（+ 同 tarball 的 libfst）；fst* 命令行属
            #   openfst/1.8.4 包的交付面，在子库包里重复编一份是冗余；
            # ②上游 1.8.4 的 src/bin 里**没有任何 lookahead 专用工具**（`grep -l lookahead src/bin/*.cc` 为空），
            #   开启 bin 对本扩展的功能与测试证据零贡献；
            # ③上游 7 个 check_PROGRAMS 只链 ../lib/libfst.la（src/test/Makefile.am 无 HAVE_BIN 条件），
            #   关 bin 不影响上游测试面；
            # ④src/script(47 TU) + src/bin(74×2 TU) 占整包编译量约 80%，关掉后 G2/CI 的 3600s 构建预算
            #   从"必然超时"回到"余量充足"（本地实测：开 bin 时设备高负载下 22 分钟只编完 11/47 script TU）。
            "--disable-bin",
            "--enable-static" if not self.options.shared else "--disable-static",
            "--enable-shared" if self.options.shared else "--disable-shared",
        ])
        tc.generate()

    def _find_built_archive(self, relative, filename):
        # libtool 把静态库放在 <build>/<相对目录>/.libs/ 下；VPATH 构建时构建目录与源码目录不同，
        # 只按 build_folder 找（不猜源码树里的陈旧副本）。
        for pattern in (
            os.path.join(self.build_folder, relative, ".libs", filename),
            os.path.join(self.build_folder, "**", ".libs", filename),
        ):
            hits = sorted(glob.glob(pattern, recursive=True))
            if hits:
                return os.path.normpath(hits[0])
        raise Exception(f"Could not locate built archive {relative}/.libs/{filename}")

    def _build_upstream_tests(self):
        # 上游 src/test/Makefile.am 定义 7 个 check_PROGRAMS（TESTS = $(check_PROGRAMS)）：
        # fst_test、weight_test、algo_test_{log,tropical,minmax,lexicographic,power}。
        # BUILD.bazel 的 cc_test 规则是同一组 7 项（fst_test + weight_test + 5 个 algo_test_*），
        # 两个注册面计数一致。make 默认目标不编 check_PROGRAMS，`make check` 编完即跑 TESTS，
        # 这里按上游同一组源码/宏手动编译，产物随包安装供 test_package 在真机逐项执行。
        #
        # 链接根因（OpenFst 1.8.4 源码确认）：Fst::Read 由文件头解析类型名（如 "vector"），
        # 经 FstRegister::GetReader -> GenericRegister::GetEntry 查注册表（fst/register.h:66、
        # generic-register.h:78）。REGISTER_FST 宏产生的是静态 registerer 对象（fst-types.cc），
        # 链 libfst.a 时若无强引用会被链接器剔除 -> 注册表空 -> 回退 dlopen("<type>-fst.so")
        # 失败 -> fst_test.h 的 CHECK 崩溃。故用 -Wl,--whole-archive / --no-whole-archive 包夹。
        src_test = os.path.join(self.source_folder, "src", "test")
        include_dir = os.path.join(self.source_folder, "src", "include")
        if not os.path.isdir(src_test):
            raise Exception(f"Could not locate upstream test sources at {src_test}")
        libfst = self._find_built_archive(os.path.join("src", "lib"), "libfst.a")
        out_dir = os.path.join(self.build_folder, "_ohos_tests")
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
        ldflags = ["-Wl,--whole-archive", libfst, "-Wl,--no-whole-archive", "-lm", "-ldl"]

        specs = [
            ("fst_test", [], "fst_test.cc"),
            ("weight_test", [], "weight_test.cc"),
            ("algo_test_log", ["-DTEST_LOG"], "algo_test.cc"),
            ("algo_test_tropical", ["-DTEST_TROPICAL"], "algo_test.cc"),
            ("algo_test_minmax", ["-DTEST_MINMAX"], "algo_test.cc"),
            ("algo_test_lexicographic", ["-DTEST_LEXICOGRAPHIC"], "algo_test.cc"),
            ("algo_test_power", ["-DTEST_POWER"], "algo_test.cc"),
        ]
        for name, extra_defines, src in specs:
            src_path = os.path.join(src_test, src)
            out_path = os.path.join(out_dir, name)
            cmd = [cxx] + cppflags + extra_defines + [src_path] + ldflags + ["-o", out_path]
            self.output.info(f"Building upstream test: {name}")
            self.run(" ".join(f'"{w}"' if " " in w else w for w in cmd), env="conanbuild")

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
        autotools.make(args=["-j1"])
        # 上游存在测试（src/test/Makefile.am 的 7 个 check_PROGRAMS），必须接入真机执行。
        self._build_upstream_tests()

    def package(self):
        Autotools(self).install()
        # 把 7 个上游测试程序复制进包的 _ohos_tests/，供 test_package 真机执行。
        tests_src = os.path.join(self.build_folder, "_ohos_tests")
        tests_dst = os.path.join(self.package_folder, "_ohos_tests")
        if os.path.isdir(tests_src):
            os.makedirs(tests_dst, exist_ok=True)
            for name in os.listdir(tests_src):
                src = os.path.join(tests_src, name)
                dst = os.path.join(tests_dst, name)
                # E087/E182: HMDFS 不支持 chmod，open("wb") 默认 0644 无执行位，test_package
                # 直接执行会 Error 126。用 os.open 指定 mode 0o755 创建带执行位的文件。
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
        self.cpp_info.libs = ["fstlookahead"]
        # OpenFst Fst::Read 回退 dlopen("<type>-fst.so") 扩展模块，查找路径含 lib/fst/。
        # 共享构建时包内 lib/fst/ 下各扩展模块，需加进 LD_LIBRARY_PATH 供运行时加载。
        for sub in ("lib", "lib/fst"):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, sub))
