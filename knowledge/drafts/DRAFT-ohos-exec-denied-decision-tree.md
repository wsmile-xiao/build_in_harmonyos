# DRAFT-ohos-exec-denied-decision-tree — OHOS 设备 exec 拒绝(126)四级判别决策树与修复矩阵

> 类型:通用知识条目(收敛型)——把散落在 E077/E486/E386/E429/E517/E653/DRAFT-cdb/canfigger
> 中的单点经验收敛为一条可执行的判别流程,并新增第四签名态(ld.bfd 无效占位段)。
> 每个单点条目仍然有效;本条目是**路由表**,不替代它们的机理细节。

## 使用说明

**何时用**:在 OHOS 真机/shadow CI 上,任何新编译或新落盘的文件执行时报
`Permission denied`(EACCES)或 `Operation not permitted`(EPERM)、exit 126,
且不能一眼看出原因时,按本树 **Level 0 → 4 顺序**逐级排除。禁止跳级猜测
(历史教训:直接归因"分区 noexec"或"权限位"而漏掉真正的签名问题,浪费整轮真机窗口)。

**输入**(4 个廉价观测,合计 <1 分钟):
1. 错误原文(区分 EACCES / EPERM,shell 文案分别是 `Permission denied` /
   `Operation not permitted`)
2. 被执行文件的**创建方式**(本次构建新产出 / 从别处复制 / 系统预装)
3. 文件所在**分区**(HMDFS `/storage/...` vs 应用沙箱 `/data/storage/el2/...`)
4. `readelf -S <file> | grep -A1 codesign` 的输出(有无 `.codesign` 段、段尺寸)

**输出**:命中决策树某个叶子 → 得到唯一修复动作(见修复矩阵)。

## 适用范围

- 任何在 OHOS 设备上执行**运行时新产出文件**的场景:autotools 的
  configure/conftest/config.status、CMake/Meson 消费者测试、go test -c 产物、
  编译器引导(build 阶段 exec 刚链出的辅助程序)、Conan test_package 消费者二进制。
- 不适用于:exit 127(not found/解释器缺失,先查 PATH 与 shebang)、
  exit 139(加载后 SIGSEGV,见 DRAFT-canfigger-resign-crash 的重签段不兼容场景)。

## 判别决策树

```
Level 0  错误语义
├─ 127 "not found / inaccessible"      → 路径/解释器问题,退出本树
├─ 126 "Permission denied"   (EACCES)  → 内核按"无有效签名或无执行位"拒绝 → Level 1
└─ 126 "Operation not permitted"(EPERM)→ 签名无效或分区策略拒绝      → Level 1

Level 1  文件来源
├─ 系统预装/已签名的既有文件            → 检查 mode/owner,退出本树
└─ 本次构建/复制新产出                  → Level 2

Level 2  分区执行能力
├─ /data/storage/el2/... (应用沙箱)     → 沙箱整体拒绝 execve(E653 实证 dlopen 同),
│                                         与签名无关 → 迁回 HMDFS(如 conan-home),
│                                         或用 `sh <script>` 显式解释器执行脚本
└─ HMDFS /storage/...                   → Level 3

Level 3  签名四态(readelf -S 看 .codesign)
├─ 无 .codesign 段                      → 态A 未签名 → strip(若有)后 binary-sign-tool
│                                         -selfSign 1 签名(E077)
├─ 有,尺寸 0x1000,来自 hnp clang/lld   → 态B 链接器内嵌有效 ad-hoc 签名:
│                                         可执行文件 OK;共享库**禁二次自签**
│                                         (重签产物 musl 加载器 SIGSEGV,canfigger)
├─ 有,尺寸异常(实测 0x22000),来源
│   ld.bfd(-fuse-ld=bfd)链接 ohos 目标  → 态C **无效占位段**(本条新增):sign 工具
│                                         报 "section already exists" 后静默失败,
│                                         文件带无效签名 → exec EPERM。
│                                         修复:llvm-objcopy --remove-section
│                                         .codesign 后再签(readelf 应见 0x1000)
└─ 字节里含 "codesign" 字样但 readelf    → 态D 内容假阳性(E429):grep 文件内容
    无该段                                判签名不可靠,必须以 readelf 段表为准

Level 4  仍不通
└─ 签名有效性是设备绑定的:构建机签好随
   包分发的 ELF 在另一台设备可能无效
   (E517)→ 在消费设备上对任务私有副本
   剥段重签,校验 .codesign 计数恰为 1
```

## 修复矩阵(叶子 → 动作)

| 叶子 | 动作 | 关键命令 |
|---|---|---|
| L2 el2 分区 | 产物迁回 HMDFS 执行;脚本用 `sh script.sh` | `CONAN_HOME=<HMDFS 路径>` |
| L3 态A | 剥段(容错)+自签+恢复执行位 | `llvm-objcopy --remove-section .codesign f 2>/dev/null; binary-sign-tool sign -inFile f -outFile f.signed -selfSign 1; mv f.signed f; chmod 755 f` |
| L3 态B(可执行文件) | 保持现状,不要重签 | — |
| L3 态B(共享库) | **禁止** selfSign 重签(canfigger) | — |
| L3 态C | 先 strip 占位段再签(注意 sign 必须是最后一次内容修改) | `llvm-objcopy --remove-section .codesign f` 然后 sign |
| L3 态D | 弃用内容 grep,改用 readelf 段表判签名 | `readelf -SW f \| grep -c codesign` |
| L4 跨设备 | 消费端私有副本剥段重签(E517) | 同态A,作用于副本 |

## 示例(make/4.4.1 真机走树实录,2026-10-04)

- r1:configure `Permission denied` 126 → L2 误判为 HMDFS noexec,迁 CONAN_HOME
  到 el2 → r2 仍 126(修正:el2 整体 noexec)→ 回迁 HMDFS + `sh configure` + CC 走
  编译+签名 wrapper(E486 模式)。
- r5/r6:链接出的 make 执行 EPERM → L3:`.codesign` 存在但 0x22000,来源
  `-fuse-ld=bfd` → 态C(strip 占位后重签)→ make3/make4 验证可执行。
- 对照实验定锚:同 wrapper 编译的 hello(18KB/420KB,含 -fuse-ld=bfd)签名恒
  0x1000 且可执行;仅 make 链接触发占位段——占位段触发与目标代码规模相关,
  **判别必须逐文件 readelf,不可按文件类型或大小推断**。

## 查重声明

- E077:态A 的标准流程(本树引用,不重复)。
- E486:编译器 wrapper 即时签名架构(本树的 Level1/3 实现载体)。
- DRAFT-canfigger-resign-crash:态B 共享库禁重签(本树引用)。
- E517:态 L4 跨设备签名失效(本树引用)。
- E429:态D 内容假阳性(本树引用)。
- E653:L2 el2 分区 dlopen 拒绝(本树补 execve 维度与 CONAN_HOME 迁移反例)。
- DRAFT-cdb-20251021:`-fuse-ld=bfd` 环境异构(invalid linker name)——本树态C
  的前置环境检查。
- **新增**:态C(ld.bfd 无效占位 .codesign,0x22000)与"四级判别顺序"本身。

verify_builds: make/4.4.1 真机 r1→r9 全程实证;态C 修复后 GNU Make 4.4.1 --version 与 test_package 4/4 断言通过(runner exit 0)。
authors: codex
source_commit: feat/make-4.4.1-codex
