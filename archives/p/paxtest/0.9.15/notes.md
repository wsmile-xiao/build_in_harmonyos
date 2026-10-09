# paxtest 0.9.15 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile → `Makefile.psm`；5 个 portability 补丁）
- 编译日期: 2026-09-27
- 编译器: clang（OHOS SDK 15.0.4，aarch64-ohos；`make CC=<clang> LD=<ld>` 覆盖上游硬编码的 `CC=gcc`/`LD=ld`，R33）
- 状态: built

## 上游测试清点（R51 三步法之 1：适配前清点）
- `tests/` 目录: **无**（上游无独立测试目录）；ctest/pytest 注册: **无**（N_static=0 / N_registered=0）。
- 测试面 = 可执行测试程序本体：**34 个测试程序**（EXEC 5 / MPROT 5 / SHLIB 2 / MPROTSH 3 /
  RAND 13 / FAST_RAND 2 / RET 2 / RETX 2）+ 15 个 helper + `genpaxtest` 生成的 `paxtest` 驱动。
- 运行方式：`./paxtest kiddie|blackhat [logfile]`（一次运行全部测试项）。

## 编译步骤

```sh
# 源码：https://codeload.github.com/opensrcsec/paxtest/tar.gz/refs/tags/paxtest-0.9.15（官方归档端点）
# SHA256: 51fe6c1eef8050fa73f2a8e620cf70a5a34a79d68cb22d07b941cf8e6c0677e7（真机重下核对一致）
# 版本口径：上游官网 pax.grsecurity.net 只列到 0.9.7-pre4；0.9.15 的官方发布在 Git 仓库 tag。
#   该 tag 归档与 Debian orig（paxtest_0.9.15.orig.tar.gz）解包后逐文件一致（真机 diff -r 实测），
#   采用官方 tag 归档端点作为源。
cd paxtest-paxtest-0.9.15
make -f Makefile.psm CC=clang LD=ld -j1     # 顶层 make linux 的等价展开（R33：CC/LD 取 Conan conf）
# 产物：paxtest 驱动 + 34 个测试程序 + 15 个 helper + shlibtest*.so + chpax/paxbin
```

`package()` 将完整运行目录安装到 `bin/paxtest/`（含 C 源码与 Makefile 便于重建），
软件级 `commands.json` 按 R38 声明工具包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | chpax 编译失败：`fatal error: 'a.out.h' file not found` | chpax-0.7 支持 pre-ELF 的 a.out 格式，`chpax.h` 无条件 `#include <a.out.h>`；musl 系 sysroot 不提供该头，aarch64 上亦不存在 a.out 二进制 | 补丁 0001-0004（portability）：移除 chpax 的 a.out 支持（aout.c 函数体、chpax.c 全局、chpax.h include/声明、io.c 检测分支）；aout.c 保留为说明性空文件以维持上游 Makefile 源列表不变 |
| 2 | exec 系测试失去判定力（修复前一律 Killed） | `shellcode.h` 无 aarch64 分支 → 回退到 x86 的 `RET`(0xC3)：ARM64 上可执行页与不可执行页都以信号终止，测试无法正判定 | 补丁 0005（portability）：增加 `__aarch64__` 分支（ARM64 `ret`，0xd65f03c0）；修复后可执行页将正常返回（Vulnerable），不可执行页 Killed |
| 3 | `paxtest blackhat` 打印 INFO 并按 kiddie 语义运行 | `body.c` 的 blackhat 技巧依赖 GCC 嵌套函数（clang 不支持） | 上游实现限制（`#ifdef __clang__` 分支即上游代码）：如实记录；两模式均完整运行 |
| 4 | VDSO randomization 项中止：`./getvdso: No error information` | OHOS `/proc/self/maps` 无 `[vdso]` 标记 → getvdso 无输出 → randbody 的 fscanf 失败并 perror 中止该行 | 平台差异，如实记录（VDSO 随机化在本次结果中缺失；其余 12 项随机化正常） |
| 5 | Return to function (memcpy) 无输出行 | 该探测用 256 字节 memcpy 溢出 8 字节栈缓冲；aarch64 的返回地址在 x30 寄存器（非栈帧）→ 未劫持控制流，子进程正常退出（无结果输出） | 体系结构语义差异，如实记录（x86 上该探测用于判定；ARM64 下语义自然失效） |
| 6 | 驱动首行 `./paxtest[70]: ./clang: inaccessible or not found` | 上游 Makefile 以 `sh genpaxtest $(CC) $(TESTS)` 生成驱动，测试列表把 CC 首参带入（上游同款行为） | 无影响（`|| echo` 吞掉），如实记录 |
| 7 | chpax 运行报 `Wrong architecture (passed)` | 上游 ELF 机器列表（SPARC/ALPHA/X86_64/IA_64/PPC64）不含 EM_AARCH64 | OHOS 无 PaX 标志可设，chpax 本就是惰性工具；`paxbin` 调用失败被 `||:` 吞掉，不影响测试默认路径 |

## 源码修改

`patches/` 共 5 个补丁，全部为 portability（无平台宏、无绝对路径）：
- `0001-chpax-0.7-aout.c.patch` ~ `0004-chpax-0.7-io.c.patch`：chpax-0.7 的 a.out 支持移除
 （musl sysroot 无 `<a.out.h>`；aarch64 无 a.out 二进制）；
- `0005-shellcode.h.patch`：补 `__aarch64__` 的 ARM64 `ret` 序列，恢复 exec 系测试的判定语义。

不改 Makefile、不改测试判定/通过口径、不改被测逻辑。

## 依赖版本

无第三方依赖（仅 POSIX libc；构建期 GNU make + OHOS clang）。

## 验证结果

```text
# 真机实跑（证据见 reports/，HarmonyOS PC / HongMeng Kernel 1.12.0 / aarch64）
#   device-kiddie.log      kiddie 全量，driver rc=0（18:26:27–18:43:20）
#   device-blackhat.log    blackhat 全量，driver rc=0（18:43:41–19:01:15）
#   攻击探测（exec 5 + mprotect 5 + shlib 2 + mprotsh 2 + writetext 1）= 15/15 Killed（无可利用）
#   随机化（bits guessed）：anon 19 / heap ET_EXEC 19 / heap PIE 19 / main ET_EXEC 21 /
#     main PIE 22 / shlib 21 / VDSO 中止 / stack(SEG/PAGE) 21/21 / argv-env(SEG/PAGE) 21/21 /
#     shlibdelta(ET_EXEC/DYN) 23/23 / exhaust(@~0/@0) 22/22
#   返回攻击：rettofunc strcpy/strcpy PIE = "return address contains a NULL byte"（上游守卫分支）；
#     rettofunc memcpy/memcpy PIE = 无输出（aarch64 语义，见问题表 #5）
# 消费者测试：test_package/ 21 条断言（conan create 内真实执行，含负向对照）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/paxtest/paxtest | 驱动脚本（genpaxtest 生成） |
| bin/paxtest/{34 个测试程序} | exec/mprot/shlib/rand/ret 全量测试二进制 |
| bin/paxtest/{15 个 helper} | getamap/getheap/getmain/getshlib/getvdso/getstack/getarg/getexhaust 系 |
| bin/paxtest/{chpax,paxbin} | PaX 标志工具（OHOS 上惰性）；Makefile.psm 生成的包装 |
| bin/paxtest/*.c/*.h 与 Makefile* | 上游源码与构建脚本（可重建） |
| licenses/COPYING | GPL-2.0-or-later 许可证文本 |

## 注意事项

- **解读口径**：`Killed` = 攻击尝试被信号终止（目标内存不可执行/不可写，属保护生效的表现）；
  `Vulnerable` = 攻击代码实际执行成功（保护缺失，需要关注）；随机化的 `N quality bits`
  是采样估计（1500 次/项），不是安全保证。**"不可利用" ≠ "该项保护一定存在"**（如 NX 不启用时
  exec 测试也可能因其它原因失败）。
- **blackhat 语义**：clang 构建下 blackhat = kiddie + INFO 行（上游实现限制），不要把它当作
  更强的对抗测试来解读。
- **共享设备**：跑测期间 loadavg ≈ 20（其他成员构建并行）；随机化位数是功能验证数据，
  不宜作为设备间严格比较。
- `package()` 目录需整体复制运行（驱动用相对路径解析测试程序并自行设置 `LD_LIBRARY_PATH=.`）。

## 对话记录

### 对话 #1（2026-09-27，W0–W1）
- W0：`conan download paxtest/0.9.15 -r=ohpcd --only-recipe` 未命中（库未发布）；设备探针
  （uname/randomize_va_space=2/make/clang 可用，gcc 缺失）。
- W1：建隔离 worktree `paxtest-wt`（`c611f7d61`，分支 `feat/paxtest-0.9.15`）；init-build
  （Debian orig，sha256 复核 `d5538484…`）+ lang-preflight 通过（detected=c，c↔cpp 兼容族）。
- 预研结论复核：上游官网无 0.9.15；`opensrcsec/paxtest`（PaX/grsecurity 官方仓库）tag
  `paxtest-0.9.15` 存在，下载后与 Debian orig 解包逐文件一致 → 最终以官方 tag 归档为源
  （https://codeload.github.com/opensrcsec/paxtest/tar.gz/refs/tags/paxtest-0.9.15，
  sha256 `51fe6c1e…`）。

### 对话 #2（2026-09-27，适配构建）
- 首构建在 chpax 处失败（a.out.h）→ 补丁 0001-0004 移除 a.out 支持 → 全量构建 rc=0
  （驱动 + 34 测试 + 15 helper + shlibs）。
- 试跑 execstack 发现 Killed；源码检查确认 shellcode.h 无 aarch64 分支（回退 x86 RET）→
  补丁 0005 增补 ARM64 ret，重跑确认判定语义恢复（不可执行页 Killed）。
- conan-verify 首跑 G2 在 test_package 计数断言处失败（测试程序 34 个，脚本误写 33）→
  修正计数后复验通过（记录在案：off-by-one 由 G2 实测捕获，非产物问题）。

### 对话 #3（2026-09-27，真机实测）
- kiddie 全量实跑 17 分钟（rc=0）：攻击探测 15/15 Killed；随机化 12 项有效、VDSO 中止；
  rettofunc memcpy 无输出（见问题表 #4/#5）。
- blackhat 全量实跑 18 分钟（18:43:41–19:01:15，rc=0）：攻击探测与返回攻击结果与 kiddie 一致
  （15/15 Killed；“结果行”diff 仅 Mode 行与随机化采样涨落），body 类测试前打印 INFO 行（见注意事项）。
- 环境事件：测试期间共享设备 loadavg ≈ 20（其他成员 conan 构建并行），不影响功能结论。

### 对话 #4（2026-09-27，W2/W3/W4）
- 归档：conanfile/conandata/test_package（21 断言）/README/commands.json/manifest 就绪；
  5 个补丁经 conan create 端到端应用（test_package 21/21）。
- 门禁按序执行：conan-verify（G0–G4 + L2/L4/L5）→ 本地 CI 门禁 → finish（`.ci-result.json`）
  → W4 独立审计（`reports/audit-result.json`）；各门禁的最终状态以上述产物文件为准
  （本文件在提交前定稿时回填）。

### 对话 #5（2026-09-27，路径 B 交付）
- 用户决策：以【知识库扩展】（路径 A+B）提交。
- 新增知识草稿 `knowledge/drafts/E546-draft-9C4A-paxtest-ohos-memory-protection-probing.{kv,md}`：《OHOS 内核内存保护/ASLR 的探针测量
  与解读口径（含非 x86 探针适配）》；`draft-review` 预审建议 **create**（最高相似 E045=0.19）。
- 知识库扩展 Issue：[#3523](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3523)
  （与本 PR 双向关联）；PR 正文含「路径 B 知识贡献说明」小节（`reports/pr-body.md`）。
- 合并冲突处理（2026-10-04）：本草稿原文件名 `E545-draft-9C4A.*` 与另一并行任务的同编号草稿在
  main 发生 add/add 冲突；已合并 `origin/main`（`1262b4ac2`）并改名为
  `E546-draft-9C4A-paxtest-ohos-memory-protection-probing.*`（kv 的 `id:`/`doc_file:` 同步）；
  `draft-review` 复跑仍为 create；合并后本地 CI 与 W4 审计复验通过。

**编译结束**: 2026-09-27
**最终状态**: built
