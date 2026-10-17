# DRAFT-iverilog-13.0-autotools-host-libs-forbuild-static-readline

> 类型: 跨库适配知识（autotools 交叉构建）
> 来源软件: **iverilog 13.0**（ohpcd 任务 7551）
> 状态: DRAFT（同 stem 配对 `DRAFT-iverilog-13.0-autotools-host-libs-forbuild-static-readline.kv`）
> 日期: 2026-09-16

---

## 一、背景

iverilog（Icarus Verilog）是 autotools 项目，在 WSL 上以 OHOS cross profile 适配时连续撞到三类问题；
它们不是 iverilog 独有，而是 **autotools + 交叉 + 静态依赖库** 的共性形态：

| # | 现象 | 一句话根因 |
|---|------|-----------|
| ① | `configure: error: C compiler cannot create executables` | 项目自带的 _FOR_BUILD 宏用全局 `LIBS` 链接**本机**编译器，而 `LIBS` 里是 conan 注入的**目标库** |
| ② | `configure: error: cannot run C compiled programs` | host/build 用同一 profile，conan 判定非交叉、不传 `--host`，configure 便尝试运行 aarch64 程序 |
| ③ | `ld.lld: undefined symbol: add_history`（build 与 `make install` 两处） | readline/ncurses 只有静态库，清空 `LIBS` 后 `AC_CHECK_LIB` 探测失败，最终链接缺 `-lreadline/-lhistory/-lncursesw` |

附加：bison/flex/gperf 是源码生成工具（iverilog 只带 `.y/.lex/.gperf`）；当它们由非标准路径提供时，
`bison` 需要 `BISON_PKGDATADIR`（数据文件）与 `M4`（m4 解释器）指向同目录，否则 `m4 subprocess failed`。

---

## 二、复现命令与原始报错

```bash
# 交叉构建（参考）
conan create archives/<letter>/<pkg>/<ver> -pr:h=<ohos-cross-profile> -pr:b=default
```

### ① for-build 检查读到目标库 LIBS
```
checking whether the C compiler works... no
configure: error: C compiler cannot create executables
# config.log 关键行（本机 gcc 链接 aarch64 目标库）：
gcc -g -O2 conftest.c -lreadline -lhistory -lbz2 -lz -lformw -lmenuw -lpanelw -lncursesw
/usr/bin/ld: cannot find -lreadline: No such file or directory
```
来源：`configure.ac:17 AX_PROG_CC_FOR_BUILD`；iverilog 的 `Makefile.in` 需要宿主编译器构建 `dosify`。

### ② 非交叉判定导致 configure 去运行目标程序
```
checking whether we are cross compiling... configure: error: cannot run C compiled programs.
If you meant to cross compile, use --host.
```
触发条件：`ci/conan/build_and_test.sh` 对 `-pr:h` 与 `-pr:b` 使用**同一个 profile**（WSL 工作流），
于是 `cross_building(self)` 为假；但编译器仍是 OHOS 交叉 clang。

### ③ 静态 readline 链接
```
ld.lld: error: undefined symbol: add_history
>>> referenced by stop.cc
>>>               stop.o:(stop_handler(int))
# 失败行（缺 -lreadline/-lhistory）：
aarch64-unknown-linux-ohos-clang++ ... -o vvp ... -lbz2 -lz -lpthread -ldl
# 且注意：make install 会重新链接（install: all），同一缺库在 package() 阶段再次出现
```

---

## 三、根因分析

1. **`AX_PROG_CC_FOR_BUILD` 与全局 `LIBS`**：autoconf-archive 的该宏为宿主编译器设置 `ac_link`，但它复用全局 `$LIBS`；conan `AutotoolsDeps` 为让目标库可被 `AC_CHECK_LIB` 发现，把 `-l...` 写进 `LIBS`，于是本机 gcc 也去链目标库 → 失败。
2. **同一 profile 的交叉盲区**：conan 以 `host != build` 判断交叉；WSL 工作流两者是同一个 OHOS profile，`cross_building` 为假 → `AutotoolsToolchain` 不追加 `--host`；configure 因此认为可运行目标程序。同一盲区还会让 `build_requirements()` 误把 **aarch64 的 bison/flex/gperf** 当本机工具使用（注册表只发布 OHOS 二进制）。
3. **静态依赖链**：`readline/8.3` + `ncurses/6.6` 在制品仓均为静态（`ncurses` 配方明确禁止 shared）。为通过 ① 而清空 `LIBS` 后，`AC_CHECK_LIB(readline, readline)` 的测试链接缺少 `-lncursesw`（readline.a 需要），探测结果为 no，`HAVE_LIBREADLINE` 未定义；但另一处探测把 `add_history` 引进来，最终链接就缺 `-lhistory/-lreadline/-lncursesw`。

---

## 四、推荐修复（recipe 层）

### ① 在 configure_args 追加 `LIBS=`
```python
tc.configure_args.append("LIBS=")   # 清空的是 configure 期间的全局 LIBS；CPPFLAGS/LDFLAGS 保留
```
`AC_CHECK_LIB` 仍能通过 `LDFLAGS` 的 `-L` 找到目标库；`AX_PROG_CC_FOR_BUILD` 的本机 gcc 链接不再带目标库。

### ② OHOS 交叉补 `--host` + 按真实机器架构决定是否用注册表生成工具
```python
if self.settings.os == "OHOS" and not any(a.startswith("--host=") for a in tc.configure_args):
    tc.configure_args.append("--host=aarch64-linux-ohos")

# build_requirements(): 只有真实 aarch64 机器（CI 原生）才用注册表 OHOS 工具
import platform
if not cross_building(self) and platform.machine().lower() in ("aarch64", "arm64"):
    self.tool_requires("bison/3.8.2")
    self.tool_requires("flex/2.6.4")
    self.tool_requires("gperf/3.3")
```

### ③ 静态链接顺序：build / check / install 三处都传
```python
def _static_libs(self):
    libs = []
    if self.options.with_readline:
        libs += ["-lreadline", "-lhistory"]
    if self.options.with_bz2:
        libs.append("-lbz2")
    if self.options.with_zlib:
        libs.append("-lz")
    if self.options.with_readline:
        libs += ["-lformw", "-lmenuw", "-lpanelw", "-lncursesw"]
    libs.append("-lpthread")
    return " ".join(libs)

libs_arg = "LIBS=" + self._static_libs()
autotools.make(args=["-j1", libs_arg])
autotools.make(target="check", args=["-j1", libs_arg])          # 上游冒烟（native 时）
autotools.install(args=[libs_arg])                              # install 会重链，必须同参
```

### ④ 生成工具的非标准路径
```bash
export BISON_PKGDATADIR=<prefix>/share/bison   # bison 数据文件
export M4=<prefix>/bin/m4                      # bison 调用 m4
```

---

## 五、验证证据（iverilog 13.0）

| 项 | 值 |
|---|---|
| 交叉 `conan create` | **EXIT=0**（`logs/036/037`）|
| `conan-verify` | **G0/G1/G2/G3 PASS**（Verdict PASS）|
| W3 本地 CI | **通过**（`.ci-result.json` exit_code=0）|
| 交付物 | `bin/iverilog`、`bin/vvp`（aarch64 ELF）、`lib/ivl/*`、`libvpi.a`、`include/iverilog/` |
| 功能测试 | test_package：`iverilog` 编译 .v → `vvp` 运行并断言输出（CI 原生活执行） |

另：iverilog 运行期模块路径被写死为 `$(prefix)/lib/ivl`，conan 用 `--prefix=/` + `DESTDIR` 安装后
需 `-B <pkg>/lib/ivl`（同类 relocation 项目可复用该判据）。

---

## 六、适用 / 不适用

- 适用：autotools 项目；`*_FOR_BUILD` 宏或配置期需要宿主编译器；host==build 的同 profile 交叉工作流；依赖 readline/ncurses 等纯静态库；`--prefix` 写死资源路径。
- 不适用：CMake/Meson 项目（机制不同，见 E092/E317 等）；依赖库为 shared（无需手动静态顺序）。

---

## 八、补充：仅在 CI 原生环境暴露的四个坑

① **config.guess 沙箱不可用**：OHOS worker 上 `config.guess` 在沙箱 tmp 编译 `dummy.c` 报 `Permission denied` → `configure: error: cannot guess build type`；显式传 `--build`/`--host`（CI 原生两者同为 `aarch64-linux-ohos`，WSL 为 `x86_64-pc-linux-gnu` + `aarch64-linux-ohos`）。

② **config.status 的 confXXXXXX 目录被拦（E114）**：`config.status` 用 `AS_TMPDIR` 在 build 目录建 `./confXXXXXX`，子进程写 `subs1.awk` 被安全框架拒绝 → 预建可写目录并把 `configure` 的 `ac_tmp=$tmp` 改指它（去掉删除 trap）。

③ **`Autotools.make` 的 LIBS 传参**：Conan 把 args 用空格 join 后经 shell 执行，含空格的 `LIBS=...` 在递归 sub-make 中被拆开（`system.vpi` 只拿到 `-lreadline`）→ 对空格转义。

④ **静态非 PIC 依赖不能进共享模块**：注册表 zlib 静态且非 PIC（`z_errmsg ... recompile with -fPIC`）、bzip2 仅静态；iverilog 无 `--with-*` 开关而是自动探测 → 用 `ac_cv_lib_z_gzwrite=no` / `ac_cv_lib_bz2_BZ2_bzdopen=no`（含 header 缓存变量）显式关闭，否则运行期 `system.vpi` dlopen 报 `gzclose: symbol not found`。

---

## 七、查重差异

- `E467`（AutotoolsDeps 把依赖闭包写进 LIBS/CPPFLAGS，干扰 autoconf 交叉判定）：讲的是 **AC_PROG_CC 交叉判定被依赖注入干扰**；本条 ① 是 `*_FOR_BUILD` 宏复用全局 `LIBS` 让**本机**编译器去链目标库，② 是同一 profile 下 `--host` 缺失、③ 是静态依赖链与 install 重链——与 E467 相邻但触发宏与层次不同。
- `E490`（autotools helper 脚本可执行位）：讲的是 `configure/config.guess/...` 的 mode，本条的 ① 是 `LIBS` 内容、② 是 `--host` 缺失、③ 是静态链接顺序，均不同层。
- `E317`（install 规则 sed 改写运行时变量）：讲的是 Makefile install 的 sed 范围，本条 ③ 是**重链**导致的缺库，判据是“install 依赖 all 会重新链接”而非 sed。
- 结论：新子类（autotools 交叉的宿主编译器检查 vs 目标库 LIBS / 同 profile 交叉盲区 / 静态依赖链与重链），接受评审合并判断。

---

*由 ohc-run.py 适配流程沉淀；证据日志见 `/mnt/e/dsh working/tasks/iverilog-13.0-2026-09-16/logs/`。*
