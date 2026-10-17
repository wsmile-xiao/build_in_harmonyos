# fathom 1.0 适配笔记

## 编译环境
- 构建系统: cmake（配方注入最小 CMakeLists；上游无库级构建系统）
- 编译日期: 2026-09-27
- 编译器: clang（OHOS SDK 15.0.4 / 真机 /data/service/hnp/bin/clang，`--target=aarch64-linux-ohos` + musl sysroot）
- 状态: built（真机 shadow CI 全绿：L0/L1/L2/L4/L5 通过，conan create 成功）

## 上游信息（W0/W1）

- 上游仓库: https://github.com/basil00/Fathom
- 版本: tag v1.0（commit 70d0091f567b465dc2045c1db4961fabbe8ddda6）
- 许可证: MIT（basil 修改部分）；tbcore.c 源自 Ronald de Man（无限制许可）
- 源码归档: 官方 tag archive tar.gz，SHA256
  `51d1f16af1b8b45c6fd5dfb8392a9dfb0282fa02df57d241ffac9896f0006d94`
- 包结构: LICENSE、README.md、src/{tbprobe.c/h, tbcore.c/h, tbconfig.h,
  apps/{fathom.c, Makefile}}
- W0 依赖结论:
  - 依赖数量: 0（纯 C99 + libc；tbcore.c 用 POSIX unistd/sys/stat/fcntl/sys/mman，
    musl 全部支持；CLI 的 getopt.h 不进本包）
  - 已满足依赖: N/A；缺失依赖: 无；是否需要拆分依赖适配: 否；阻塞点: 无

## 编译步骤

1. `conan source` 等价流程：下载 tag 归档（conandata.yml 双镜像：gh-proxy +
   官方），解压后 strip_root 得 `Fathom-1.0/`。
2. `source()` 内 `replace_in_file` 应用两处可移植性修改（见下节）。
3. CMake 构建：`add_library(fathom STATIC src/tbprobe.c)`，
   C99 + GNU extensions，宏 `TB_NO_THREADS TB_NO_HW_POP_COUNT`
   （与上游 src/apps/Makefile 的 `-std=gnu99 -D TB_NO_THREADS
   -D TB_NO_HW_POP_COUNT` 一致），fPIC 打开。
4. 安装：`lib/libfathom.a`、`include/{tbprobe.h, tbconfig.h}`、licenses/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 上 `#include <x86intrin.h>` 编译失败 | clang 该头文件在非 x86 目标直接 `#error "This header is only for x86"`；唯一用途 `_mm_popcnt_u64` 已被 `TB_NO_HW_POP_COUNT` 守卫 | include 外加 `#if defined(__i386__) \|\| defined(__x86_64__)` 守卫 |
| 2 | `lsb()` 的 `bsfq` 内联汇编在 aarch64 无法汇编 | x86 专属指令，且该处无任何条件编译守卫 | x86 分支保留 `bsfq`；`#else` 分支用 `__builtin_ctzll`（对非零输入语义相同；调用方均以 `for (; b; b = poplsb(b))` 保证非零） |

两处修改均在 `conanfile.py source()` 内完成（R8：保持上游风格、追加平台
分支、x86 行为零变化；无 OHOS 专属宏，所有非 x86 目标共享回退分支）。

## 源码修改

无 .patch 文件；修改清单（配方内完成）：

- `src/tbprobe.c`：`#include <x86intrin.h>` 加 x86 目标守卫
- `src/tbprobe.c`：`lsb()` 内联汇编加 x86 守卫 + 非 x86 走 `__builtin_ctzll`

## 上游测试盘点（R51）

v1.0 tag 归档仅含 LICENSE、README.md、src/（5 个库文件 + CLI），
无 test/ tests/ 目录，Makefile 仅有 main 目标，无 ctest / make check。
**上游测试 0/0 (N/A)**。消费者测试由 test_package 补位：5 组 21 个 CHECK
断言（tb_init 契约、probe 参数守卫、无表文件探测语义、helper API 位运算、
攻击表一致性），其中 helper API（tb_lsb/tb_pop_count/tb_pop_lsb）恰好执行
被补丁的 lsb()/popcount() 路径，无需 Syzygy 表文件即可实质验证核心修复。
无表探测语义实测确认：KvK 走上游特判（probe_wdl_table 中 key==KEY_KvK
直接判和，root 探测还能给出和棋走法），KQvK 等缺失材料签名则优雅返回
TB_RESULT_FAILED。

## 验证结果

本机前置验证（2026-09-27，未用 conan，直接等价命令）：

```bash
# 1) OHOS aarch64 交叉编译补丁后的库本体（Wall 零警告）
clang --target=aarch64-linux-ohos --sysroot=<OHOS SDK>/sysroot \
  -std=gnu99 -O2 -Wall -D TB_NO_THREADS -D TB_NO_HW_POP_COUNT \
  -Isrc -c src/tbprobe.c -o out/tbprobe.o          # OK, 62KB

# 2) 打包静态库并链接消费者测试（compile+link 验证）
llvm-ar rcs out/libfathom.a out/tbprobe.o
clang --target=aarch64-linux-ohos ... test_fathom.c out/libfathom.a \
  -o out/test_fathom                                # OK
llvm-readelf -h → ELF64 / AArch64（lib 与测试二进制均正确）
llvm-nm → tb_init / tb_probe_wdl_impl / tb_lsb / tb_pop_count 全部解析

# 3) 消费者测试实跑（本地无 WSL 发行版/qemu 可用环境，实测在
#    x86_64 Linux 容器 gcc 11.4 下编译运行；helper API 位运算与 KvK
#    特判走的正是补丁覆盖的代码路径）
21/21 CHECK 断言通过，退出码 0
（含 KvK 无表判和、KQvK 无表优雅失败、tb_lsb/tb_pop_count 回退分支）
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libfathom.a | 静态库（AArch64） |
| include/tbprobe.h | 公共 API 头 |
| include/tbconfig.h | 配置头（tbprobe.h 依赖） |
| licenses/LICENSE | MIT |

## 注意事项

- 本包只打包库本体；上游 CLI（src/apps/fathom.c，需 getopt）未打包，
  L2（bin smoke）预期 skip，属纯库正常现象。后续如需 CLI 可增补版本。
- Syzygy 表文件（.rtbw/.rtbz）是运行时数据，不属本包；test_package 与
  探测函数在无表环境均按 TB_RESULT_FAILED 优雅失败。
- 静态库设计：aarch64 无 .so 产物，规避签名与系统库污染问题（R26 精神）。
- 真机/shadow CI 未执行（本轮只做本机前置工作），下一步命令见下。

## 下一步（真机 / shadow CI）

1. 确认真机 SSH 可达且空闲（单包排队）。
2. 创建隔离 job：

```sh
job="fathom-1.0-<timestamp>"
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job "$job" \
  --package archives/f/fathom/1.0 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"
```

3. 传输包目录（scp 或 base64，勿用文本管道 tar），设备端核对文件清单。
4. 执行 runner，记录 exit code 与 L0/L1/L2/L4/L5 结果：

```sh
sh "$HOME/ohos-users/codex/$job/run-conan-heavy.sh"
```

5. 预期：上游测试 0/0 (N/A)；test_package 21/21 断言；L2 skip (no bin/)。

## 真机 shadow CI 实测结果（2026-09-27）

隔离 job `fathom-1.0-20260927`（--repo-source 方式，设备无 git）。

| 项 | r1（16:10） | r2（16:16） |
|---|---|---|
| exit code | 1 | **0** |
| G0 / KC / JC | pass / fail(bash) / pass | **全 pass** |
| L0 | pass（结构类全过） | **pass: all checks passed** |
| L1 | skip: blocked_by_KC | **pass: test_package executed**（含 L1e 通过） |
| L2 | skip: blocked_by_KC | **skip: no bin/ dir**（纯库正常） |
| L4 / L5 | skip: blocked_by_KC | **pass / pass: lib/ has content** |
| 排队等待 | 0s | 0s（锁空闲，未排队） |
| test_package | 未执行 | **21/21 断言真机实跑通过** |
| 上游测试 | 0/0 (N/A) | 0/0 (N/A) |

- r1 失败根因（环境，非配方）：runner 环境 PATH 缺少 `/data/service/hnp/bin`，
  KC 步骤调用 bash 失败（该目录下 bash/git/clang 为实际可用入口）。修复：在
  本 job 的 env.sh 末尾追加 `export PATH=/data/service/hnp/bin:$PATH`（job
  局部修改，未动公共设施）。r2 全绿。
- CI L1e 破坏性反向验证确认：`Negative test confirmed — test genuinely
  depends on fathom`。
- CI Build Summary：Success 1 / Failed 0，pass rate 100%。
- 真机 conan create 源码走 gh-proxy 镜像下载成功，SHA256 校验通过。
