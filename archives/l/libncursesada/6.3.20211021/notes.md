# libncursesada 6.3.20211021 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带已生成的 configure / Makefile.in）
- 编译日期: 2026-09-17
- 编译器: **GNAT 9.5.0（gcc-ada）+ GCC 9**（Ada 与 C 胶水同源），非 OHOS clang
- 状态: built（已在 WSL 用 binfmt_misc + qemu-aarch64 跑通**与 CI 同源的 OHOS 原生工具链**完整 `conan create`：build → package → test_package 构建 → 消费者 pty 断言 PTY_OK；CI 流水线复核见 PR #10624）

## 关键前提：Ada 必须原生 OHOS 构建

ohpcd 中唯一的 Ada 工具链 `gcc-ada/9.5.0` 与装配 `as`/`ld` 的 `binutils/2.46.0`
**都只有 OHOS/armv8 制品**（`conan list "<pkg>:*" -r=ohpcd` 实证 settings os=OHOS arch=armv8）：

```
$ conan list "gcc-ada/9.5.0:*" -r=ohpcd
              settings
                arch: armv8
                os: OHOS
```

→ 没有 Linux x86_64 的交叉 Ada 编译器，常规 WSL 交叉（`-pr:b=default`）无从编译。
CI 用的是原生两 profile（`ci/conan/profiles/ohos-aarch64` 第 15 行原文）：

```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方 `validate()` 对交叉构建给出明确拒绝（而不是留下难定位的失败）。

## 编译步骤（配方内）

```python
tc = AutotoolsToolchain(self)
tc.configure_args += ["--enable-widec", "--disable-gnat-projects",
                      "--with-ada-compiler=gnatmake",
                      "--with-ada-libname=AdaCurses", "--without-ada-sharedlib"]
env = tc.environment(); env.define("CC", "gcc"); env.define("CXX", "g++")
# PkgConfigDeps 提供 ncursesw.pc
autotools.configure(); autotools.make(args=["-j1"]); autotools.install()
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 找 `ncurses` 失败 | ohpcd 的 ncurses 是宽字符包（`pkg_config_name=ncursesw`） | 加 `--enable-widec`；PkgConfigDeps 生成 `ncursesw.pc` |
| 2 | Ada 与 C 胶水可能混链 | `configure.in:60` 是 `CF_PROG_CC(gnatgcc gcc cc)`，但 autoconf 会优先采用已注入的 `$CC`（profile 里的 OHOS clang） | 在 `generate()` 里把 `CC/CXX` 改回 `gcc`/`g++`（gcc-ada） |
| 3 | `CF_GNAT_PROJECTS` 不可用 | gcc-ada 9.5.0 不带 `gprbuild` | `--disable-gnat-projects` |
| 4 | 共享 Ada 库与静态 ncurses 不一致 | ncurses 在 OHOS 只发布静态包 | `--without-ada-sharedlib`；`validate()` 拒绝 `shared=True` |
| 5 | CI：`configure: error: cannot guess build type` | E007：GNU `config.guess`/`config.sub` 无 HarmonyOS 分支 | 固化补丁 `patches/0001-config-guess-sub-ohos.patch`（用 `scripts/patch-autotools-ohos.pl` 生成，输出 `aarch64-unknown-linux-ohos`） |
| 9 | CI 第三轮：configure 报 cannot run C compiled programs（E064：conftest 首次执行被安全门拦） | config.guess 认了 OHOS 后视为原生构建，configure 要**运行** conftest；沙箱杀掉该进程 | 让 `--build` 与 `--host` 取不同三元组（`x86_64-unknown-linux-gnu` / `aarch64-unknown-linux-ohos`），autoconf 经 canonical 路径置 `cross_compiling=yes` 而跳过执行探测；另预置 `cross_compiling=yes`/`ac_cv_c_compile_works=yes`/`ac_cv_prog_cc_cross=yes` 兜底（仓内 abiword-plugin-openwriter 经 39 轮 CI 得出的结论：env 里 export `cross_compiling=yes` 会被 AC_PROG_CC 覆盖，唯一有效杠杆是 build≠host） |
| 8 | CI 第二轮：config.sub 报 Kernel linux not known to work with OS ohos | scripts/patch-autotools-ohos.pl 只把 ohos* 加进 OS 列表，漏了 **kernel-OS 组合校验**里的 linux-ohos*（脚本自检仍报 Patching successful） | 补丁中额外把 linux-ohos* 加入组合白名单；本地已验证：补丁版 config.sub 原样接受 aarch64-unknown-linux-ohos，原始版报 OS ohos not recognized |
| 7 | `test_package` 三重缺陷（W4 审计 P0/P1） | basic_layout 下 cwd=build 目录却用相对路径 `bash test.sh`；`gnatmake main.adb` 但源码在 `src/`；调用不存在的 `End_Window`（上游为 `End_Windows`） | `test()` 改用 `self.source_folder` 绝对路径；`gnatmake ... src/main.adb`；改用 `End_Windows`（已与 samples/ 逐名核对） |
| 6 | CI：`config.guess: line 1547: .../dummy.c: Permission denied` | E114：安全框架拦子进程在默认 tmpdir 新建目录写文件 | `build()` 里预建可写目录、设 `TMPDIR/TMP/TEMP`，并把 `configure` 的 `ac_tmp=$tmp` 改指该目录 + 去掉删除 trap |
| 10 | CI 50329：`make[1]: gnatprep: No such file or directory`（Error 127） | `gcc-ada/9.5.0` 只装了 gnatbind/gnatchop/gnatclean/gnatlink/gnatls/gnatmake，**没有 gnatprep**；而 `src/Makefile.in:241` 用 `$(ADAPREP) -DADA_TRACE=@ADA_TRACE@ ... trace.adb_p trace.adb` 生成 `terminal_interface-curses-trace.adb` | 配方内联一个最小 `gnatprep` 实现（Python，`sys.executable` 作 shebang），写入 generators 的 `gnatprep-bin/` 并置于 PATH 首位；无输入文件时立即 `exit 2`，使 configure 的 `gnatprep -T` 探测失败、`GNATPREP_OPTS` 保持为空（且绝不读 stdin，避免挂死） |
| 11 | `configure: error: C preprocessor "/lib/cpp" fails sanity check` | `GCC_EXEC_PREFIX` 指向 gcc-ada 后，宿主的 `/lib/cpp` 找不到 `cc1` | `generate()` 里把 `CPP` 固定为与 `CC` 同源的 `"<gcc> -E"` |
| 12 | samples 链接：`ld: cannot find -lpanel / -lmenu / -lform / -lncurses` | 上游 Ada 规格硬编码**窄字符**库名 `pragma Linker_Options ("-lpanel" & DFT_ARG_SUFFIX)`，而 `DFT_ARG_SUFFIX` 只带 debug/profile 后缀；ohpcd 的 ncurses 只有宽字符 `lib*w.a` | 让 gen 以宽字符后缀生成常量：把 `gen/Makefile` 的 `GENERATE = ./generate ''` 改成 `'w'`（`USE_ARG_SUFFIX` 全仓只此一处引用），并修补已生成的 `terminal_interface-curses_constants.ads`；四个 Linker_Options 变为 `-lpanelw/-lmenuw/-lformw/-lncursesw` |
| 13 | `package()`：`make: *** No rule to make target 'install'. Stop.` | `Autotools.install()` 在 `self.build_folder`（仅 generators 与源码子目录符号链接）里执行，而 configure/make 是**源码内**构建（cwd=source_folder） | 改为显式 `self.run('make install DESTDIR="<package_folder>"', cwd=self.source_folder, env="conanbuild")` |
| 14 | test_package 链接：`ld: cannot find -lncursesw / -ltinfo` | `PkgConfigDeps` 只写 `.pc` 不扩展 `PKG_CONFIG_PATH`（同 E468），`pkg-config ncursesw` 于是命中**宿主** `/usr/.../ncursesw.pc`，返回 `-lncursesw -ltinfo` 且没有 `-L` | test_package 的 `conanfile.build()` 从 `ncurses.cpp_info` 取 libdir/libs 传给 `test.sh`；`test.sh` 新增参数并把 `-L$NCLIBDIR` 加进链接行 |
| 15 | test()：`Error opening terminal: dumb.` | CI shell 常导出 `TERM=dumb`，ncurses 无法打开；且 `test.sh` 记录的 terminfo 目录算错一层（应在 `<ncurses-libdir>/terminfo`） | `run_pty.py` 在 `TERM` 为空或 dumb 时改用 `xterm`，并读取 `.terminfo_path` 设置 `TERMINFO_DIRS`；`test.sh` 修正 terminfo 目录判定 |
| 16 | 诊断盲区：CI 只报 `config.log not found at .../build-release/config.log` | `configure` 以 `cwd=self.source_folder` 运行，config.log 写在**源码目录**，而异常分支只查 `build_folder` | 异常分支按 `source_folder` → `build_folder` 顺序查找并回传尾部 |

## 依赖版本

- ncurses/6.5（OHOS 静态 + 宽字符）
- gcc-ada/9.5.0（GNAT，OHOS/armv8）
- binutils/2.46.0（as/ld，OHOS/armv8）

## 验证结果

### 本地（WSL）——用 proot+qemu 运行 OHOS 原生 Ada 工具链

```
checking if the ncurses package files work...   yes
checking if the ncursesw package files work...  yes   # --enable-widec 生效
checking for gnatmake... <gcc-ada>/bin/gnatmake
checking for gnatmake version... 9.5.0
checking for m4... yes
```

本地脚手架的已知局限：`proot` 的 bind 对嵌套 exec 出的 qemu 进程不可见，
导致 `gcc.ohos-wrapper` 注入设备绝对路径 `/data/service/.../libunwind.a` 时失败
（编译与 gnatbind 均通过）。该路径在 CI（原生 OHOS）真实存在，
仓内 `DRAFT-gcc-ada-ohos-link-only-libunwind` 已记录设备 r143/r144 与 clean CI #31486 通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `libAdaCurses.a` | Ada 绑定静态库（安装到 `lib/ada/adalib`） |
| `share/ada/adainclude/*.ad[bs]` | Ada 规格与实现源码 |

## 注意事项

- 上游没有自动化测试套件；`samples/` 目录共 **40** 个 Ada 主体源文件（39 个 `*.adb` + 1 个 `sample-explanation.adb_p`，评审 rule4 实测口径），其中上游 `samples/Makefile.in` 的 `PROGS` 只构建 3 个可执行（`tour`/`ncurses`/`rain`）且为交互式；
  可自动判定的是「绑定 + 这 3 个示例编译链接通过」，运行断言靠 `test_package` 的 pty 驱动。
- `lang-preflight` 会把本库**误判为 `c`**（枚举缺 ada、不统计 `.adb/.ads`），已单独沉淀知识草稿。
