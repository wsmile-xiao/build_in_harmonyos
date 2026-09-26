# DRAFT: OHOS procfs 不提供 /proc/\<pid\>/fdinfo —— 运行期能力探测与诚实收窄输出

- **草稿 ID**: DRAFT-ohos-proc-pid-fdinfo-absent-capability-probe
- **来源库**: inotify-info 0.0.4（OHOS PC aarch64, clang 15.0.4 / OHOS SDK 26.0.0.18）
- **申报域**: 平台探测（八分类）；机理分层 L1（平台能力缺失）
- **状态**: 草稿（待主编 promote 为正式 E 条目；编号留待主编）

## 问题（真机实测）

依赖解析 `/proc/<pid>/fdinfo` 的进程内省工具（inotify 视角的 lsof、fd/watch
用量统计类）在 OHOS 真机上是**"构建运行全过、核心数据面结构性缺失"**：

1. **节点层（结构性缺失）**：OHOS 内核 procfs 不实例化 `/proc/<pid>/fdinfo`
   ——**自身进程亦 ENOENT**（`ls /proc/self/fdinfo` → No such file or
   directory），而 `/proc/self/fd` 正常存在。这是"节点根本不存在"，不是
   权限拒绝（区别 E031 的 SELinux Permission denied 族），**sudo 亦无解**。
2. **降级形态（工具仍可用）**：
   - `fopen("/proc/<pid>/fdinfo/<fd>")` 恒 NULL（inotify-info.cpp:329 的
     `if (fp)` guard 静默吞掉）→ watch 计数恒 0，被 watch inode/sdev→路径
     反查（dev_map）恒空；
   - 实例计数走 `readlink /proc/<pid>/fd/*` → `anon_inode:inotify`
     （:356-372），**对同 uid 进程有效**（正对照两次独立复现
     `Instances=1`）；跨 uid `/proc/<pid>/fd` 为 Permission denied 不可见；
   - 限额展示 `/proc/sys/fs/inotify/*` 完全可用
     （max_user_watches=524288 / max_user_instances=128 /
     max_queued_events=16384）；
   - 工具自带优雅降级守卫 `g_kernel_provides_watches_info |= !!watches`：
     无 watch 数据时自动隐藏 watch 统计列。
3. **测试层（假绿风险）**：若冒烟/单测断言"watch 计数 == 0"当作通过，
   会把结构性缺失伪装成数值正确——平台恢复 fdinfo 后测试仍错误通过、
   降级不被发现。

## 根因

OHOS 内核 procfs 不实例化 fdinfo 节点（平台能力缺失，内核 procfs 语义），
用户态无 patch 可解。归类：**非 musl 差异、非 SELinux、非代码 bug**。
机理链：节点缺失 → fopen 恒 NULL → 静默返 0 → watch 计数与路径反查恒空；
同 uid 实例计数因只依赖 `/proc/<pid>/fd` readlink 而幸存；限额走
`/proc/sys/fs/inotify/*` 完全不受影响。

## 方案

- **推荐 `fdinfo-capability-probe-degrade`**：运行期先对自身 pid 探测
  fdinfo 节点存在性（一次判定全平台），缺失时收窄输出到可用子集并显式
  标注（对齐 `g_kernel_provides_watches_info` 式守卫）；测试侧只断言可用
  子集（限额数值、退出码），不断言 fdinfo 派生计数。
- **回退 `same-uid-instance-count-only`**：以 readlink
  `/proc/<pid>/fd → anon_inode:inotify` 计实例（仅同 uid 可见，诚实标注
  覆盖边界），输出退化为限额 + 同 uid 实例总数。权衡：掩盖不了 watch 侧
  缺失，仅保住可用面，**非修复**。

## 验证（自包含脚本，设备实测通过）

```sh
# A. shell 三步探针（预期: A3=ABSENT；/proc/1/fdinfo Permission denied；限额可读）
cd "$(mktemp -d)"
ls /proc/self/fd >/dev/null && echo A1-fd-dir-present
r=$(readlink /proc/self/fd/0) && echo A2-readlink-ok:$r
[ -e /proc/self/fdinfo ] && echo A3-fdinfo-PRESENT || echo A3-fdinfo-ABSENT
ls /proc/1/fdinfo 2>&1 | head -1           # 预期: Permission denied（跨 uid）
cat /proc/sys/fs/inotify/max_user_watches  # 预期: 524288

# B. 内联 C 探针：持 inotify fd + watch + 普通 fd，fopen 自身 fdinfo → NULL
cat > probe.c <<'EOF'
#include <stdio.h>
#include <fcntl.h>
#include <sys/inotify.h>
int main(void) {
    int ifd = inotify_init();
    inotify_add_watch(ifd, "/tmp", IN_CREATE);
    int f = open("/etc/passwd", O_RDONLY);
    char p[64];
    snprintf(p, sizeof p, "/proc/self/fdinfo/%d", f);
    FILE *x = fopen(p, "r");
    printf("inotify_fd=%d open_fd=%d fdinfo_probe=%s\n",
           ifd, f, x ? "PRESENT" : "NULL(ABSENT)");
    return x == NULL;
}
EOF
/data/service/hnp/bin/clang probe.c -o probe && ./probe
# 预期: inotify_fd=3 open_fd=4 fdinfo_probe=NULL(ABSENT)
```

## 证据清单（三路独立复现）

1. **Scout fdinfo-probe**（同进程持 inotify fd）：
   `/storage/Users/currentUser/tmp/oh-device-porting-v2/inotify-info-0.0.4/fdinfo-probe.out`
   —— fopen `/proc/self/fdinfo/3` → FAILED (NULL)。
2. **Scout 正对照**（实例检出席工作、watch 侧无数据可给的降级形态）：
   同目录 `positive-control.out` —— fdinfo-probe 持 inotify fd 运行时，
   工具检出 1 instance。
3. **Auditor 独立正对照（第二独立复现）**：自编探针（clang 现场编译，
   非复用 Scout 探针）持 inotify fd + 1 个 watch，用 CI 产物真实工具
   （`.conan2/p/b/inoti97089ed920425/p/bin/inotify-info`）裸跑扫描：
   probe 进程被检出 **Instances=1**，输出仅限额+实例表，无任何 watch
   计数列/路径列。见 `reports/auditor/audit-report.md`（B-1 §2）。
4. **Curator 本机独立复核**：`reports/curator/curation-report.md` §0
   （ls /proc/self/fdinfo ENOENT、/proc/1 跨 uid EPERM、限额数值）。
5. **权威 CI**（佐证"构建/运行不受阻、缺失在运行期数据面"）：
   worktree/.ci_logs/conan_build_inotify-info_0.0.4.log —— run 退出码 0，
   test_package 冒烟 8/8（只断言限额数值与退出码）。

## 关联与去重

- **similar_to**:
  - `E031`（procfs 受限族）：机理区分——E031 是"有节点读不了"
    （SELinux Permission denied），本条是"节点根本不存在"（ENOENT，
    sudo 无解）。
  - `E285`（平台能力缺失 → 能力探测 + 诚实替代验证族）：同范式实例。
- **principles**: `P013`（平台限制必须降级而非绕过）。注册表与对齐目标：
  `knowledge/graph/principles.kv:151`（Curator 原报告"principles.yaml"
  为误记，经 Curator addendum 更正，以此为准）。
- **去重**：fdinfo/inotify/anon_inode 在 knowledge/graph + drafts +
  经验仓均 0 命中（Scout 与 Auditor 独立重跑 grep 双确认）。
- **配额**：本 run 主条位（1/2；原次条 B-2 经 Auditor CHALLENGED +
  Curator addendum 复核降级经验仓，B 收敛单条申报）。

## 来源

- run: inotify-info 0.0.4（oh-device-porting-v2，路径 A+B）
- 作者: sea_crab（不知对不队）
- 交付: 随 feat 分支交付；Issue 正文由 Delivery Worker 按
  templates/issue-knowledge-extension.md 生成
