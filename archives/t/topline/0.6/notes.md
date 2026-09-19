# topline 0.6 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-19
- 编译器: clang（OHOS aarch64 工具链，经 conan profile `tools.build:compiler_executables` 注入）
- 状态: built
- worktree: `~/qzy/GLM-57-topline-0.6`，分支 `feat/topline-0.6`
- CONAN_HOME: `~/tmp/ch/home-glm57-topline`（复制自 home-zchunk 的 global.conf + remotes.json）

## W0/W0b 与语言预检
- W0 依赖检查：preflight_check.sh topline/0.6 → 无依赖声明（上游零外部依赖，Makefile 不链接任何库），通过。
- W0b 历史经验：归档树无 topline 历史归档/notes（首适配）。注：登记表备注曾写 "top 风格 IO 监控（C，ncurses）"，
  实际勘察 Makefile 后确认**不链接 ncurses**（纯 /proc 读取 + 终端输出），无该依赖。
- 语言预检 lang-preflight：task=cpp，detected=c（c↔cpp 兼容族），4 个 .c 主体占比 100%，exit 0 通过。

## 编译步骤
1. `python3 scripts/ohc-run.py init-build topline 0.6 --url=<官方 tag tarball>`（源码落 `~/tmp/builds/topline-0.6.work`）
2. 手动编译探针：`make CC=clang CFLAGS='-Wall -O2'` → 一次通过（clang 15，仅 1 条上游自带
   `disk.c:66 array index -1` 警告，属上游代码风格，不影响构建）
3. `conan-init topline 0.6` 生成骨架 → 按 vlevel 0.5.2（同类纯 Makefile 工具）改写 conanfile.py：
   package_type=application，build() 显式 `make CC=<conf clang> CFLAGS='-Wall -O2'`，
   package() 拷贝 `topline` 到 bin/，软件级 commands.json（R38，type=tool）
4. `conan-verify topline 0.6`（G0-G4/L2/L4/L5 + 消费者测试）

## 上游测试账本（五维，rule4 口径）
| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | Makefile 无 check 目标、无 tests/ 目录、源码无测试注册宏（见 test_package/MANIFEST.yml 证据） |
| N_registered | 0 | 同上 |
| N_executed | 0 | 上游无测试可执行 |
| 未执行分类数 | 0 | — |
| N_consumer（新增消费者测试） | 1 | test_package/test.c：fork+exec 真实 topline 二进制，重定向 stdout 采样 3 秒后 SIGTERM，断言 ①exec 成功（非 127）②产出非空监控输出 ③输出含数字统计 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 工具链无 gcc/cc，上游 Makefile 硬编码 `CC=gcc` | 上游假设 GNU 环境 | 配方 build() 显式传 `CC=<conan compiler_executables c>`（惯用法同 vlevel 0.5.2） |
| 2 | G2 首跑消费者测试失败：`Can't open /proc/diskstats: Permission denied`，进程 die() 退出 | HarmonyOS PC 上 `/proc/diskstats` 是指向 `/sys/block/diskstats` 的符号链接且仅 root 可读（SSH 用户直读同报错），而 `/proc/stat` 可读；上游 `init_disks()` 打不开即 `die()`，属致命路径 | 补丁 `patches/0001-disk.c.patch`：`init_disks()` 失败改为 stderr 告警（磁盘监控禁用），`do_disks()` 对 `ds==NULL` 早退 → 降级为纯 CPU 监控（知识图谱近亲 E031 为 htop 的 /proc 权限问题、方案 sudo-run，CI 环境不适用） |
| 3 | 补丁 1 后消费者测试仍零输出（`topline produced no output`） | 主循环靠 `if (!delay.tv_sec && !delay.tv_usec)` 判断采样时机，依赖 pselect 回写剩余 timeout 归零；musl/HarmonyOS 的 `SYS_pselect6` 不修改 timeout（上游目标平台 select() 语义会归零），`delay` 恒为 interval → `do_line(0)` 永不执行 | 补丁 `patches/0002-topline.c.patch`：每轮迭代末手动清零 `delay`，采样恢复 interval 节奏（行为与上游设计意图一致：定期采样 + 提前唤醒泵子进程输出） |

## 源码修改

| 补丁 | 内容 | 原因 | 结果 |
|------|------|------|------|
| `patches/0001-disk.c.patch`（refresh-patch --auto 生成，+7/-1） | `init_disks()`：fopen 失败由 `die()` 改为 stderr 告警；`do_disks()`：新增 `if (!ds) return;` | 平台限制：/proc/diskstats 仅 root 可读（见上） | topline 可在 OHOS 正常启动，输出 CPU 监控行（磁盘列按平台限制省略）；未删除/静默任何上游行为，降级路径有明确 stderr 提示 |
| `patches/0002-topline.c.patch`（refresh-patch --auto 生成，+7/-0） | 主循环 pselect 后手动 `delay.tv_sec=0; delay.tv_usec=0;` | musl pselect6 不回写剩余 timeout（见上） | 采样按 interval 正常输出；子进程输出泵（copy_line）路径不变 |

## 依赖版本

无外部依赖（零依赖包）。

## 验证结果

```bash
# conan-verify：G0-G4/L2/L4/L5 全绿（配方验证通过，可标记 built）
python3 scripts/ohc-run.py conan-verify topline 0.6   # ✅ 配方验证通过
# W3 本地 CI 模拟（finish step 5，与 CI 同源）
python3 scripts/ohc-run.py finish topline 0.6 built   # ✅ FINISH_EXIT=0
# 消费者测试（conan create 真实执行，reports/conan-create.log:132）
topline consumer test: captured 106 bytes of monitor output   # 新增 1/1 通过
# 上游测试：N_static=0（无测试套件），无执行项，未伪报通过率
```

## 路径 A/B 判断

**结论：路径 B（A+B 申报）。** 判断依据（2026-09-19 首次真实构建后作出）：

- **触发实例**：G2 消费者测试真实复现 `fopen("/proc/diskstats")` EACCES → 上游 die() 启动失败（非构造场景）。
- **稳定错误签名**：`Can't open /proc/diskstats: Permission denied`（SSH 用户直读 /proc/diskstats 同样 EACCES）。
- **根因与最小复现**：HarmonyOS PC 虚拟化环境将 diskstats 以 `/proc/diskstats → /sys/block/diskstats` 符号链接
  暴露且仅 root 可读；`head -c 100 /proc/diskstats` 即 Permission denied；`/proc/stat` 同期可读（CPU 维度可用）。
- **已尝试方案**：①直接读取（失败，EACCES）；②知识库近亲 E031 的 sudo-run 方案（conan/CI 环境无 sudo，不可用）；
  ③代码级优雅降级（本次采纳，补丁 +7/-1）。
- **最终方案与验证**：init_disks 告警 + do_disks NULL 早退；消费者测试真实运行 topline 二进制断言 CPU 监控输出。
- **跨仓库复用价值**：适用于所有读取 /proc/diskstats 的监控类工具（sysstat/iostat/dstat/nmon/htop disk 模式等）
  在 HarmonyOS PC 的适配；E031 只给了 sudo-run，对 CI/包环境无效，本次补充"代码级降级"这一 CI 可用方案。
- **适用范围/反例/解除条件**：适用于"磁盘统计为辅助功能"的工具；反例是磁盘统计为核心功能的工具
  （如 iostat 本体）不能降级了事（需另寻数据源或按无法适配处理）；若未来平台放开 /sys/block/diskstats
  读取权限，本补丁的降级路径自动失效（不影响正常读取路径）。
- **查重结论**：`grep index.tsv` 命中 E031（htop，/proc Permission denied，sudo-run）与 E303（受限进程
  文件系统探测）；无 diskstats 专属条目；E031 方案在 CI 场景不可用，本次新增价值成立。知识草稿将引用
  E031 作关联条目。

路径 B 交付物：知识草稿（.kv/.md，draft-review 通过）+ 知识库扩展 Issue + PR 单列"路径 B 知识贡献说明"。

## 注意事项

- topline 是交互式监控器（pselect6 循环），消费者测试以 fork+采样+SIGTERM 方式验证，勿在前台直接运行。
- 上游 `disk.c` 的 `&bdev[-1]` 写法产生 -Warray-bounds 警告，属上游代码，未修改（保持上游测试/代码原样）。
---

**编译结束**: 2026-09-19 02:31
**最终状态**: built
