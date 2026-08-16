# flint 3.6.0 编译笔记（HarmonyOS PC · Conan autotools · 版本升级自 3.2.2）

## 定位
- 基线已有 flint 3.2.2（2026-08-10，soname libflint.so.20）；本版本升级到
  3.6.0（soname libflint.so.24，configure.ac 映射表：3.6.0 → 24.0.0）。
- 产出 libflint.so 等 1 个库，供链接与 dlopen。

## 关键适配（相对 3.2.2 的变更）
1. **config.guess / config.sub 补丁替代硬编码三元组**：
   3.2.2 在 generate() 硬编码 `--build/--host=aarch64-unknown-linux-musl`
   （反模式，见 workflow 挫折 9）。3.6.0 改为补丁 config/configfsf.guess
   （`uname -s = HarmonyOS` 时输出 `aarch64-unknown-linux-ohos`，挫折 22）
   + config/configfsf.sub（接受 linux-ohos），不再传任何 --build/--host，
   Linux 上也可正常构建（平台无关）。
2. **umask 077→022 改为补丁 0003**（HMDFS E011）：autoreconf 重新生成
   configure 的归档包路径由 build() 中的 _fix_umask() 兜底。
3. **make 并行度不再硬编码 -j20**：`tools.build:jobs` conf 优先，
   回退 `os.cpu_count()`。
4. 其余沿用 3.2.2 已验证结论：
   - `flint_cv_check_cpu_set_t=no`：FLINT 探测 cpu_set_t 只编译不链接。
     OHOS 的 musl 在头里声明了 `pthread_getaffinity_np`、也有
     `cpu_set_t`/`CPU_ZERO`，探测会通过；但 libc 里没有这个符号，
     直到消费方链接、`--no-allow-shlib-undefined` 生效时才报 undefined
     reference。预置 autoconf 的 cache 变量即可关掉，无需打源码补丁。
   - 头装在 `include/flint/`，`.pc` 的 Cflags 是 `-I${includedir}`
     （下游写 `<flint/fmpz.h>`）。
   - package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）
     链接期自签即失效，dlopen 报 Permission denied。
   - 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到
     //lib/ 死路。

## 上游测试说明（官方审查要求本地全量验证，已执行）
- 上游测试源文件 3810 个（src/*/test/t-*.c，136 个模块目录）；其中
  3592 个被 129 个模块 main driver include 注册；218 个为条件编译排除
  （x86 专用 / WANT_NTL 等）或独立构建目标。
- **设备全量执行**：128 个模块 main driver，3652 个测试用例，
  **3652/3652 全部通过（100.00%）**，0 失败、0 崩溃、0 超时。
- 运行方式：make tests -j12 编译全部测试程序 → 自写并行 runner
  （12 路，TMPDIR=$HOME/tmp，LD_LIBRARY_PATH 指向构建树）逐个模块
  运行并解析每个用例的 (PASS)/(FAIL) 行。结果清单：
  设备 $HOME/tmp/flint-test-results.txt。
- **发现并修复 8 个模块的 OHOS 特有崩溃**（统一根因：/tmp 只读）：
  1. fmpz_factor / qsieve / fq / fq_nmod / gr_mat：大数分解走 qsieve，
     其 relations 临时文件硬编码 `/tmp/siqsXXXXXX` → mkstemp 失败 →
     flint_throw → abort。**补丁 0004**：尊重 TMPDIR（缓冲从 20 字节
     扩到 1024，QSIEVE_FNAME_SIZE 常量）。
  2. arf / arb / mag：dump_file 测试用 tmpfile()——OHOS 的 tmpfile()
     **无视 TMPDIR 且 /tmp 只读，恒返回 NULL**（探针实测 errno=13）→
     NULL FILE* 崩溃。**补丁 0005**：test_helpers.h 增加
     FLINT_TEST_TMPFILE 宏（mkstemp($TMPDIR/flint-test-XXXXXX) +
     立即 unlink + fdopen，语义等价 tmpfile），三个 t-dump_file.c
     改用该宏；另显式声明 mkstemp/fdopen 原型（musl 在严格
     -std=c11 下隐藏 POSIX 声明）。
- 诊断过程：gdb ptrace 被 OHOS 沙箱禁止、LD_PRELOAD 被禁用；
  --wrap=abort 拦不到动态库内 abort；最终通过测试内插桩标记 +
  逐用例二分定位。崩溃确定性、可复现（设备实测）。

## 已知特性（与 3.2.2 相同，消费方需知情）
gmp/mpfr 在制品仓是**静态**包，被整体链进 `libflint.so`：
- 好处：`DT_NEEDED` 只剩 `libc.so`，部署自包含；
- 代价：libflint.so 重导出大量 `__gmp*` 与 `mpfr_*` 符号。下游若同时
  动态链接另一份 libgmp，运行期会有两份 GMP 代码共存（符号插入使先加载者
  胜出）。默认分配器一致时通常无害，调用过 `mp_set_memory_functions` 的
  场景需留意。

## 设备构建（OHOS 专属路径）
- profile 的 CONFIG_SHELL bash 在 HMDFS 上有 getcwd 缺陷（configure 报
  "working directory cannot be determined"，挫折 1/3 实撞）。build() 在
  os=OHOS 时用 /bin/sh 原位驱动 configure/make/install，绕过 Conan
  Autotools helper 的 shell wrapper；TMPDIR 指向 $HOME/tmp（/tmp 只读）。
  非 OHOS（Linux）仍走标准 Autotools helper（WSL x86_64 验证通过）。
- 编译器解析链：tools.build:compiler_executables conf → VirtualBuildEnv
  CC → 报错（R33，无硬编码）。
- **官方 CI 首跑失败教训（PR #5402 build #25792）**：CI worker 的 PATH
  不含工具链目录，clang（绝对路径）内部调用的 ld.lld/nm 等走 PATH →
  configure 报 "C compiler cannot create executables"。修复：从 CC 的
  dirname 推导工具链目录并 prepend 到 /bin/sh 脚本的 PATH（不硬编码）。
  验证方式：`env -i` + CI worker 相同 PATH/TMPDIR 模拟复现失败 → 修复后
  模拟环境 20/20 通过（configure "C compiler works... yes"、m4 找到）。

## CI 门禁结果（ci/conan/build_and_test.sh，2026-08-15）
- G0/KC/JC pass；L0 pass（含 L0i 依赖在制品仓、L0j 版本未发布）；
  L1 pass（L1a test_package 执行、L1b 执行痕迹、L1e 破坏性负向测试）；
  L2 skip（库包无 bin/）；L5 pass（lib/ 有内容）
- L4 warn：补丁扫描命中 `patches/0001-config.guess-ohos.patch` 与
  `patches/0004-qsieve-tmpdir.patch` ——
  **均为误报**：L4 用 `(strcpy|sprintf|gets|strcat)\b` 扫描补丁，
  ① 0001 上下文行中的英文单词 `targets`（"tar-gets" 尾匹配 `gets\b`，
  挫折 28）；② 0004 的 `snprintf`（**有界安全函数**）被 `sprintf\b`
  子串误命中（无前置边界）。两补丁均无任何危险函数。
- 门禁通过率 100%（1/1）

## 状态
built —— 真机 `conan create -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` rc=0（2026-08-15），
test_package 20 条断言全部通过；官方 CI 门禁 build_and_test.sh 通过率 100%。
