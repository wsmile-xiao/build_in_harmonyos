# coinor-csdp 6.2.0 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 GNU make，无 configure/CMake/meson）
- 编译日期: 2026-09-23
- 编译器: /data/service/hnp/bin/clang（OHOS clang 15, aarch64）
- 状态: built

## W0 依赖预检结论（生死关，2026-09-23 实核）

- **版本可得性**：`git ls-remote --tags https://github.com/coin-or/Csdp.git` 实证
  tag `releases/6.2.0` → `e1586e0413ef236b19abe5202f7e8392f3dd4614`。发行物取官方
  tag 归档 `https://github.com/coin-or/Csdp/archive/refs/tags/releases/6.2.0.tar.gz`
  sha256=`3d341974af1f8ed70e1a37cc896e7ae4a513375875e5b46db8e8f38b7680b32f`
  （设备 curl 实测，与 coinor-cbc 2.10.13 同源同形态取数）。`releases/download/
  …/Csdp-6.2.0.tgz` 404 属「无 dist 资产」常态，非版本缺失。
- **硬依赖**：只有 BLAS/LAPACK（INSTALL 明示），**无 coinor 兄弟包依赖**（无需前置
  任务清单）。取 openblas/0.3.34：
  - `conan install --requires=openblas/0.3.34 --build=missing -pr:h=<绝对路径 ohos-aarch64>
    -pr:b=<同>` 实测 **rc=0**（真实组合，非 conan list 口径；R35 另用
    `conan download … --only-recipe` rc=0 复核）；
  - ohpcd armv8 二进制在档（`conan list -r=ohpcd "openblas/0.3.34:*"` → arch=armv8 /
    clang 15 / os=OHOS）；
  - llvm-nm 实测 `libopenblas.a` 含 CSDP 所需 10 个符号：dpotrf/dpotri/dpotrs/
    dgemm_/dtrsm_/dgemv_/dger_/dnrm2_/ddot_/dtrmv_（含 LAPACK 三件套）。
- **平台可移植**：源码全量 grep `altivec.h|mmintrin|immintrin|xmmintrin|emmintrin|
  3dnow|arm_neon|msa.h|printf.h|register_printf_` → **零命中（rc=1）**，无 ISA 专属
  路径、无 glibc printf 钩子（libvecpf 教训项排除）。
- 分支门禁人工核对：`feat/coinor-csdp-6.2.0` 去前缀 = `coinor-csdp-6.2.0` =
  包目录名-版本（新包 `--allow-unpublished` 放行，upstream/main 无同名/子串相似包）。

## 集成口径（为什么是「命令行钉 flags + openblas 静态直链」）

1. **R33 钉死 flags（防 CI 环境泄漏，coinor-cbc !11827 教训）**：上游 Makefile 把
   `export CFLAGS=-m64 -march=native -mtune=native -Ofast -fopenmp -ansi -Wall
   -DBIT64 -DUSEOPENMP -DSETNUMTHREADS -DUSESIGTERM -DUSEGETTIME -I../include` 与
   `export LIBS=-static -L../lib -lsdp -llapack -lblas -lm` 写死。makefile 定义被
   **命令行变量覆盖**，且命令行变量会导出给 `cd lib; make` 这种子 make（设备实测：
   lib/solver/theta/example 四层编译与链接行全部取到钉死值）。钉死值（本机验证）：
   - `CFLAGS = -O2 -fPIC -DBIT64 -DUSESIGTERM -DUSEGETTIME -Wall -I../include`
   - `CXXFLAGS = -O2 -fPIC`（本包无 C++ 源，占位防泄漏）
   - `LIBS = -L../lib -lsdp <openblas>/lib/libopenblas.a -lm`
   与 CI worker 泄漏值 `-fPIC -O2` 同向 ⇒ 设备与 worker 同一份构建配置。
   剔除：`-march=native -mtune=native`（跨机不可复现）、`-fopenmp/-DUSEOPENMP/
   -DSETNUMTHREADS`（worker 无 OpenMP 运行时保证，串行路径是上游自带正确代码）、
   `-m64`（aarch64 默认）、`-ansi`（隐藏 POSIX 原型）；保留 `-DBIT64/-DUSESIGTERM/
   -DUSEGETTIME`（输出形态与 .correct 一致）。
2. **openblas 静态归档直链**：`-lopenblas` 动态形态的产物在 **L2 门禁**
   （`<bin> --version`，无 conanrun 的 LD_LIBRARY_PATH）下实测 rc=127
   （`Error loading shared library libopenblas.so.0`）；改直连 `libopenblas.a` 后
   `llvm-readelf -d` 只剩 `NEEDED libc.so`、可裸跑，且 10 个所需符号静态链接
   **无 Fortran 运行时未决符号**（实链通过）。消费者侧经 `transitive_libs=True`
   拿到 openblas 链接行。
3. **5 个 CLI 补 `--version/--help`（patches/0001–0005）**：L2 smoke 以
   `<bin> --version` 探测，上游把该参数当输入文件打开（theta `fopen(NULL)` 后
   `fscanf` 未判空），退出码非 0 ⇒ L2 必红。补丁在打开输入文件前退出，打印
   `CSDP 6.2.0`（与上游 usage 横幅同源）；顺带修复 `theta --help` 崩溃路径。
   纯新增参数分支，不改求解/测试逻辑（refresh-patch --auto 逐文件生成，dry-run -p1 已过）。
4. **OHOS 自签**：build() 在跑上游测试前对 5 个 ELF 自签（binary-sign-tool，
   coinor-cbc 同款口径）；package() 幂等兜底（实测重复自签 `.codesign` 仍为 1 节）。
5. **in-source 构建**：上游 `-L../lib -lsdp` 相对路径要求 `layout()` 为空（同族口径）；
   上游 `make install` 硬编码 `/usr/local/bin` **不调用**，package() 用 conan copy 落盘。

## 编译步骤（配方 build() 内固定序）

```bash
# 0. apply_conandata_patches（5 个 --version/--help 补丁）
# 1. make all（命令行钉死 flags，CC=clang 来自 conanbuild 的 compiler_executables）
cd <src> && . <gens>/conanbuild.sh && \
  make CC='<clang>' CXX='<clang++>' \
       CFLAGS='-O2 -fPIC -DBIT64 -DUSESIGTERM -DUSEGETTIME -Wall -I../include' \
       CXXFLAGS='-O2 -fPIC' \
       LIBS='-L../lib -lsdp <openblas>/lib/libopenblas.a -lm' MAKEFLAGS= all
# 2. OHOS 自签 5 个 CLI → make unitTest（test/Makefile → csdp theta1.dat-s / theta g50）
# 3. _check_upstream_tests()：目标值 == .correct、DIMACS 六项 < 1.0e-6、含 Success 行
```

## 上游测试口径（N=2，R51）

- **N = 2**：`test/Makefile` `all: theta1.out g50.out`，上游注释自证
  “Currently, we have only two tests to complete”。候选数法：源码无测试框架宏、
  无注册表 ⇒ 唯一口径 = makefile 注册测试目标数 = 2，无差额。
- 判据（`test/Makefile` 注释原文）：最优值 “agree to six digits or more” +
  DIMACS “all smaller than 1.0e-6”。
- **不做整文件字节比对**，两处非功能性差异：
  1. 耗时行（Elements/Factor/Other/Total time）随机器浮动；
  2. **`g50.correct` 缺 `CSDP 6.2.0` 横幅**：`lib/sdp.c` 在 `printlevel >= 1` 时打印
     该横幅，theta 与 csdp 走同一条 `easy_sdp → sdp` 路径（theta1.correct 第 1 行
     就有该横幅）⇒ g50.correct 属**上游参考输出陈旧**，登记不改。
- 实测（2026-09-23 本机，钉 flags + 静态直链）：theta1 与 g50 的
  Primal/Dual/Lovasz 目标值行与 .correct **逐字符一致**（2.3000000e+01），
  DIMACS 最大 1.00e-07 / 1.87e-07，全部 < 1.0e-6（最终采信轮日志读数）；相对不可行性尾数差异
  （theta1 1.32e-18 vs 1.11e-16）同为浮点尾数，远低于 1e-6 判据。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cc: 未找到`（init-build env-check ⚠）与子 make 用内置 `CC=cc` | 设备/worker 无 `cc` 别名；`cd lib; make` 不继承交互 shell 的隐式 CC | make **命令行**传 `CC='<clang>'`（命令行变量会导出给子 make，四层实测生效） |
| 2 | 上游 `export CFLAGS=-march=native … -fopenmp …` 若原样生效 | makefile 定义优先于环境 ⇒ CI worker 环境 flags 也盖不掉它，但**我们自己的**环境与 CI 不同会漂移；`-march=native` 跨机不可复现、`-fopenmp` 无运行时保证 | 命令行钉死 CFLAGS/CXXFLAGS/LIBS（R33，见集成口径 1） |
| 3 | `-static` 全静态链接必败 | OHOS 无静态 libc | LIBS 去 `-static`，仅对 openblas 静态归档直链 |
| 4 | `-lopenblas` 动态产物 L2 裸跑 rc=127 | `libopenblas.so.0` 无 RPATH/conanrun 注入时找不到（实测） | 直连 `<openblas>/lib/libopenblas.a`；产物 `NEEDED` 只剩 libc.so |
| 5 | `<bin> --version` 被当输入文件：theta `fopen(NULL)` 后 fscanf 段错误、其余用法退出码非 0 | 上游 CLI 无 `--version` 分支 | patches/0001–0005 补 `--version/--help`（打开输入文件前退出） |
| 6 | 消费者首版断言 `n=104 k=1` 失败 | CSDP API 语义与 SDPA 文件头顺序不同：`easy_sdp(n,k,…)` 的 **n=矩阵维度**（夹具头单个 50×50 块）、**k=约束数**（104）；example.c 的 `easy_sdp(7,2,…)` 亦为「总块维 7 / 2 约束」 | 断言改为 n=50 k=104（实测 read_prob 解析值），并在 consumer 注释里写清语义 |
| 7 | `make unitTest` 第二次报 Nothing to be done | `theta1.out:`/`g50.out:` 目标无依赖、文件已存在即视为最新 | 判读前 `rm -f test/*.out` 强制重跑（配方在干净源码树上不存在 .out，天然首跑） |
| 8 | 共享设备内存窗口 / 槽位 | 见 device-facts §一.5/§一.15 | 重活持 build_slot（BUILD_SLOTS_N=6），长等待走后台 job |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-solver-csdp.c.patch | solver/csdp.c | +string.h；argc 检查前插 `--version`/`--help` 分支 |
| 0002-theta-complement.c.patch | theta/complement.c | 同上 |
| 0003-theta-graphtoprob.c.patch | theta/graphtoprob.c | 同上（已有 string.h） |
| 0004-theta-rand_graph.c.patch | theta/rand_graph.c | 同上 |
| 0005-theta-theta.c.patch | theta/theta.c | 同上（--help 顺带修复 fopen(NULL) 崩溃路径） |

全部为**纯新增**参数处理分支（+20/+21 行/文件，0 删除），不含任何平台宏
（PF5：补丁无 `__OHOS__`）。

## 依赖版本

- openblas/0.3.34（ohpcd armv8 二进制；含 BLAS+LAPACK+CBLAS）
- 工具链：profile `ci/conan/profiles/ohos-aarch64`（clang 15 / libc++ / armv8 /
  os=OHOS 6.0，`-pr:h` 与 `-pr:b` 同传，与 CI conan create 同款）

## 验证结果

```bash
# W0 真实依赖组合（rc=0）
conan install --requires=openblas/0.3.34 --build=missing \
  -pr:h="$TARGET_REPO/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$TARGET_REPO/ci/conan/profiles/ohos-aarch64"

# 本机钉 flags 原生构建 + 上游测试（N=2）
make CC=clang CFLAGS='-O2 -fPIC -DBIT64 -DUSESIGTERM -DUSEGETTIME -Wall -I../include' \
     CXXFLAGS='-O2 -fPIC' LIBS='-L../lib -lsdp <openblas>/lib/libopenblas.a -lm' \
     MAKEFLAGS= all && rm -f test/*.out && \
make CC=clang CFLAGS='…' LIBS='…' MAKEFLAGS= unitTest
# → theta1/g50 目标值行与 .correct 逐字符一致，DIMACS max 1.00e-07 / 1.87e-07 < 1.0e-6
# → 5 个 CLI `--version`/`--help` rc=0 输出 "CSDP 6.2.0"（L2 门禁形态）

# 库消费者原生预检（test_package/test_csdp_consumer.c）
clang -O2 -fPIC -I include test_csdp_consumer.c lib/libsdp.a <openblas>/lib/libopenblas.a -lm \
  -o consumer && ./consumer test_package/theta1.dat-s
# → CONSUMER PASS: pobj=dobj=2.3000000e+01（①–⑤ 全过）

# 采信轮（干净缓存 conan create + G0–G4/L2/L4/L5）
sh tools/conan_verify_round.sh coinor-csdp 6.2.0 \
  --repo "$TARGET_REPO" --task-dir "$HOME/tmp/coinor-csdp-6.2.0"
# 逐字证据：$TASK_DIR/evidence/（conan-create.log、conan-verify-report.md、w3-local-ci.log）
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libsdp.a | 静态库（上游唯一库产物） |
| include/{blockmat,declarations,index,parameters}.h | 公共头 |
| bin/{csdp,theta,complement,rand_graph,graphtoprob} | 5 个 CLI（OHOS 自签 ELF，静态闭包，NEEDED 只有 libc.so） |
| licenses/LICENSE | CPL-1.0 |

## 注意事项

- 上游 `g50.correct` 参考输出缺 `CSDP 6.2.0` 横幅（陈旧），判据按数值口径；
  本包不改上游 .correct 文件。
- 无 OpenMP：多线程路径（`USEOPENMP/SETNUMTHREADS`）未启用，串行为上游自带
  正确代码；两测试规模小（单次求解 <0.1s），性能影响可忽略。
- 新包 PR 必带软件级 `commands.json`（4 段路径）会命中 PF9「缺版本目录层」——
  属已登记确定性误报（device-facts §10.3 / pipeline README），按 `--no-preflight
  --preflight-note` 处置并在 PR 正文留痕。
- `reports/`、`feedback/SKILL_FEEDBACK_*`、`.build-context-*` 均为工具副产物，
  按 finish 白名单忽略/还原，不入库。
