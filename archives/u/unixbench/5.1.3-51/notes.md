# unixbench 5.1.3-51 适配笔记

## 编译环境
- 构建系统: makefile（上游 UnixBench/Makefile，1 个 portability 补丁）
- 编译日期: 2026-09-27
- 编译器: clang（OHOS SDK 15.0.4，aarch64-ohos；make CC=<clang> 覆盖硬编码 CC=gcc）
- 状态: built

## 编译步骤

```sh
# 源码：https://codeload.github.com/kdlucas/byte-unixbench/tar.gz/refs/tags/v5.1.3
#（GitHub 官方归档端点，等价于 /archive/refs/tags/v5.1.3.tar.gz）
# SHA256: 3a6bb00f270a5329682dff20fd2c1ab5332ef046eb54a96a0d7bd371005d31a3（真机重下核对一致）
cd UnixBench            # 解包后源码位于 byte-unixbench-5.1.3/UnixBench/（配方的 source() 会提升为源码根目录）
patch -p1 < .../patches/0001-src-arith.c.patch   # conan create 中由 apply_conandata_patches 自动应用
make CC=clang           # 18 个基准程序产物 → pgms/
make CC=clang check     # 发行完整性检查（编译 + testdir/pgms 文件齐备）
```

`package()` 将完整运行目录安装到 `bin/unixbench/`（Makefile、Run、USAGE、README、
WRITING_TESTS、pgms/、src/、testdir/ 与预编译产物；tmp/、results/ 以占位文件保留），
软件级 `commands.json` 按 R38 声明工具包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 默认 `CC=gcc`，OHOS 无 gcc | 上游 Makefile 硬编码 | 构建命令 `make CC=<clang>`（R33：编译器取 Conan conf，不写死路径） |
| 2 | `Run` 直接执行报 shebang 错误 | `#!/usr/bin/perl` 在 OHOS 不存在（perl 位于 Harmonybrew 前缀） | 使用 `perl Run` 调用；README 说明 |
| 3 | 报告固定 `0 CPUs in system` | OHOS `/proc/cpuinfo` 字段名与 Run 期望不同（`BogoMIPS`/`Features` 大小写、无 `model name`）→ `getCpuInfo()` 返回空数组 | 平台行为，保持上游代码不动；在 README/test-report 如实标注，跨平台比较需说明 |
| 4 | `System:` 显示 `Toybox`、`Machine: aarch64 ()`、Language 为空 | Toybox `uname -o` 输出 `Toybox`；`uname -i` 空；无 `locale` | 平台行为，如实记录（B 分析素材） |
| 5 | stderr 的 Perl uninitialized 警告 | `locale`/`3dinfo`/`runlevel`/`who` 缺失导致空值 | 非致命（getCmdOutput 设计容忍空值）；报告字段降级 |
| 6 | 复制目录后 `Run` 触发 `make` 且失败（gcc 缺失） | `Run` 启动时 `make check`；若时间戳顺序丢失（普通 `cp -r`）则尝试重建 | 用 `cp -a` 保留时间戳；README 说明（预编译产物时间戳新于源码即不重建） |
| 7 | 图形项与 dc/C 项无法运行 | 无 X11/x11perf；无 dc；Run 内 `$cCompiler='gcc'` 硬编码 | 逐项 SKIP 并登记原因（非适配裁剪：图形项上游默认即不构建） |
| 8 | 算术族（Run 可选 6 项：arithoh/short/int/long/float/double）输出 `COUNT\|0`，Run 以 `Can't take log of 0` 中止（rc=25） | clang -O2 将 SIGALRM 处理器读取的全局计数器 `iter`（arith.c）保持在寄存器，纯计算循环内无外部调用 → 信号处理器读内存恒为 0（arith 家族 7 个二进制产物的计数逻辑同源） | 补丁 0001：`volatile unsigned long iter;`；最小矩阵实测 -O0=4676336 / -O2=0 / -O2+volatile=526329615（3 秒计数） |

## 源码修改

`patches/0001-src-arith.c.patch`（唯一补丁，portability）：`src/arith.c` 全局计数器
`unsigned long iter;` → `volatile unsigned long iter;`。不改断言、不改测试、不改基准算法，
仅恢复「信号处理器可观察到计数更新」的语义（与 gcc 构建的上游行为一致）。其余源码零改动。

## 依赖版本

无第三方依赖（仅 POSIX libc + Perl 运行时）。

## 验证结果

```text
# 真机基准实跑（子集口径：-i 1；通过口径 = 有效分数 + 退出码 0；完整输出摘要见 test-report.md §2-§3）
#   index 12 项：rc=0，Index Score 189.7
#   算术 6 项：rc=0（补丁后，计数 1.8e8+ lps）
#   非索引 3 项（hanoi/grep/sysexec）：rc=0
#   文件写/读/拷贝 9 项：rc=0；shell16：rc=0
#   SKIP 实测（graphics/dc/C）：rc=1 并留错误输出
#   （原始 device-*.log 与报告副本已按评审意见/规则 19 从提交中移除，留存构建工作区）
# 共享设备负载偏高（loadavg ~20-24，其他成员构建并行），分数仅供功能验证。
# test_package（conan create 消费者回归）：18 条断言全过（5 项基准实跑 + 报告断言 + 平台签名 + 负向对照）。
```

补丁前后对照（3 秒计数，最小矩阵，见 test-report.md §4）：
`-O0`=4676336 / `-O2`=0（复现） / `-O2`+volatile=526329615（修复生效）。

## 对话记录

### 对话 #1（2026-09-27，W0–W1）
- 环境与发布检查：`conan download unixbench/5.1.3-51 -r=ohpcd` 返回 not-found 特征错误（对照 bogus 包同特征、lutok/zlib 正常）→ 未发布，可继续。
- 真机探针：`uname -o`=Toybox、`uname -i` 不支持、`/proc/cpuinfo` 字段名与 Run 期望不符（model name/bogomips/flags 命中数 0）、无 X11 头、工具 perl/make/clang 在、gcc/dc/3dinfo/x11perf/locale 缺。
- 建隔离 worktree `unixbench-wt`（`c611f7d61`），init-build（sha256 复核一致）+ lang-preflight 通过（detected=c，c↔cpp 兼容族）。

### 对话 #2（2026-09-27，W1–W2 适配）
- 源码勘察：Run 的 testList 共 41 基准项；默认 index 12 项；图形项上游默认关闭；`make CC=clang` 零改 Makefile 可构建 18 个基准程序。
- 首跑默认子集发现算术族 `COUNT|0` → Run `Can't take log of 0`（rc=25）。最小矩阵定位：clang -O2 将 SIGALRM 处理器读取的全局 `iter` 寄存器化；补丁 0001 加 `volatile` 修复（-O0/-O2/-O2+volatile = 4676336 / 0 / 526329615）。
- 配方：conanfile（Makefile 直调 + 源码根提升 + 预编译发行）、conandata（codeload 官方源 + filename + 补丁清单）、test_package（18 断言，含 arithoh 回归）、commands.json/README/软件级 manifest。

### 对话 #3（2026-09-27，W2 证据）
- 干净重建后全量实跑：index 12 项（Index 189.7）、算术 6 项、非索引 3 项、文件 9 项、shell16 全部 rc=0；图形/dc/C 三组失败尝试留证。
- 期间经历共享设备资源枯竭（loadavg 峰值 ~40、fork EAGAIN）与设备重启；恢复后重跑，index 首轮超时（资源）后重试通过。

### 对话 #4（2026-09-27，W3–W4）
- conan-verify G0–G4 + L2/L4/L5 通过（补丁在 conan create 中生效，test_package 18/18）；本地 CI 门禁（L0/L1/L1e/L4/L5）通过；finish（W2/W3）完成，`.ci-result.json` exit_code=0。
- 已知外部项：finish step5b 因仓库既有条目（E219/E253/E305 字段为空，非本包）标注未过（非阻塞）；gen_summary 因 qpdf 历史 manifest 解析崩溃（非本包）；G0 clean-verify 对嵌套 tarball 的补丁根目录假设与 conan 路径不同（非阻塞，conan create 已端到端验证补丁）。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/unixbench/Run | Perl 驱动脚本 |
| bin/unixbench/pgms/* | 18 个预编译基准程序 + gfx-x11/multi.sh/tst.sh/index.base |
| bin/unixbench/src/、testdir/ | 上游源码与测试数据（重编译/运行所需） |
| licenses/README.license | 许可证来源说明（GPL-2.0，上游无独立 LICENSE 文件，不伪造文本） |

## 注意事项

- **版本口径**：平台任务版本 `5.1.3-51`（`-51` 为发行版 pkgrel），上游 tag 为 `v5.1.3`；配方/目录用平台版本值。
- **分数解释**：本机为共享设备（跑分期间负载较高），分数仅供功能验证与相对比较，不代表设备基准性能；
  且 `0 CPUs` 识别使套件只做单副本轮，与 Linux 上"单副本 + N 副本"两轮结果不可直接对比。
- **图形项**：保持上游默认关闭，不属适配裁剪；如需在支持 X11 的环境使用，可用
  `make GRAPHIC_TESTS=defined CC=clang` 并自备 x11perf。
- 复制运行目录务必保留时间戳（`cp -a`），或准备 clang 供 `make CC=clang` 重建。

---

**编译结束**: 2026-09-27
**最终状态**: built
