#!/usr/bin/env python3
"""Conan recipe — sofa 20231011-also-called-release-19 (custom direct build).

IAU Standards of Fundamental Astronomy (SOFA) C Library, Issue 2023-10-11,
the nineteenth release of the ANSI C library ("also called release 19").

The upstream bundle ships plain ANSI C sources plus a vendor makefile and a
single self-test program (c/src/t_sofa_c.c). There is no CMake/autotools
entry point, so this recipe compiles the sources directly with the Conan
configured C compiler (tools.build:compiler_executables, never bare $CC)
and archives them with the configured archiver, following the
archives/t/tiny-aes-c direct-build precedent.
"""

import glob
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SofaConan(ConanFile):
    name = "sofa"
    version = "20231011-also-called-release-19"
    description = "IAU Standards of Fundamental Astronomy (SOFA) C Library."
    license = "SOFA Software License"
    homepage = "https://www.iausofa.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("iau", "astronomy", "sofa")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executables(self):
        return (
            self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            )
            or {}
        )

    def _cc(self):
        import shutil
        cc_conf = self._compiler_executables().get("c")
        # 仅当 conf 绝对路径真实存在时采用（mpfit 经验：永不返回不存在的绝对路径）。
        # 真机预检证明 profile 的 /data/service/hnp/bin/clang 在执行机上
        # 不存在（/bin/sh: inaccessible or not found），必须回退。
        if cc_conf and os.path.isabs(cc_conf) and os.path.isfile(cc_conf):
            return cc_conf
        # PATH 中查找（hmbs/profile 把工具目录前置到 buildenv PATH）。
        for candidate in ("clang", "cc"):
            found = shutil.which(candidate)
            if found:
                self.output.info("resolved C compiler %s -> %s" % (candidate, found))
                return found
        # OHOS SDK 内 clang 常见位置（不写死版本号，动态 glob）。
        for pattern in (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang",
            "/data/service/hnp/*/llvm/bin/clang",
            "/data/service/hnp/bin/clang*",
        ):
            for hit in sorted(glob.glob(pattern)):
                if os.path.isfile(hit):
                    self.output.info("resolved C compiler via sdk glob -> %s" % hit)
                    return hit
        # 最后回退 basename，交由 buildenv PATH 在 self.run 时解析；
        # 若 conf 给的是 stale 绝对路径，取其 basename 比原样返回更有机会命中。
        if cc_conf:
            base = os.path.basename(cc_conf) or "clang"
            which_base = shutil.which(base)
            if which_base:
                return which_base
            self.output.warning(
                "configured C compiler %s not found; falling back to basename %s"
                % (cc_conf, base)
            )
            return base
        raise ConanInvalidConfiguration(
            "tools.build:compiler_executables must define the C compiler as 'c'"
        )

    def _ar(self):
        import shutil
        import subprocess
        ar_conf = self._compiler_executables().get("ar")
        # conf 的 ar 仅当真实存在时直接采用，否则走与 _cc 同样的多级回退。
        if ar_conf:
            if os.path.isabs(ar_conf):
                if os.path.isfile(ar_conf):
                    return ar_conf
            elif shutil.which(ar_conf):
                return shutil.which(ar_conf)
            elif os.path.basename(ar_conf) == ar_conf:
                # 相对名（如 "ar"）视为可用 basename，交由 PATH 解析
                pass
            # stale 绝对路径不直接返回，继续向下回退
        cc = self._cc()
        compiler_dir = os.path.dirname(cc)
        # 1) 与编译器同目录的 llvm-ar / ar（原逻辑，保留）
        for candidate in ("llvm-ar", "ar"):
            path = os.path.join(compiler_dir, candidate)
            if compiler_dir and os.path.isfile(path):
                return path
        # 2) PATH 中查找（真机 PATH 由 hmbs/ profile 注入，
        #    ar 可能不在编译器同目录而在 /usr/local/bin 或 SDK llvm/bin）
        for candidate in ("llvm-ar", "ar"):
            found = shutil.which(candidate)
            if found:
                return found
        # 3) 问编译器：clang/gcc 的 -print-prog-name 能给出配套 archiver
        if cc:
            for prog in ("llvm-ar", "ar"):
                try:
                    out = subprocess.run(
                        [cc, "-print-prog-name=" + prog],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=15,
                    )
                    name = (out.stdout or "").strip().splitlines()
                    name = name[0].strip() if name else ""
                    if name and os.path.isabs(name) and os.path.isfile(name):
                        return name
                    if name and shutil.which(name):
                        return shutil.which(name)
                except Exception:
                    pass
        # 4) OHOS SDK 内 llvm-ar 常见位置（不硬编码版本号，动态推导）：
        #    profile 指向 /data/service/hnp/bin/clang，而真机 SDK 在
        #    /data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/llvm-ar。
        #    用 glob 动态收集，避免写死 SDK 版本号。
        for pattern in (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/llvm-ar",
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/ar",
            "/data/service/hnp/*/llvm/bin/llvm-ar",
        ):
            for hit in sorted(glob.glob(pattern)):
                if os.path.isfile(hit):
                    return hit
        # 5) 最后回退 basename，交由 buildenv PATH 在 self.run 时解析；
        #    若真机 PATH 确实无 ar，shell 会报明确错误而非静默跳过。
        #    （呼应 mpfit 经验：永不返回不存在的绝对路径）
        if shutil.which("ar") is None:
            self.output.warning(
                "ar/llvm-ar not found in PATH; falling back to 'ar' basename "
                "so the failure surfaces from the shell"
            )
        return "ar"

    def _sofa_src_dir(self):
        candidates = [
            os.path.join(self.source_folder, "20231011", "c", "src"),
            os.path.join(self.source_folder, "c", "src"),
            os.path.join(self.source_folder, "src"),
            self.source_folder,
        ]
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "sofa.h")) and os.path.isfile(
                os.path.join(candidate, "t_sofa_c.c")
            ):
                return candidate
        matches = glob.glob(
            os.path.join(self.source_folder, "**", "t_sofa_c.c"), recursive=True
        )
        if matches:
            return os.path.dirname(matches[0])
        raise ConanInvalidConfiguration(
            "SOFA source layout not recognised: "
            "sofa.h/t_sofa_c.c not found under %s" % self.source_folder
        )

    def _get_license(self, src_dir):
        header = load(self, os.path.join(src_dir, "sofa.h"))
        begin = header.find("/*----------------------------------------------------------------------")
        if begin >= 0:
            return header[begin:]
        return header

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        ar = self._ar()
        src_dir = self._sofa_src_dir()
        os.makedirs(self.build_folder, exist_ok=True)

        sources = sorted(glob.glob(os.path.join(src_dir, "*.c")))
        sources = [s for s in sources if os.path.basename(s) != "t_sofa_c.c"]
        if not sources:
            raise ConanInvalidConfiguration(
                "no SOFA C sources found in %s" % src_dir
            )

        use_fpic = self.options.shared or self.options.get_safe("fPIC")
        fpic_flag = "-fPIC" if use_fpic else ""
        objects = []
        for src in sources:
            obj = os.path.join(
                self.build_folder, os.path.basename(src)[:-2] + ".o"
            )
            self.run(
                "{cc} -c -O2 -Wall {fpic} -I{inc} {src} -o {obj}".format(
                    cc=shlex.quote(cc),
                    fpic=fpic_flag,
                    inc=shlex.quote(src_dir),
                    src=shlex.quote(src),
                    obj=shlex.quote(obj),
                ),
                cwd=self.build_folder,
            )
            objects.append(obj)

        if self.options.shared:
            self.run(
                "{cc} -shared -o libsofa_c.so {objs} -lm".format(
                    cc=shlex.quote(cc),
                    objs=" ".join(shlex.quote(o) for o in objects),
                ),
                cwd=self.build_folder,
            )
        else:
            self.run(
                "{ar} rcs libsofa_c.a {objs}".format(
                    ar=shlex.quote(ar),
                    objs=" ".join(shlex.quote(o) for o in objects),
                ),
                cwd=self.build_folder,
            )

        # ── 上游官方测试: t_sofa_c 自检程序 ──
        # 上游仅注册 1 个 testbed 程序。按上游 makefile 的 check 语义编译并运行:
        # 成功时打印 "t_sofa_c validation successful" 且退出码为 0, 失败时打印
        # "... validation failed!" 且退出码非 0。输出落盘为确定性日志源。
        lib_arg = (
            "libsofa_c.so"
            if self.options.shared
            else "libsofa_c.a"
        )
        test_bin = os.path.join(self.build_folder, "t_sofa_c")
        self.run(
            "{cc} -O2 -I{inc} {test_src} {lib} -lm -o {bin}".format(
                cc=shlex.quote(cc),
                inc=shlex.quote(src_dir),
                test_src=shlex.quote(os.path.join(src_dir, "t_sofa_c.c")),
                lib=shlex.quote(os.path.join(self.build_folder, lib_arg)),
                bin=shlex.quote(test_bin),
            ),
            cwd=self.build_folder,
        )
        test_log = os.path.join(self.build_folder, "t_sofa_c.log")
        rc = self.run(
            "./t_sofa_c > {log} 2>&1".format(log=shlex.quote(test_log)),
            cwd=self.build_folder,
            ignore_errors=True,
        )
        log_text = ""
        if os.path.isfile(test_log):
            with open(test_log, "r", encoding="utf-8", errors="replace") as handle:
                log_text = handle.read()
        # 单一 testbed 程序: discovered=1; 是否执行以二进制实际运行为准;
        # 通过与否以退出码 + 规范成功行为双重判定。
        ok = rc == 0 and "t_sofa_c validation successful" in log_text
        upstream_result = {
            "status": "passed" if ok else "failed",
            "framework": "t_sofa_c",
            "command": "./t_sofa_c",
            "discovered": 1,
            "executed": 1,
            "passed": 1 if ok else 0,
            "failed": 0 if ok else 1,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result)
        )
        if not ok:
            raise ConanInvalidConfiguration(
                "upstream t_sofa_c validation failed "
                "(rc=%s, see t_sofa_c.log)" % rc
            )

    def package(self):
        src_dir = self._sofa_src_dir()
        copy(
            self,
            "sofa.h",
            src=src_dir,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "sofam.h",
            src=src_dir,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libsofa_c.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "libsofa_c.so*",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        save(
            self,
            os.path.join(self.package_folder, "licenses", "LICENSE"),
            self._get_license(src_dir),
        )

    def package_info(self):
        self.cpp_info.libs = ["sofa_c"]
        self.cpp_info.set_property("cmake_file_name", "sofa")
        self.cpp_info.set_property("cmake_target_name", "sofa::sofa")
        self.cpp_info.set_property("pkg_config_name", "sofa")
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.append("m")
