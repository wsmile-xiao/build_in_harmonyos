# E563 — OHOS musl 空 libutil.a：-lutil 链接零贡献（pty 函数已并入 libc）

## 错误特征

- 上游 Makefile/configure 写死 `-lutil`，交叉链接不报错——但 `-Wl,-t` 追踪
  显示空档案从未贡献任何成员，`forkpty`/`openpty` 实际由 libc.so 解析。
- 极端情况下（HMDFS/E050 类库路径丢失）才会看到
  `unable to find library -lutil`。

## 触发条件

- 构建系统: 自定义 Makefile、autotools（`AC_CHECK_LIB(util, openpty)` 类探测）
- 阶段: linking
- 平台: OpenHarmony/HarmonyOS PC musl sysroot（musl 上游本身不提供 libutil）

## 根因分析

OHOS musl 把 BSD pty 接口（forkpty/openpty/login_tty）并入 libc 直接导出，
sysroot 仅为兼容构建脚本保留一个空壳 `libutil.a`（`!<arch>` 头、**0 成员**）。
ld 找到空档案即视为满足 `-l`，探测"成功"，但符号贡献为零：

```bash
ar t .../aarch64-linux-ohos/libutil.a | wc -l      # → 0
nm -D --defined-only .../libc.so | grep -cE "forkpty|openpty"  # → 2
clang --sysroot=$SR probe.c -lutil -o p -Wl,-t 2>&1 | grep -c libutil  # → 0
```

## 解决方案

### 推荐方案

配方不执行上游的 `-lutil`：按上游源码语义等价改写链接命令（mtm 案例：
复制 Makefile 的 mtm 规则去掉 `-lutil` 与 strip），或 patch 上游 Makefile
的 LIBS 行。目标函数已在 libc 中，去掉后链接依然解析成功。保留 `-lutil`
也无害（空档案无成员），但按"上游语义等价 + 可审计性"应去除。

### 禁止做法

- ❌ 为了让 `-lutil` "生效"而向 sysroot 手工注入非空 libutil.a——libc 已
  导出全部所需符号，注入重复副本违背单副本原则。
- ❌ 依 `-lutil` 探测"成功"就断定存在真实 libutil 符号依赖——空档案下
  探测必然成功，需用 `-Wl,-t`/`ar t` 实证。

## 验证

```bash
# 空档案 + libc 导出 + 链接零贡献三联证
ar t $SYSROOT/usr/lib/aarch64-linux-ohos/libutil.a | wc -l     # 0
nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep -E "forkpty|openpty"
clang --sysroot=$SYSROOT forkpty_probe.c -lutil -o /tmp/p -Wl,-t 2>&1 | grep -c libutil   # 0
```

## 关联条目

- 相关: E050（HMDFS 符号链接丢失导致 unable to find library——那是真正
  报错的形态；本条目是"静默零贡献"形态）
- 先例: bsdutils/4.4.1.1 conanfile.py:60、dtach/0.9 patches/0002-configure.patch
  （openpty 探测）、mtm/1.2.1 conanfile.py build()（去 -lutil 内联链接）

## 全量查重记录（2026-09-08）

主题词：forkpty / openpty / login_tty / libutil / empty archive /
merged into libc / musl PTY，及中文变体（空档案、空 archive、并入 libc、
并入libc、merged into libc、musl PTY）。

- `knowledge/graph/*.kv`（全部 540 条）：0 命中
- `knowledge/doc/`、`knowledge/operations/`（含 ohos-adaptation-patterns.md）：
  0 命中（唯一中文命中"pthread 并入 libc"属 glibc 主题，与本条目无关）
- `knowledge/*.md`（ARCHIVE-SPEC.md、README、musl-compat、error-patterns、FAQ）：
  0 命中
- `knowledge/drafts/`：0 命中（本条目自身除外）
- `knowledge/requirements/`：0 命中
- 结论：现有知识库未完整覆盖"OHOS musl 空 libutil.a 零贡献"形态，
  按 **路径 B**（创建唯一编号知识草稿）处理——本条目 E563 即为该草稿，
  编号在 graph/ 与 drafts/ 中唯一（E541 为最高已入图编号，E563 未占用）。
  后续由维护者在 KB 维护流程中正式入图。
