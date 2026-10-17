# E-DRAFT E687: 纯 make 包适配四件套 —— 命令行钉死 flags、静态 BLAS 直链过 L2、CLI 补 --version、按数值口径判上游测试

- **触发实例**：coinor-csdp 6.2.0 全新包适配（2026-09-23，任务卡 6548·火种 10，分支 `feat/coinor-csdp-6.2.0`）
- **上游**：`https://github.com/coin-or/Csdp` tag `releases/6.2.0`（sha256 `3d341974…0b32f`）
- **类别**：纯 make / 构建变量所有权 / 交付 ELF 形态 / 平台 smoke 门禁 / 上游参考输出陈旧
- **严重度**：2（每个机制都确定性复现；单看任一条报错都会把排查方向带偏）

> 逐字证据：`$HOME/tmp/coinor-csdp-6.2.0/e687-repro.out`（三段探针）、
> `$HOME/tmp/coinor-csdp-6.2.0/e687-make.out`（钉死 flags 的 37 行编译/链接行）。

## 症状（四类，报错形态互不相似）

1. 上游 Makefile 把 `export CFLAGS=-m64 -march=native -mtune=native -Ofast -fopenmp …`
   与 `export LIBS=-static … -llapack -lblas -lm` **写死**；同机 CI worker 环境里还泄漏着
   `CFLAGS/CXXFLAGS='-fPIC -O2'`（coinor-cbc !11827 当日实测踩坑 → ositests Segfault）。
2. 用动态 `-lopenblas` 链出的 CLI，在 L2 门禁形态（裸 `<bin> --version`，不 source conanrun）下：
   `Error loading shared library libopenblas.so.0` → **rc=127**，L2「所有二进制文件均无法运行」⇒ FAIL。
3. 上游 5 个 CLI 都没有 `--version` 分支：`csdp --version` 把它当输入文件（`Giving up.` exit 201）；
   `theta --version` 通过 argc 检查（2..2）后 `fopen(NULL)` → `fscanf` 未判空 → 段错误。
4. `test/*.out` 与 `test/*.correct` 直接 diff 恒不相等：耗时行随机器浮动，且
   `g50.correct` 缺当前源码必打的第 2 行 `CSDP 6.2.0` 横幅。

## 根因（三个独立机制叠加）

### ① flags 的所有权错位：makefile 定义 > 环境 > 内置

GNU make 优先级是**命令行 > makefile 定义 > 环境 > 内置默认**。上游用 `export CFLAGS=…`
写死后，环境里的（无论是 worker 泄漏的还是我们自己 export 的）都盖不掉它；反过来，
配方若把 flags 交给环境决定，"设备上验证过的配置"与"CI worker 实际用的配置"就可能分叉——
coinor-cbc 的分叉点是 `#ifdef NDEBUG` 编译期行为，最终报出来的是**测试段错误**，
与 flags 毫无字面关系，单轮归因 75–100min。

**唯一确定性解法是在 make 命令行上钉死**：

```sh
make CC='<clang>' CXX='<clang++>' \
     CFLAGS='-O2 -fPIC -DBIT64 -DUSESIGTERM -DUSEGETTIME -Wall -I../include' \
     CXXFLAGS='-O2 -fPIC' \
     LIBS='-L../lib -lsdp <openblas>/lib/libopenblas.a -lm' \
     MAKEFLAGS= all
```

子 make 的传递不靠 `$(MAKE) -C`（上游写的是 `cd lib; make libsdp.a` 裸命令），
而靠 **GNU make 把命令行变量导出到 recipe 环境**——实测四层（lib/solver/theta/example）
37 行编译/链接全部携带探针宏 `-DPROBE_E687`。

剔除项与理由：`-march=native -mtune=native`（设备与 worker 指令集不同，不可复现）、
`-fopenmp -DUSEOPENMP -DSETNUMTHREADS`（worker 无 OpenMP 运行时保证；串行路径是上游
自带正确代码）、`-m64`（aarch64 默认）、`-ansi`（隐藏 POSIX 原型）。
保留 `-DBIT64`（64 位索引路径）与 `-DUSESIGTERM -DUSEGETTIME`（与 `.correct` 输出形态一致）。
`-O2 -fPIC` 取**与 worker 泄漏值同向**的本机验证值 ⇒ 两侧天然同配置。

### ② 动态 BLAS 撞 L2 裸跑门禁；上游 `-static` 在 OHOS 又必败

L2 门禁（`scripts/ohc/conan_verify.py::gate_l2_smoke_test`）对 bin/ 下每个 ELF 直接
`subprocess [bin, "--version"]`，**不带任何 conanrun 环境**：

```text
$ LD_LIBRARY_PATH= ./t_dyn            # -lopenblas 链出
Error loading shared library libopenblas.so.0: No such file or directory
rc=127
$ LD_LIBRARY_PATH= ./t_sta            # libopenblas.a 直链
ddot=11.000000                        # rc=0，readelf -d NEEDED=1（只剩 libc.so）
```

而照抄上游 `-static` 在 OHOS（没有静态 libc）必败。交集解法 = **只把依赖归档静态直链**：
`LIBS` 里写 `<dep>/lib/libX.a` 绝对路径而不是 `-lX`。两个前置核对：
1. `llvm-nm` 确认所需符号在 `.a` 里（本包 10 个 BLAS/LAPACK 符号齐）；
2. 实链确认无 Fortran/OpenMP 运行时未决符号（libopenblas.a 直链通过；`.so` 才在内部
   解析 flang 运行时，所以「.so 能跑」不等于「.a 能链」，必须实链）。

好处同时覆盖 P009（不存在 RPATH 覆盖问题）、P012（静态优先）与 `conanrun` 缺失类假失败。

### ③ 平台 smoke 的 `--version` 约定 vs 2016 年前的 argv-as-filename CLI

补丁必须插在 **argc 检查之前**（theta 的检查是 `(argc < 2) || (argc > 2)`，
`--version` 恰好通过检查走进 `fopen(NULL)`）。打印与 usage 横幅同源的
`CSDP 6.2.0`，L2 取首行展示即为版本行，test_package 同时断言 rc==0 与 `6.2.0` 子串
（版本自报一致性）。五个工具同族处理（csdp/theta/complement/rand_graph/graphtoprob），
`refresh-patch --auto` 逐文件生成（tracker 精准模式，dry-run `-p1` 已过）。

### ④ `.correct` 参考输出会陈旧 ⇒ 判据必须退回上游自述的数值口径

`test/Makefile` 注释原文：“The optimal values should agree to **six digits or more**,
and the **DIMACS errors should all be smaller than 1.0e-6**”。这就是上游给的判据：
目标值行比对（6 位有效数字）+ DIMACS 六项阈值，**不是整文件 diff**。
`g50.correct` 缺横幅的原因：`lib/sdp.c` 在 `printlevel >= 1` 时打印 `CSDP 6.2.0`，
theta 与 csdp 走同一条 `easy_sdp → sdp` 路径（`theta1.correct` 第 1 行就有该横幅）——
同一份源码的两个参考文件不自洽，字节比对判据自身就站不住。

## 处方（配方侧四步）

1. **make 命令行钉死** `CC/CXX/CFLAGS/CXXFLAGS/LIBS/MAKEFLAGS=`（值 = 本机验证值）。
2. **依赖数学库静态归档直链**（`<dep>/lib/libX.a`），交付 ELF `NEEDED` 收敛到 libc.so 后
   再过 L2 裸跑；`transitive_libs=True` 把该归档传给静态消费者。
3. **CLI 补 `--version`/`--help`**（argc 检查前），refresh-patch + conandata 登记；
   补丁只增不改（+20/+21 行每文件，无平台宏，PF5 安全）。
4. **上游测试在 `build()` 内 Python 断言数值口径**（目标值 == .correct、DIMACS < 1e-6、
   含 `Success` 行），N 口径按 `test/Makefile` 注册目标数清点（本包 N=2，上游注释自证
   "only two tests"）。附：OHOS 交付 ELF 跑测试前 `binary-sign-tool` 自签（P017），
   `package()` 幂等兜底（实测重复自签 `.codesign` 仍为 1 节）。

## 复现命令

```sh
sh $HOME/tmp/coinor-csdp-6.2.0/e687-repro.sh
# 期望（rc=0，ALL PASS）：
#   [A] 编译/链接行携带 -DPROBE_E687 次数: 37（命令行变量下传四层子 make）
#   [B] 动态 -lopenblas 裸跑 rc=127｜静态 .a 直链裸跑 rc=0，NEEDED=1（libc.so）
#   [C] 5 个 CLI --version rc=0 输出 "CSDP 6.2.0"
```

## 相关

- `notes/device-facts.md` §一.4（harmonybrew PATH 掩盖 CI 缺口 ⇒「设备全绿 ≠ CI 绿」）、
  §一.14（OHOS Python 裸命令名）、§二.12/13（干净轮与 finish 覆盖日志）
- `DRAFT-E628-rtklib-handwritten-makefile-multi-app-adaptation`（raw makefile 家族的
  源码布局与 N 口径）、`DRAFT-8958-clthreads-makefile-stage-install-shadow`
  （`-march=native` 交叉坑与配方侧打包）、`DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing`
  （raw makefile + OHOS CLI 签名）
- 原则：P006（flags 改动留痕）、P009（RPATH 覆盖——本条用静态直链绕开）、
  P012（静态库优先）、P017（ELF 签名与运行环境匹配）
- 同日教训：coinor-cbc !11827 CI worker 环境泄漏 `CFLAGS/CXXFLAGS='-fPIC -O2'`
  ⇒ 配方不钉 flags 的代价面（ositests Segfault、`#ifdef NDEBUG` 编译期分叉）
