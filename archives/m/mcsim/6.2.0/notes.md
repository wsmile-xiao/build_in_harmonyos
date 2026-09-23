# mcsim 6.2.0 适配笔记

## 编译环境
- **构建系统**: autotools (configure + make)
- **编译日期**: 2026-09-16
- **编译器**: clang（OHOS 工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过——conan create 全绿）
- **补丁数量**: 0（配方内联处理——无独立补丁文件）
- **依赖**: gsl/2.8（configure AC_CHECK_LIB 探测；lapack/sundials/sbml 为可选功能，制品仓未提供）

## 编译步骤（conan create 全流程）

```bash
conan create archives/m/mcsim/6.2.0 --build=missing
```

### 1. 源码获取（source()）
```bash
tar -xzf mcsim-6.2.0.tar.gz --no-same-owner || true
cp -a mcsim-6.2.0/. . && rm -rf mcsim-6.2.0
```

### 2. 配置（configure）——含两处平台适配
```bash
ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes \
CFLAGS='-I<gsl>/include -Wno-error -Wno-implicit-function-declaration -fsigned-char' \
LDFLAGS='-L<gsl>/lib' \
./configure --build=aarch64-unknown-linux-ohos --prefix=/usr --disable-shared
```

- **musl malloc/realloc 检测覆盖**：musl 的 `malloc(0)/realloc(0)` 语义触发 autoconf/gnulib
  老式检测判负（`ac_cv_func_*_0_nonnull=no`）→ `config.h` 把 `malloc/realloc` 宏定义
  为 `rpl_*`，而 `mod_LDADD` 未包含 `LIBOBJS` 导致链接 `undefined symbol: rpl_realloc`。
  musl 行为完全符合 C99 允许范围，用缓存变量覆盖检测、直接用系统实现。
- **`-fsigned-char`（知识库 E419 复用）**：mcsim 的 `CountChars` 用
  `char c; while ((c = getc(f)) != EOF)`——aarch64 上 plain char 默认 unsigned，
  EOF(-1) 被截断为 255 永不相等 → **mod 处理任何模型文件都死循环**（实测
  `timeout 20 mod perc.model` 返回 rc=124 挂起，AnnounceProgram 之后无任何输出）。
  按知识库 E419（plain char signedness implementation-defined，
  rec_approach=consistent-target-signed-char-mode）经 toolchain 统一 plain char
  语义，**不改上游源码**。
- 其余：config.status 的 mktemp 相对路径改 `${TMPDIR}/`（沙箱限制）；
  config.sub 补 `linux-ohos` 模式。

### 3. 编译（make -j2）

### 4. 上游测试（build() 集成——R51 实测回填）
上游测试入口：`TESTS = examples/perc/Makefile`（回归脚本，内部含 TEST1-5 五组检查）。

实测结果：
```
Testing mod on perc.model
-PASSED-
-SKIPPED- TEST2-5: require libsbml/sundials/lapack/mpi + gcc (unavailable)
# PASS:  1
# FAIL:  0
```

### 5. 打包（package()）
```bash
make install DESTDIR=<package_folder>
```
安装布局：`usr/bin/{mod,makemcsim,...}`、`usr/lib/libmcsim.a`、`usr/include/`；
`package_type = "application"`，`package_info` 声明 bindirs/libdirs/includedirs
（`configure --prefix=/usr` + DESTDIR → `usr/*`）；软件级 `commands.json` 声明 CLI。

## 上游测试用例修改说明（R51 逐项）

### 是否存在对上游测试用例的修改？

**是**——对 `examples/perc/Makefile`（上游回归脚本本体）做了以下修改，逐项如下：

1. **修改的测试文件**：`examples/perc/Makefile`（脚本第 1 行 shebang）
   - **修改原因**：`#!/bin/bash` 在本平台不存在（设备无 `/bin/bash`；测试驱动报
     `bad interpreter: No such file or directory`，exit 126）
   - **修改内容**：`#!/bin/bash` → `#!/bin/sh`（POSIX sh），并把脚本内 bash 专用
     重定向 `&> file` 改为兼容写法 `> file 2>&1`
   - **修改后结果**：测试脚本可被 test-driver 执行，TEST1 正常跑出 `-PASSED-`

2. **修改的测试文件**：`examples/perc/Makefile`（TEST2-5 段落）
   - **修改原因**：TEST2-5 需要 `libsbml`、`sundials_cvodes/nvecserial`、`lapack`、
     `mpi` 与 `gcc` 编译 mcsim.perc——这些库在制品仓未提供、超出本包依赖链
     （configure 的 `AC_CHECK_LIB` 对它们均为可选探测），无法在本平台执行
   - **修改内容**：在 TEST1（mod 编译 perc.model 并与 ref_model.c 做 diff，
     本包可直接验证的部分）结束处插入显式跳过标记与退出逻辑：
     ```sh
     echo '-SKIPPED- TEST2-5: require libsbml/sundials/lapack/mpi + gcc (unavailable)'
     if test $TEST -eq 1; then exit 1; else exit 0; fi
     ```
     TEST2-5 的断言逻辑与输入数据**原样保留**，未删除任何检查
   - **修改后结果**：TEST1 真实执行并通过；TEST2-5 在日志中显式标记为 skipped
     及技术原因；`make check` 汇总 `# PASS: 1 / # FAIL: 0`

3. **其他**：为防 mod 在无 stdin 环境等待输入，`../../mod/mod perc.model` 调用加
   `</dev/null` 与 `timeout 60` 保护（不改变测试语义）。

## 验证结果
- **构建**: `mcsim/6.2.0: Package created`（conan create 全绿）
- **上游测试**: 实测 **1/1 通过**（TEST1：mod 编译 perc.model 后与 ref_model.c
  逐行 diff 一致；TEST2-5 因依赖缺失显式跳过并附技术原因）
- **R34 消费者验证**: test_package — 运行被测二进制并断言行为：
  - `mod -h` → 输出 `Usage: mod` 且退出码 0
  - `mod <不存在的文件>` → 非零退出码且不挂起（输入错误处理）

## 已知限制
- lapack / sundials / libsbml / MPI 支持未启用（制品仓无对应依赖包；configure
  对它们均为可选探测，核心 mod/sim 功能不依赖）。
- 上游 perc 回归的数值测试段（TEST2-5）在本平台不可执行（见上逐项说明）。
- `-fsigned-char` 会统一改变 plain char 语义（与上游在 x86 上的默认一致；
  mcsim 的文本/数值处理路径不依赖无符号 char 行为）。
---

**编译结束**: 2026-09-16 01:57
**最终状态**: built
