# tinymembench 0.4 适配笔记

## 软件简介

tinymembench（Siarhei Siamashka，MIT）测量内存顺序访问峰值带宽与随机访问
延迟：C 版 memcpy/memset 变体、libc memcpy/memset、各架构手写汇编
（x86 SSE2 / ARM NEON+VFP / AArch64 LDP-STP / MIPS32），以及按 2^n 递增
缓冲区尺寸的随机读延迟扫描（hugepage/非 hugepage 对照）。

- 上游：https://github.com/ssvb/tinymembench（tag `v0.4`，2016；
  `version.h` 中 `VERSION "0.4"`）
- 语言：C + 经 C 预处理器的手写汇编（`.S`）
- 许可证：MIT（tarball 内含独立 `LICENSE` 文件）
- 产物：单个命令行可执行文件 `tinymembench`

## 构建系统分析（W1）

- **类型**：纯 C + 手写 GNU makefile，无 configure/autotools/cmake。
- **无 install 目标、无 check/test 目标**，源码树不含任何测试文件。
- makefile 关键点：
  - `ifdef WINDIR` 分支强制 `CC = gcc`（Windows 宿主陷阱；命令行 `CC=`
    覆盖优先，build() 同时从环境清除 `WINDIR`）
  - 编译规则 `${CC} -O2 ${CFLAGS} -c xxx.c` / `-c xxx.S`
  - 链接规则 `${CC} -O2 ${CFLAGS} -o tinymembench main.c util.o asm-opt.o
    x86-sse2.o arm-neon.o mips-32.o aarch64-asm.o -lm`（`-lm` 在末尾，
    链接顺序正确）
- **平台分发**：`asm-opt.c` 用 `#if defined(__i386__)/__amd64__/__arm__/
  __aarch64__/__mips__` 选择基准集；四个 `.S` 文件各自整体包在
  `#ifdef <arch>` 内（大写 `.S` 走 C 预处理器），任何目标架构都能编译
  全部四个 `.S`，非本平台的成为空目标文件 → aarch64-linux-ohos 上只有
  `aarch64-asm.S` 产出代码（NEON LDP/STP、LD1/ST1、STP/STNP fill 等）。
- **运行时特性**：
  - `__linux__` 分支 include `<linux/fb.h>` 做 framebuffer 读测试；
    `/dev/fb0` 打不开时自动跳过（OHOS PC 一般无 fb0 → 跳过）
  - 延迟测试优先 `posix_memalign` + `madvise(MADV_HUGEPAGE/MADV_NOHUGEPAGE)`
    （musl 提供 `MADV_HUGEPAGE`）；madvise 失败时该轮返回 0，main 降级到
    `use_hugepage=0` 的 malloc+对齐路径
  - `/proc/cpuinfo` 特性探测（NEON 等）在 `__linux__` 下启用，aarch64 的
    汇编基准集不依赖探测结果，直接启用

## 依赖（W0）

- 运行时/构建依赖：仅 C 标准库（musl）+ libm，无第三方 Conan 依赖。
- 无可选集成依赖。
- **W0 结论**：依赖数 0，全部满足，无需拆分依赖适配。

## 适配点

1. **CC/CFLAGS 覆盖**：`make CC=<ohos-clang> CFLAGS="" -j1`；编译器来自
   `tools.build:compiler_executables`（R33）。
2. **WINDIR 陷阱**：makefile `ifdef WINDIR` 会在 Windows 宿主上强制
   `CC = gcc`；命令行覆盖优先，且 build() 从子进程环境移除 `WINDIR`。
3. **补丁 0001（clang 汇编兼容）**：clang 集成汇编器不支持 GNU gas 的
   `.func`/`.endfunc` 指令（本机实测 OHOS SDK clang 15 报
   `<instantiation>:3:1: error: unknown directive .func`），删除这 46 行
   DWARF 注记指令（x86-sse2.S 11 行、arm-neon.S 24 行、aarch64-asm.S
   8 行、mips-32.S 3 行）。OpenEmbedded 上游 master 也做了同样修改
   （`0001-asm-Delete-.func-.endfunc-directives.patch`）。
4. **补丁 0002（musl ioctl）**：`main.c` 使用 `ioctl()` 却未包含
   `<sys/ioctl.h>`，glibc 经其它头间接暴露而 musl 不会，交叉编译报
   C99 隐式函数声明警告；补 include 消除（本机实测加补丁后 0 警告）。
5. **无 install 目标**：package() 直接把源码树中的 `tinymembench` 拷到
   `bin/`，`LICENSE` 拷到 `licenses/`。
6. **ELF 签名**：OHOS 内核要求可执行文件签名，package() 内（仅
   os==OHOS）执行 `llvm-objcopy --remove-section .codesign` +
   `binary-sign-tool sign -selfSign 1`；工具不存在时跳过并告警（与
   simh/3.8.1 相同策略，由 CI/消费端补签）。
7. **无上游测试**：验证 = 完整构建 + 消费端运行完整 benchmark 并断言
   输出结构（banner / 带宽段 / 带宽行数 ≥10 / 延迟段 / 延迟数据行 /
   退出码 0）。
8. **运行时长**：完整 benchmark 数分钟（每基准自适应重复×每轮 ≥0.5s；
   延迟部分 64MiB 缓冲×hugepage/非hugepage 两轮），test_package 超时
   设 1200s，真机排单时按重任务错峰。

## 验证结果

### 本机前置验证（W4，2026-09-29，本机 = Windows + DevEco OHOS SDK clang 15 + Conan 2.29.1 + Python 3.12）

- **SHA256 复核**：下载
  `https://github.com/ssvb/tinymembench/archive/refs/tags/v0.4.tar.gz`
  → `e37a26…f23d`，与 conandata.yml 声明一致；tarball 单一根目录
  `tinymembench-0.4/`（strip_root=True）。
- **上游信息**：tag `v0.4`（注意不是 `0.4`，无 v 前缀的归档 404）；
  tarball 含 LICENSE/Makefile/version.h（VERSION "0.4"）与 4 组架构
  汇编；无任何测试文件。
- **补丁可应用性**：两补丁对原始源码树按序 `git apply --check` 通过，
  应用后与验证编译所用源码树逐文件一致（aarch64-asm.S / main.c /
  x86-sse2.S diff 均为 0）。
- **OHOS 交叉编译**（本机无 make，用脚本复现 makefile 的编译/链接
  规则；`clang --target=aarch64-linux-ohos --sysroot=<SDK sysroot> -O2`）：
  - 无补丁：`aarch64-asm.S` 报 `unknown directive .func`，编译失败。
  - 仅补丁 0001：全部目标编译、链接成功，`main.c:56` 残留 ioctl
    隐式声明警告（1 warning）。
  - 补丁 0001+0002：**0 警告**，链接 exit=0。
- **产物核验**：`llvm-readelf -h` → `ELF64 / AArch64`；
  `llvm-readelf -d` → NEEDED 仅 `libc.so`（musl，无 libm 残留——
  musl 的 libm 并入 libc，链接 `-lm` 为空链接，符合预期）。
- **SDK sysroot 核验**：`usr/include/linux/fb.h` 存在，framebuffer
  测试代码可直接编译。
- **语法/结构检查**：`python -m py_compile`（conanfile.py、
  test_package/conanfile.py、test_tinymembench.py）通过；conandata.yml /
  manifest.yaml / test_package/MANIFEST.yml `yaml.safe_load` 通过。
- **git 检查**：`git diff --cached --check` 仅对补丁文件中来自上游
  源码的上下文行尾随空白告警（上游源码固有，补丁上下文必须保真才能
  应用；仓库 CI 无 diff --check 门禁）；变更范围仅
  `archives/t/tinymembench/0.4/` 9 个文件。
- **未执行**（如实记录）：本机无 OHOS 运行环境/模拟器，未运行产物
  与 test_package；`conan create` 完整流程未在本机执行（无 OHOS
  profile 依赖链，交由真机/shadow CI 的隔离 job runner 执行）。

## 下一步（真机/shadow CI 命令）

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job tinymembench-0.4 \
  --package archives/t/tinymembench/0.4 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/tinymembench-0.4/run-conan-heavy.sh"
```

重点记录：L0-L5 结果、test_package 断言输出（真实带宽/延迟数字）、
binary-sign-tool 签名后能否 exec。

## 真机 shadow CI 迭代记录

| 项 | r1 | r2 | r3 |
|---|---|---|---|
| job 名 | tinymembench-0.4-20260929 | 同左 | 同左 |
## 真机 shadow CI 迭代记录（job: tinymembench-0.4-20260929）

| 项 | r1 | r2 | r3/r4 | r5 | r6（最终） |
|---|---|---|---|---|---|
| 排队 wait_seconds | 5 | ~5 | ~5-137 | — | 137 |
| exit code | 1 | 1 | 1 | 1 | **0** |
| 门禁 | KC fail | L0 pass，create 失败 | export() 崩 | build() env 参数错 | **G0/L0/L1/L4/L5 全 pass，L2 skip（预期），100%** |
| 报错原文 | `build_and_test.sh:980: permission denied: bash` | `FileNotFoundError: …/s/patches/0001-…patch` | `TypeError: expected str…not NoneType`（export_conandata_patches） | `AssertionError: env argument to ConanFile.run() should be a list` | — |
| 根因 | runner 环境 PATH 缺 `/data/service/hnp/bin`（bash 所在，坑清单第 6 条） | patches/ 未导出进配方缓存，`apply_conandata_patches` 在 source() 找不到补丁 | conan 2.29.1 export() 阶段 `export_sources_folder` 恒为 None，`os.path.join(None,…)` 崩；加 exports_sources 后仍崩 | `self.run(env=dict)` 不合规（conan 2.x 只接受 list/None） | — |
| 解法 | 启动 runner 前 `export PATH=/data/service/hnp/bin:$PATH` | `exports_sources = "patches/*"` | 删除 export() hook，exports_sources 单独即可（本地 conan 2.29.1 复现验证后上真机） | 去掉 env 参数（WINDIR 有命令行 CC= 覆盖兜底，设备无 WINDIR） | — |

### r6 最终结果（2026-09-29，真机 shadow CI，排队 137s）

```
G0_RESULT=pass          （知识图谱 541 条目）
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: tinymembench version/help failed
                        （预期降级：main(void) 无参数解析，--version/--help
                          被忽略直接跑 benchmark，探测不过属正常）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Pass rate: 100.0% (1/1)   exit code 0
```

test_package 消费者断言全过：

```
OK: banner, bandwidth (22 lines), latency sections all present, exit 0
```

22 条带宽行 = 13 C 变体 + 2 libc（memcpy/memset）+ 7 AArch64 汇编
（NEON LDP/STP copy、LD1/ST1 copy、STP/STNP fill 等），与 asm-opt.c
的 aarch64 基准集完全吻合；延迟段表头与数据行断言通过。产物为
OHOS aarch64 ELF（NEEDED 仅 libc.so），包内签名步骤在真机 runner
环境按 simh 同款 best-effort 逻辑处理。

### r2 附注

G0/G0e/L0 在 r2 已全过（版本无冲突、commands.json type=tool 有效、
目录结构合规）；source() 经 gh-proxy 镜像下载 v0.4.tar.gz 成功、
SHA256 校验通过。CI 预下载脚本会把 conandata.yml 的 url 改写成镜像
列表并在构建后还原，与本包无冲突（curl 缺失时预下载跳过，conan 自身
下载器工作正常）。

## PR（W6）

- 平台：AtomGit OpenHarmonyPCDeveloper/build_in_harmonyos
- PR：#13716（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13716）
- 标题：`【积分赛】feat(tinymembench): 0.4 适配 HarmonyOS PC`
- 任务分支：`feat/tinymembench-0.4`（自 `feat/tinymembench-0.4-codex`
  重放，head sha 07700084fe），目标 main（基线 317e16ed5a）
- 正文：按积分赛事PR模板 B 类路径填写（上游 0 用例清点证据 + 补全
  8 项鸿蒙特有消费者断言 + 真机 6 轮门禁结果）
- issue：待补（按当前轮次指示跳过，PR 前未建）

### PR 审查跟进（W6 续）

- CI：#64335 全绿（首次 #64331 为 checkout 下载 PR diff 瞬时网络
  超时，非包问题，重建即过）。
- pc-pr-review 审查（16:33）：11+1 条规则中仅 rule6 FAIL——
  「无 AI 检视评论」，因 atomgit-bot 的 AI 代码检视多次触发
  （11:01 / 14:21 / 18:14）均停留在「进行中」未返回结果；其余
  规则（模板/测试口径/改动范围/CI/分支/鸿蒙特有测试等）全 PASS，
  上游 N 实测核实 0=声明 0 未少报。
- 处置：推送新 commit 刷新 PR diff 重置检视流水线，并在 AI 检视
  产出后回复审查意见并标记已解决。
