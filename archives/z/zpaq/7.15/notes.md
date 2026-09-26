# zpaq 7.15 适配笔记

## 编译环境

- 构建系统: makefile（上游顶层 `Makefile`，`make zpaq` 目标）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang++`，aarch64-unknown-linux-ohos）
- 目标: `os=OHOS os.version=6.0 arch=armv8 compiler=clang`（`ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 上游形态

zpaq 7.15（2016-08-17，Matt Mahoney）是 ZPAQ 开放压缩标准的参考实现：
日志式（journaling）归档器，支持 AES-256 加密、5 级压缩、
内容感知的文件片段级去重、以及可回滚的历史版本。发布物只有 8 个文件：

| 文件 | 说明 |
|------|------|
| `zpaq.cpp` | CLI（archiver 前端，123 KB） |
| `libzpaq.cpp` / `libzpaq.h` | 可复用库（压缩引擎 + ZPAQL 虚拟机，265 KB / 60 KB） |
| `Makefile` | 上游构建系统（`all` / `install` / `check` / `clean`） |
| `zpaq.pod` | man page 源（pod2man 格式） |
| `COPYING` | Unlicense（公有领域） |
| `readme.txt` | 构建与用法说明 |
| `.gitignore` | —— |

**零外部依赖**：AES-256 / SHA-1 / SHA-256 / scrypt 均在 `libzpaq.cpp` 内自实现
（源自 libtomcrypt，非 OpenSSL），divsufsort 内嵌于同一文件（Yuta Mori，MIT），
系统侧只需要 pthread。因此本配方 `requirements()` 为空。

## 编译步骤

上游 readme 给出的构建命令是：

```
g++ -O3 -march=native -Dunix zpaq.cpp libzpaq.cpp -pthread -o zpaq
```

本配方直接复现这条命令并做四处平台化取值（上游 `Makefile` 只是把它包成
`zpaq.o` + `libzpaq.o` → `zpaq` 的规则，两条翻译单元一次编译链接等价）：

```bash
<tools.build:compiler_executables.cpp> \
  -O3 -DNDEBUG -Dunix -DNOJIT -static-libstdc++ \
  zpaq.cpp libzpaq.cpp -pthread -o zpaq \
  > <build_folder>/zpaq-build.log 2>&1      # 见下表 #4：stdio 必须落到文件
```

逐项理由：

| 参数 | 理由 |
|------|------|
| `-DNOJIT` | **必需**：`libzpaq.cpp` 的 `ZPAQL::assemble()`（3035–4585 行）在运行期生成 x86-32/x86-64 机器码并跳转执行。aarch64 上不加此宏虽能编译、也能压缩，但一旦走到 JIT 路径即 `Illegal instruction (core dumped)`（本机实测，见下表 #1） |
| `-Dunix` | 选择 POSIX 代码路径（上游默认目标是 Windows） |
| `-O3 -DNDEBUG` | 沿用上游优化级别与发布语义；`-DNDEBUG` 关闭上游 `assert` 调试块 |
| 去掉 `-march=native` | 交叉/非本机原生目标下 clang 直接拒绝该选项，且包需要在 aarch64 目标矩阵上可移植 |
| `-static-libstdc++` | OHOS SDK sysroot 的 `libc++_shared.so` 是链接器脚本（`INPUT(-lc++_shared)`），musl 加载器无法解析；静态烘焙 libc++ 后产物 `DT_NEEDED` 仅剩 `libc.so` |
| `> zpaq-build.log 2>&1` | **必需**（本机实测）：CI harness 用 `/system/bin/sh` 做 recipe shell 时，编译器 stdio 若直连 harness 的捕获管道会**静默退出 1（无任何诊断输出）**；同一条命令把 stdio 落到普通文件即成功。日志随后 `cat` 出来，诊断信息仍留在 conan/CI 日志里 |

上游 `Makefile` 的 `all` 目标还会生成 man page（`zpaq.1`，依赖 `pod2man`）。
本配方不构建它：man page 是可选文档而非包产物，且不引入额外工具链依赖。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 不传 `-DNOJIT` 时压缩正常，解压瞬间 `Illegal instruction (core dumped)`（`zpaq add` 成功、`zpaq extract` 崩溃） | `libzpaq.cpp:3035-4585` 的 `ZPAQL::assemble()` 生成 x86-32/x86-64 机器码，`Predictor::predict()` 会跳进去执行（`libzpaq.cpp:3237/3837` 只在 CPU 特性探测失败时才 `error("JIT supported only for x86-32 and x86-64")`，aarch64 上探测通过，于是执行了 x86 指令） | 构建时加 `-DNOJIT`，走可移植解释器 `predict0()`（上游 readme 明确要求非 x86 目标这么做） |
| 2 | 动态链接的 `zpaq` 起不来（`Error loading shared library libc++_shared.so`） | 同 libzpaq 0.01 的历史踩坑：SDK 的 `libc++_shared.so` 是链接器脚本，musl 加载器不认 | `-static-libstdc++` 静态烘焙 libc++，产物只依赖 `libc.so` |
| 3 | `-march=native` 在本机 clang 上不可用 | 编译目标是 `aarch64-unknown-linux-ohos`，与探测到的宿主 CPU 不匹配；且会破坏包的可移植性 | 去掉 `-march=native`，保留 `-O3 -DNDEBUG` |
| 4 | recipe shell 为 `/system/bin/sh` 时，编译命令**静默失败**（`ConanException: Error 1`，编译器零输出；`make` 版本表现为 `make: *** [Makefile:15: zpaq.o] Error 1`） | 该 shell 下「编译器 stdio 直连 harness 捕获管道」这一组合会让编译器进程以 1 退出且不打印任何诊断（受控实验：同一命令、同一 env，stdio 落到普通文件即 `rc=0`；同为 ELF、同样由该 shell 拉起的 `cat`/`make` 写管道正常） | 编译输出重定向到 `zpaq-build.log` 再 `cat` 回显；同时改用单次直接编译调用（去掉 `make` 层），使构建不依赖 recipe shell 的具体实现 |
| 5 | `make check` 最后一步报 `rm: No such file or directory`（错误码 127） | 本机 `rm` 被沙箱安全 shim 接管，shim 的 `#!/bin/bash` 解释器不存在（环境问题，与 zpaq 无关） | 不修上游：`make check` 的 add / extract / cmp 三步已全部成功，仅收尾清理受影响；包内 `test_package` 用 `rm -rf ... \|\| true` 做 best-effort 清理，CI 上正常 |
| 6 | `conandata.yml` 注释里写入上游仓库地址/官网地址后，W3/CI 的 `source()` 报 `NotADirectoryError`（路径形如 `<predl>/<hash>_zpaq/archive/refs/tags/7.15.tar.gz`） | CI 的 mirror-fallback 与 Pre-download 两步按「conandata.yml 内出现的**全部** URL 字面量」做 `str.replace`：注释里的裸仓库地址是 tarball 地址的前缀，替换后把 `sources.url` 改写成畸形 `file://` 路径 | 本文件（含注释）只保留 `sources.url` 一处 URL 字面量；官网/仓库地址改写为不含 scheme 的文字描述 |

## 源码修改

无补丁。上游源码为 2016 年发布的原样 C++（纯 ISO C++ + POSIX pthread），
零修改即可在 aarch64 OHOS 上编译运行；`conandata.yml` 的 `patches:` 为空，
`apply_conandata_patches()` 是空操作。

## 依赖版本

零依赖（`requirements()` 为空）。系统侧仅 pthread —— 链接命令里由上游 Makefile
的 `-pthread` 提供，OHOS musl 的 pthread 在 libc 内，无需额外 Conan 包。

## 验证结果

### 1) 上游测试（R51 第 2 步：实际运行）

清点结论：上游只有一个测试入口——顶层 `Makefile` 的 `check` 目标
（`Makefile:32-36`），注册用例 1 项（一次 `add` → `extract` → `cmp` 往返）。
`make -n check` 逐字输出 4 行：

```
./zpaq add archive.zpaq zpaq
./zpaq extract archive.zpaq zpaq -to zpaq.new
cmp zpaq zpaq.new
rm archive.zpaq zpaq.new
```

适配机实测（`make check CXX=clang++ CPPFLAGS="-Dunix -DNOJIT" CXXFLAGS="-O3 -DNDEBUG" LDFLAGS="-static-libstdc++"`）：

```
zpaq v7.15 journaling archiver, compiled Sep 25 2026
100.00% 0:00:00 [1..37] 2214620 -method 14,103,0
1 +added, 0 -removed.
0.000000 + (2.214464 -> 2.214464 -> 0.930681) = 0.930681 MB
0.170 seconds (all OK)
[extract] [1..37] -> 2214620  0.303 seconds (all OK)
cmp zpaq zpaq.new              # 无输出 = 字节一致
```

结论：**上游 1/1 通过**（仅收尾 `rm` 因沙箱 shim 报 127，见上表 #4）。

### 2) 交付包消费者实测（test_package，7 项断言）

对 `conan create` 安装出来的 `bin/zpaq` 真实执行 add / extract / list / 回滚 / 错误路径，
断言归档往返字节一致、日志版本递增、`-until 1` 回滚正确、去重记账存在、
缺失归档有可诊断错误。逐项台账见 `reports/test-report.md`。

### 3) 产物属性（application 判据）

```
$ llvm-readelf -dW bin/zpaq | grep NEEDED
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]
$ file bin/zpaq
ELF 64-bit LSB shared object, ARM aarch64, dynamic (/lib/ld-musl-aarch64.so.1)
```

单依赖 `libc.so`（libc++ 已静态烘焙），无系统同名库冲突（不是库包）。

### 4) conan-verify 八门禁与人工补测

`conan-verify` 结果（逐字见 `reports/conan-verify-report.md`）：

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | PASS | 构建系统识别（工具报 unknown，因本包零依赖无需预查询） |
| G1 | PASS | 配方结构 12 项全绿 |
| G2 | PASS | `conan create` 成功（日志 `reports/conan-create.log`） |
| G3 | PASS | 无 `lib/`（纯可执行包），无系统同名库冲突 |
| G4 | **SKIPPED** | 工具报 `⚠️ 无法找到程序包 ID`（application 包无 `lib/`，同 bti 034 现象） |
| L2 / L4 / L5 | **SKIPPED** | 工具因 `无 cache 路径` 跳过 |

工具对 G4/L2/L4/L5 同时打印 `✅ PASS` 与 `⏭️ 跳过`。本包**按「并存时以跳过为准」**
的口径记为 **未执行**，不计入通过；这四项由 `reports/conan-verify-supplement.md`
中的人工补测覆盖（G4 产物清单、L2 消费者实测、L4 ELF 安全属性、L5 两轮独立构建复现基线）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/zpaq` | 命令行归档器（ZPAQ 7.15） |
| `licenses/COPYING` | 上游许可证正文（Unlicense，公有领域；`libzpaq.cpp` 内嵌的 divsufsort 片段为 MIT） |

## 注意事项

- **`-DNOJIT` 不能省**：省略后编译/压缩看起来都正常，只在解压（真正执行 ZPAQL）时崩溃，
  属于"能编过但不可用"的隐性失败，回归时务必保留。
- zpaq 7.15 **没有 `--version` / `--help` 选项**：任何未识别参数（含 `--version`）都会
  打印横幅 + 用法并以退出码 1 结束；因此 `conan-verify` 的 L2 冒烟（`bin --version`
  → 退出码 0）对本包不适用，本包的可用性由 `test_package` 的真实往返断言证明。
- **退出码语义实测**（对交付的 aarch64 二进制逐条测得，写用例时务必按此断言）：

  | 调用 | 退出码 | 说明 |
  |------|--------|------|
  | 无参数 / 未知选项（含 `--version`） | 1 | 打印横幅 + 用法 |
  | `x <不存在的归档>` | **2** | 诊断 `…: No such file or directory` 走 stderr |
  | `add <归档> <不存在的输入路径>` | **0** | 只打印诊断，**不返回非 0** |
  | 成功的 add / extract / list | 0 | —— |

  即"错误命令一律返回 0"**不成立**：缺失归档返回 2，而缺失输入路径返回 0。
  正因如此，`test_package/test.sh` 的正向用例断言产物字节（`cmp`）而非 `$?`，
  错误用例（T6）则同时断言诊断文本与退出码。
- `zpaq extract -to <dir>` **会自动创建**缺失的输出目录（本机实测 `-to out1`
  在 `out1` 不存在时成功并生成 `out1/src/...`），这正是上游 `make check`
  （`extract … -to zpaq.new`）所依赖的行为；`test_package` T2 依赖同一行为。
- **本包不含 `packaging/` 与 `.staging-verified`**（框架预检会报这两项 ❌，属已知误报）：
  v3.0（`knowledge/ARCHIVE-SPEC.md`，2026-06-22 生效）已将二者列为**废弃**产物
  （「Conan 体系替代手动 tar.gz 打包」），R19 也禁止手动打包 tar.gz。
  实测全仓 `git ls-files` 下 `packaging/*.tar.gz` 为 **0** 个、最近合并提交 **0** 个带
  `packaging/`；`.staging-verified` 全仓仅 1 个（`archives/c/cloog/0.21.1/`）且不在
  `ci/scripts/junk_check.sh` 的 `JC5_ALLOWED` 白名单内，创建它会被 JC 拦。
  处置依据：`knowledge/drafts/DRAFT-makedepend-1.0.10-finish-prereq-deprecated-markers.md`
  与 `DRAFT-semver-0.3.0-index-only-baseline-finish-recovery.md`。即：`finish` Step 10 与
  `submit` 自检的 `packaging_present` 是 v2.0 遗留检查，本包按 v3.0 规范不创建这两项。

- 与同上游的 `libzpaq/0.01`（2009 年的 level 0 单文件实验版）是**不同版本、不同结构**，
  两者各自独立归档；7.15 是本仓库中 zpaq 生态的正式发布版参考实现。
---

**编译结束**: 2026-09-25 16:51
**最终状态**: built
