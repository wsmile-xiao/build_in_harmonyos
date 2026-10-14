# gaffitter 1.0.0 适配笔记（OHOS aarch64）

## 1. 基本信息

| 项 | 值 |
|---|---|
| 上游项目 | https://sourceforge.net/projects/gaffitter/ |
| 主页 | https://gaffitter.sourceforge.net/ |
| 作者 | Douglas A. Augusto（2005-2015） |
| 许可证 | GPL-3.0-or-later（README 声明 GPLv3 or later，源码头均带 GPLv3 头，COPYING 为 GPLv3 全文 674 行） |
| 语言/规模 | C++（约 5,100 行源码） |
| 构建系统 | CMake（`cmake_minimum_required(VERSION 2.4)`；src/util、src/optimizers 两个内部静态库 + bin/fit 可执行；无第三方依赖） |
| 产物 | `bin/fit` —— CLI 工具（上游历史命名，可执行名与包名不同） |
| 源码 tarball | https://downloads.sourceforge.net/project/gaffitter/gaffitter/1.0.0/gaffitter-1.0.0.tar.gz |
| SHA256 | `c85d33bdc6c0875a7144b540a7cce3e78e7c23d2ead0489327625549c3ab23ee`（50,827 字节，双下载端点校验一致） |

## 2. 上游测试枚举台账（双口径）

口径 A（源码树文件枚举，tarball 解压后全量 24 文件）：

```
AUTHORS  COPYING(674 行)  CMakeLists.txt  INSTALL  README
src/{DiskUsage,Input,Optimizer,Params,gaffitter}.cc
src/{BBHash,DiskUsage,Input,Optimizer,Params}.h
src/optimizers/{BestFit,GeneticAlgorithm,Split}.cc + {BestFit,GeneticAlgorithm,Split}.h
src/util/{CmdLineParser,Exception}.cc + {CmdLineParser,Exception}.h
src/util/{Color,Random,StreamManager}.h
```

- 无 tests/ 目录，无 test_*.cc / *_test.cc，无测试脚本与测试数据文件
- src/optimizers/ 与 src/util/ 为算法/工具库，非测试代码

口径 B（构建系统集成检查）：

- `grep -rni "enable_testing\|add_test\|CTest" .` → **0 命中**
- 根/src/src\*/4 个 CMakeLists.txt 均无 CTest 目标
- 上游无 CI 配置（无 .travis.yml/.github/workflows 等）

结论：**上游 1.0.0 官方测试 = 0**。test_package 以 CLI 真实行为测试补位（40 断言），test_ohos 补平台专项（17 断言）。

## 3. 适配要点与修复记录（0 patch）

上游代码为纯 POSIX（`sys/stat.h`/`dirent.h`/`unistd.h`/`rand`-`srand`），musl 完整覆盖，
无 `__OHOS__`/OS 名称分支。两处问题均以构建配置解决，无源码 patch：

### 3.1 CMake ≥ 4.0 拒绝 `cmake_minimum_required(VERSION 2.4)`

- 症状：`conan create` configure 阶段报
  `Compatibility with CMake < 3.5 has been removed from CMake`（本机 cmake 4.1.2）
- 修复：`CMakeToolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`
  （E187 推荐方案 / E103 回退方案，即 CMake 官方文档为"不可改 CMakeLists 的旧项目"
  提供的机制，等效把策略最低版本提到 3.5）
- 踩坑记录：先用 `tc.variables[...]` 不生效——它写进工具链文件的是
  `set(... CACHE ...)`，而 CMakeLists.txt:1 的 `cmake_minimum_required()` 求值时
  工具链文件尚未加载；必须 `cache_variables` 走 `-D` 命令行注入才会先于任何
  CMakeLists 处理生效。

### 3.2 libc++ C++17 模式移除 `std::random_shuffle`

- 症状：profile `cppstd=17` 下编译
  `src/optimizers/GeneticAlgorithm.cc:190: error: no member named 'random_shuffle' in namespace 'std'`
- 原因：`std::random_shuffle` C++14 起弃用、C++17 起从标准移除；OHOS 工具链的
  libc++ 严格移除该符号（libstdc++ 在 C++17 下通常仍保留）
- 修复：配方 `configure()` 钉 `self.settings.compiler.cppstd = "14"`——应用为终端
  产物，无下游 ABI 消费方，钉死标准不影响兼容性

## 4. 测试执行台账

### 4.1 upstream tests：0/0（上游无测试，见第 2 节）

### 4.2 test_package（cli_test.sh，`conan create` 内真实执行）

**40/40 断言通过**，覆盖：

| 组 | 断言数 | 内容 |
|---|---|---|
| 基础 | 4 | `--version` 退出码 + 精确版本串；`-h` 退出码 + 用法行 |
| 错误路径 | 6 | `-t` 缺值 rc=1（CmdLine 异常）；缺 `--target` rc=2；空输入 rc=2（含错误信息匹配） |
| 管道直输+切分 | 7 | `printf \| fit - --di -t 100 --sp --ss`：rc、两卷摘要（90/100、70/100）、4 个条目行（名称+字节） |
| 超大条目 | 3 | 150>100 排除告警 + 剩余条目装箱 + rc=0 |
| 恰好装满 | 2 | `100/100, Diff: 0` 精确摘要 |
| --bins 截断 | 2 | `--bins 1` 仅输出一卷 |
| GA 语义 | 5 | rc、每卷 ≤ target（容量约束）、Σ卷=160（守恒）、卷数=⌈160/100⌉=2（理论最优）、固定种子两次运行一致（确定性） |
| --ga-theo | 3 | 两卷均 80/100（理论最优即停） |
| 真实文件 | 6 | `fit -t 100k --ss <files>`：stat 到 60/30/50KiB，两卷摘要精确、3 个文件名保留 |
| 管道文件名 | 2 | `ls \| fit - -t 100k --sp --ss`：find/ls 集成语义 |

### 4.3 test_ohos（run_ohos_test.py，对 conan 安装产物真实执行）

**17/17 断言通过**：

| 用例 | 断言数 | 内容 |
|---|---|---|
| case1 ELF 身份 | 3 | ELF64（Class）/ AArch64（Machine）/ PIE（Type DYN） |
| case2 musl 动态链接 | 3 | INTERP=`/lib/ld-musl-aarch64.so.1`；NEEDED libc.so；OHOS 专属 `.note.ohos.ident` 段 |
| case3 真机运行 | 4 | `--version` rc+精确版本串；`-h` rc+用法行 |
| case4 HMDFS stat | 3 | 真实定长文件（60/30/50KiB）stat 装箱：rc、两卷摘要精确 |
| case5 真机 GA 组合 | 4 | rc、容量约束、守恒、理论最优卷数 |

## 5. 知识候选台账

| # | 标题 | 症状 | 处置 |
|---|---|---|---|
| K1 | 旧 CMake 项目（最低版本 <3.5）在 CMake ≥ 4.0 下的兼容开关 | `cmake_minimum_required(2.4)` configure 直接报错 | 知识图谱已覆盖（E103 bump-cmake-minimum-version / E187 add-cmake-flag），本包复用 E187 推荐方案，无需新建 |
| K2 | cppstd=17 + libc++ 下 `std::random_shuffle` 编译失败 | 2010 年代 C++ 代码常用 API 被 libc++ 在 C++17 模式严格移除（libstdc++ 宽松），profile 强制 17 时老包普遍踩坑 | 知识图谱无覆盖（grep 0 命中）→ 候选：配方钉 cppstd=14（无 patch）或 std::shuffle 替换（patch）。Path A 不扩展知识库，记录待批量复用 |

## 6. Path A/B 判断

**gaffitter 1.0.0 → Path A 完成**：无 patch、无 `__OHOS__`/OS 分支、无能力裁剪，
两处问题（CMake 版本兼容、cppstd）均为构建配置级修复且已有/可标准解决。

K2（random_shuffle × cppstd=17 × libc++）为通用能力问题：不阻塞本包，
但预计同代 C++ 包会批量复现，建议后续以 Path B 扩展知识图谱（候选标题
"libc++-cpp17-removes-random-shuffle"）。
