#!/usr/bin/env python3
"""Conan recipe — OCaml 4.14.4

OCaml uses a custom configure script (not autotools) and a bootstrap
compilation process. Key platform adaptations for OHOS:
  - config.guess patched to recognize HarmonyOS as linux-gnu
  - ASM set to 'clang -c' (not llvm-as, which expects LLVM IR)
  - TMPDIR used for configure temp directories
  - config.status patched to use mkdir instead of mktemp (OHOS permission fix)
  - boot/ocamlrun copy uses rm -f && cp (HMDFS workaround)
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file

class OcamlConan(ConanFile):
    name = "ocaml"
    version = "4.14.4"
    description = "OCaml is a functional, statically-typed language from the ML family"
    license = "LGPL-2.1"
    homepage = "https://ocaml.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # 解释器：CI 沙箱 /bin/sh 为 toybox 精简实现，无法通过 autoconf 2.69 健全性检查
    # （as_fn_success failed），必须使用 profile [buildenv] 注入的 CONFIG_SHELL（OHOS bash）。
    # 定义为类属性，build()/package() 均可用。
    shell = "${CONFIG_SHELL:-/bin/sh}"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # OCaml has no external Conan dependencies

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # OCaml uses custom configure, not autotools toolchain

    def build(self):
        apply_conandata_patches(self)
        # prefix is set to package_folder; DESTDIR staging in package() handles the rest
        prefix = self.package_folder
        # 编译器路径从 Conan conf 获取（R33，不硬编码）；默认回退 clang
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        # OHOS 下 as/ar 为 binutils 工具（GNU 汇编器/归档器），OCaml runtime 编译必需，显式注入
        asm = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("asm", "as")
        ar = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("ar", "ar")
        # config.guess/configure 需要可写的临时目录（可建子目录）：
        # 构建目录在 CI 上不可建子目录（Permission denied），TMPDIR 用系统可写目录
        tmp_dir = os.environ.get("TMPDIR", "/storage/Users/currentUser")
        if not os.path.isdir(tmp_dir) or not os.access(tmp_dir, os.W_OK):
            tmp_dir = "/storage/Users/currentUser"
        # shlex.quote 防御 conf 注入（R33 值可能含特殊字符）
        tool_env = (f"CC={shlex.quote(cc)} AS={shlex.quote(asm)} "
                    f"AR={shlex.quote(ar)} TMPDIR={shlex.quote(tmp_dir)}")
        # 解释器见类属性 self.shell（CI 沙箱 /bin/sh 为 toybox，须用 CONFIG_SHELL=OHOS bash）
        # Step 1: Run configure with --no-create to generate config.status without executing it
        # OHOS hmmac 策略拒绝直接执行带 shebang 的脚本 (EACCES/126)，须用显式解释器调用
        # autoconf 只探测 gcc/cc，须显式注入 CC 指向 OHOS Clang
        # env="conanbuild" 使 buildenv（CONFIG_SHELL/PATH/LD_LIBRARY_PATH）注入子进程
        self.run(f"{tool_env} {self.shell} ./configure --prefix={shlex.quote(prefix)} --no-create",
                 env="conanbuild")
        # Step 2: Patch config.status to fix OHOS temp directory permission issue
        # mktemp -d creates dirs with umask 077 which OHOS /bin/sh cannot write to
        # Replace with a simple mkdir-based approach
        replace_in_file(self, "config.status",
            'tmp=`(umask 077 && mktemp -d "${TMPDIR:-./}/confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"',
            'tmp="${TMPDIR:-.}/cs.$$" &&\n  rm -rf "$tmp" && mkdir -p "$tmp" && test -d "$tmp"')
        replace_in_file(self, "config.status",
            'tmp=${TMPDIR:-.}/conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            'tmp="${TMPDIR:-.}/cs.$$"\n  rm -rf "$tmp" && mkdir -p "$tmp"')
        # Step 3: Run config.status manually
        self.run(f"CC={shlex.quote(cc)} TMPDIR={shlex.quote(tmp_dir)} {self.shell} ./config.status",
                 env="conanbuild")
        # Step 4: Fix ASM: llvm-as expects LLVM IR, but OCaml generates GAS assembly.
        # 注入 AS=GNU as 时 configure 已生成正确 ASM，此替换仅在检测到 llvm-as 时生效（strict=False）
        replace_in_file(self, "Makefile.config", "ASM=llvm-as", "ASM=clang -c", strict=False)
        # Step 5: Pre-remove boot/ocamlrun to avoid HMDFS cp permission error
        boot_ocamlrun = os.path.join(self.source_folder, "boot", "ocamlrun")
        if os.path.exists(boot_ocamlrun):
            os.remove(boot_ocamlrun)
        # Step 6: Disable manpages generation (ocamldoc.opt triggers OHOS security popup)
        replace_in_file(self, "Makefile.config", "STDLIB_MANPAGES=true", "STDLIB_MANPAGES=false")
        # Step 6.5: OHOS hmmac 拒绝直接执行 shebang 脚本 + symlink 创建，修复 make 内部调用点
        # 显式解释器统一用 $(SHELL)（= CONFIG_SHELL，即 OHOS bash），避免 CI 沙箱 /bin/sh(toybox) 兼容问题
        # 6.5.1 runtime/Makefile: gen_primitives.sh 显式解释器（primitives 表生成）
        replace_in_file(self, "runtime/Makefile",
            "$(shell ./gen_primitives.sh",
            "$(shell $(SHELL) ./gen_primitives.sh")
        # 6.5.2 stdlib/Makefile: Compflags 显式解释器（多处）
        replace_in_file(self, "stdlib/Makefile",
            "$(shell ./Compflags",
            "$(shell $(SHELL) ./Compflags")
        # 6.5.3 根 Makefile: hmmac 拒绝 symlink 创建，ln -sf 改为 cp -f（上游 win32 分支即用 cp）
        replace_in_file(self, "Makefile", "LN = ln -sf", "LN = cp -f")
        # 6.5.3b tools/Makefile: 同上（install 阶段 ocamlobjinfo 等符号链接）
        replace_in_file(self, "tools/Makefile", "LN := ln -sf", "LN := cp -pf")
        # 6.5.4 根 Makefile: lambda/runtimedef.ml 由脚本生成，规则体 $^ > $@ 改为显式解释器
        replace_in_file(self, "Makefile", "\t$^ > $@", "\t$(SHELL) $^ > $@")
        # 6.5.5 根 Makefile: HMDFS 拒绝覆盖已存在文件，ocamlrun/ocamlruns 复制改为 rm -f && cp
        replace_in_file(self, "Makefile",
            "\tcp runtime/ocamlrun$(EXE) boot/ocamlrun$(EXE)",
            "\trm -f boot/ocamlrun$(EXE) && cp runtime/ocamlrun$(EXE) boot/ocamlrun$(EXE)")
        replace_in_file(self, "Makefile",
            "\tcp runtime/ocamlruns$(EXE) boot/ocamlruns$(EXE)",
            "\trm -f boot/ocamlruns$(EXE) && cp runtime/ocamlruns$(EXE) boot/ocamlruns$(EXE)")
        # Step 7: Bootstrap compilation with -j1
        # make 显式指定 SHELL=CONFIG_SHELL，使 $(shell ...) 与规则体均用 OHOS bash
        self.run(f"make -j1 SHELL=\"{self.shell}\"", env="conanbuild")

    def package(self):
        # Use temp DESTDIR to avoid nested directory structure.
        # OCaml configure set prefix=self.package_folder, so
        # make install DESTDIR=X creates files at X/<prefix>/
        dest = os.path.join(self.build_folder, "dest_install")
        self.run(f'make install DESTDIR="{dest}" SHELL="{self.shell}"', env="conanbuild")
        # Copy from dest/<prefix>/ to package_folder (top-level layout)
        prefix = self.package_folder
        src_base = os.path.join(dest, prefix.lstrip("/"))
        if not os.path.isdir(src_base):
            src_base = dest
        copy(self, "*", src_base, self.package_folder)

    def package_info(self):
        # 实际库位于 lib/ocaml/ 下（libcamlrun.a/libasmrun.a），必须显式声明 libdirs，
        # 否则下游 -L<prefix>/lib 找不到库导致链接失败
        self.cpp_info.libs = ["camlrun", "asmrun"]
        self.cpp_info.libdirs = ["lib/ocaml"]
        self.cpp_info.includedirs = ["lib/ocaml"]
        # 声明 bindirs：下游通过 env="conanbuild" 即可自动获得 ocaml bin 路径
        # （ocamlc/ocamlrun/ocamlopt 等），无需手动注入
        self.cpp_info.bindirs = ["bin"]
        # 显式将 ocaml bin 追加到下游构建环境 PATH（Conan 2 兼容）
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        # 声明 stublibs：下游运行字节码程序（ocamlrun）需加载 C stubs 动态库
        # （dllunix.so/dllthreads.so/dllcamlstr.so），CAML_LD_LIBRARY_PATH 指向 stublibs
        self.env_info.CAML_LD_LIBRARY_PATH.append(
            os.path.join(self.package_folder, "lib", "ocaml", "stublibs"))
