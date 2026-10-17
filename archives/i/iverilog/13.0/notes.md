# iverilog 13.0 适配笔记

## 基本信息
- 软件: iverilog（Icarus Verilog）13.0，tag `v13_0`（注意下划线）
- 构建系统: autotools（`configure` + `Makefile.in`）
- 编译日期: 2026-09-16；编译器: OHOS clang 15 / aarch64-linux-ohos；libc++
- 扁平引用: `iverilog/13.0`；归档: `archives/i/iverilog/13.0`

## 依赖
- 强制生成工具: `bison/3.8.2`、`flex/2.6.4`、`gperf/3.3`（源码只带 `.y/.lex/.gperf`，不可省）
- 可选库: `readline/8.3`（传递 ncurses 6.6）、`zlib/1.3.1`、`bzip2/1.0.8`
- 系统: pthread、dl

## 构建要点（本地交叉 `conan create` EXIT=0）
1. `build_requirements()`：非交叉（CI 原生）时 `tool_requires` bison/flex/gperf（注册表有 OHOS aarch64 二进制）；交叉构建改用宿主 PATH 上的 bison/flex/gperf。
2. **configure 传 `LIBS=`**：iverilog `configure.ac:17 AX_PROG_CC_FOR_BUILD` 的“编译器可用”检查用全局 `LIBS` 链接本机 gcc；`AutotoolsDeps` 注入的目标库（aarch64 的 `-lreadline/-lbz2/-lz`）会让本机 gcc 链接失败。清空 `LIBS` 后检查通过；`CPPFLAGS/LDFLAGS` 保留，configure 的 `AC_CHECK_LIB` 仍能定位目标库。
3. **make 时显式静态链接顺序**：注册表 readline/ncurses 只有静态库（ncurses 配方禁止 shared），且 `LIBS=` 清空后 configure 的 `-lreadline` 探测无法解析 readline 里的 ncurses 符号 → `make LIBS=-lreadline -lhistory -lbz2 -lz -lformw -lmenuw -lpanelw -lncursesw -lpthread`。
4. **CI 设备的 config.guess 不可用**：OHOS worker 上 `config.guess` 在沙箱 tmp 目录编译 `dummy.c` 报 `Permission denied` → `configure: error: cannot guess build type`；必须显式传 `--build=`/`--host=`（CI 原生两者同为 `aarch64-linux-ohos`；WSL 为 `x86_64-pc-linux-gnu` + `aarch64-linux-ohos`）。
5. **静态 zlib/bzip2 不能进共享 VPI 模块**：注册表 `zlib/1.3.1` 仅静态且**非 PIC**（`z_errmsg ... recompile with -fPIC`）、`bzip2/1.0.8` 仅静态 → `system.vpi` 无法链接，运行 vvp 时 `$display` 报 `gzclose: symbol not found`。默认关闭 `with_zlib`/`with_bz2`（readline 静态是 PIC，可保留）；并在 generate() 用 `ac_cv_lib_z_gzwrite=no` / `ac_cv_lib_bz2_BZ2_bzdopen=no`（含 header 缓存变量）关闭 configure 的自动探测，避免模块引用这些符号。
6. **`make LIBS=...` 的传参陷阱**：Conan `Autotools.make` 把参数用空格 join 后经 shell 执行，含空格的 `LIBS=` 在递归 sub-make 中被拆开（`system.vpi` 只拿到 `-lreadline`）→ 必须对空格转义（`replace(" ", "\\ ")`）。
7. **运行期模块路径**：iverilog 把模块路径编译成 `$(prefix)/lib/ivl`；conan 用 `--prefix=/` + `make install DESTDIR=<pkg>`，故实际在 `<pkg>/lib/ivl` → 运行需 `-B <pkg>/lib/ivl`（test_package 已显式传）。
5. 上游测试：`make check`（`examples/hello.vl` 冒烟，`build()` 在 `can_run()` 时执行）；真回归是仓内 `ivtest/`（`vvp_reg.py` 驱动，37 个条目；另有 csh 脚本 `regress`→perl `vvp_reg.pl`）。

## 本地交叉命令（宿主工具）
```bash
# 宿主 bison/flex/gperf/m4 由 apt-get download + dpkg-deb -x 解到 ~/.ohos/host-tools/root/usr/bin
export PATH="$HOME/.ohos/host-tools/root/usr/bin:$PATH"
export BISON_PKGDATADIR="$HOME/.ohos/host-tools/root/usr/share/bison"
export M4="$HOME/.ohos/host-tools/root/usr/bin/m4"
conan create archives/i/iverilog/13.0 -pr:h=$PROF_AARCH64 -pr:b=default
```
- 结果：**CREATE_EXIT=0**（编译 iverilog/vvp/iverilog-vpi + `lib/ivl/*` + `libvpi.a`；test_package 交叉跳过执行）
- 日志：`/mnt/e/dsh working/tasks/iverilog-13.0-2026-09-16/logs/036-conan-create-7.log`

## 踩坑记录
1. `bison` 数据文件缺失：deb 解包的 bison 编译期写死 `/usr/share/bison` → 需 `BISON_PKGDATADIR=<extract>/usr/share/bison`。
2. `bison: m4 subprocess failed`：bison 找不到 m4 → 显式 `M4=<extract>/usr/bin/m4`。
3. `configure L1`：`TMPDIR` 之外无特殊要求；`AutotoolsDeps` 的 `LIBS` 是本次最大坑（见构建要点 2）。

## 交付物
- `bin/iverilog`、`bin/vvp`（aarch64 ELF）、`bin/iverilog-vpi`（脚本）
- `lib/ivl/`（编译器后端 ivl/ivlpp + 目标配置）、`lib/libvpi.a`、`include/iverilog/`
- `share/man/`（man 手册）

## 状态
- 本地交叉：`conan create` EXIT=0、`conan-verify` G0/G1/G2/G3 PASS、`finish` W3 通过（`.ci-result.json` exit_code=0）；等人工评审/合入。
---

**编译结束**: 2026-09-16 22:18
**最终状态**: built
