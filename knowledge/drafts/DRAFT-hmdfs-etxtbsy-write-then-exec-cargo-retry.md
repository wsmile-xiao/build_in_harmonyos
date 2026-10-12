# DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry — HMDFS 写回越过 close() 持有写句柄，cargo 写后即 exec 偶发 ETXTBSY，须带锚定文本的一次重试

> Contributor: Curator (zram-1.2.1 run) / Status: **DRAFT** / Updated: 2026-09-30 / Severity: 2 (medium，偶发但阻塞构建)
> Prospect ID: `DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry`（正式编号由主编 `graph promote` 分配）
> 一句规则：**在 HMDFS 工作区跑 cargo，"写完 build-script 即 exec"的紧邻序列会偶发 `Text file busy (os error 26)` 使整轮构建失败；cargo 构建/测试命令必须包一层锚定错误文本的一次重试（真实编译错误第二轮照抛），并发收敛（-j1）仅作退路。**

## 查重证据

检查范围与命令（2026-09-30，真机，run worktree `knowledge/` 与经验仓 `/storage/Users/currentUser/ophs_ci_review`）：

| 检索 | 范围 | 命中 | 结论 |
|---|---|---|---|
| `grep -rEiln 'etxtbsy\|text file busy\|os error 26'` | graph/ doc/ drafts/ | 0 | 问题类零覆盖 |
| `grep -rli busy`（复核误命中） | graph/ doc/ drafts/ operations/ | E534（BusyBox 兼容层）、E464（busy loop）、若干 bash 脚本类草稿 | 全部为词形误命中 |
| `grep -rli 'text file busy'` | 经验仓全仓 | 0 | 经验仓亦无同类条目 |

相近家族（HMDFS 语义差异族，作 `similar_to`）：`P-HMDFS-001`（HMDFS 限制必须用替代方案）、`P-FS-001`（HMDFS 无硬链接/FIFO，**点名 cargo 内部硬链接在 HMDFS 上 EPERM**——与本条同属"cargo 在 HMDFS 上的文件操作语义"问题面）、`DRAFT-libfreenect-0.5.3-hmdfs-shared-lib-versioned-symlink`、`DRAFT-coordgenlibs-3.0.2-hmdfs-inode-sparse-worktree`、`DRAFT-dmc_unrar-1.8.0-hmdfs-inode-enospc-sparse-checkout`。家族内既有条目覆盖软硬链接、inode/sparse、ENOSPC，**exec 语义（ETXTBSY）无任何条目覆盖**。

**新增价值**：确立 HMDFS 第 5 个语义切面（写回句柄生命周期 × exec），并给出可直接抄的"文本锚定一次重试"工程守卫。

## 症状（真实日志，zram-1.2.1 run 真机预检第一轮）

```console
Caused by:
  could not execute process `/storage/Users/currentUser/zram-work/preflight/src/target/release/build/libc-33db606bffb79ea2/build-script-build` (never executed)

Caused by:
  Text file busy (os error 26)
warning: build failed, waiting for other jobs to finish...
make: *** [Makefile:32: program] Error 101
make: Leaving directory '/storage/Users/currentUser/zram-work/preflight/src'
+ echo PREFLIGHT_BUILD_FAIL
PREFLIGHT_BUILD_FAIL
+ exit 1
```

证据：设备 `~/zram-work/logs/preflight.log:119-129`。同命令重跑即过；权威 CI run1（带重试守卫）PASS。

## 根因机理链与证据状态（诚实分级）

| 环节 | 状态 | 依据 |
|---|---|---|
| cargo 对 build-script 走"写完即 exec" | 工具事实（cargo 既有行为，带 build.rs 的 crate 必经） | 日志失败对象即 `build/libc-*/build-script-build` |
| exec 撞未释放写句柄 → ETXTBSY(26) | **确定性语义**，探针第 1 段可复现 | POSIX 语义 + 下述探针 |
| HMDFS 写回在 close() 后仍短暂持有句柄 | **推断（平台特异环节）**，由"close 之后仍偶发 26"的生产命中 + 探针第 2 段（概率放大）佐证；原生 ext4 无此现象 | preflight.log 命中记录 + 探针 |
| 偶发性 | 实测（预检多轮仅第一轮命中一次） | preflight.log vs preflight2.log/unittest.log |

不夸大：第 3 行是当前最强解释（与 docker/overlayfs 上已知的 ETXTBSY 竞态同构），但**未能按需复现**；条目价值不依赖它成立——症状特征（os error 26 + never executed + 重跑即过）与守卫（文本锚定一次重试）独立成立。

## 验证（自包含探针）

```sh
# 设备上现场编译（clang 在 PATH 或 /data/service/hnp/bin/clang）
cat > $HOME/etxtbsy_probe.c <<'EOF'
#define _GNU_SOURCE
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/wait.h>

static int try_exec(const char *path) {
    execv(path, (char *[]){(char *)path, NULL});
    fprintf(stderr, "execv: %s (errno=%d)\n", strerror(errno), errno);
    return errno;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s <path> <hold|close|loop>\n", argv[0]); return 2; }
    const char *path = argv[1];
    int fd = open(path, O_CREAT | O_WRONLY | O_TRUNC, 0755);
    if (fd < 0) { perror("open"); return 1; }
    write(fd, "#!/system/bin/sh\necho ok\n", 25);
    fchmod(fd, 0755);
    if (!strcmp(argv[2], "hold")) return try_exec(path);   /* 期望: execv: Text file busy (errno=26)，返回 26 */
    close(fd);
    if (!strcmp(argv[2], "close")) return try_exec(path);  /* 期望: 执行成功（execv 不返回，shell 打印 ok） */
    int hits = 0;                                          /* loop: close 后紧循环 exec，放大写回存活窗口 */
    for (int i = 0; i < 200; i++) {
        pid_t p = fork();
        if (p == 0) _exit(try_exec(path));
        int st; waitpid(p, &st, 0);
        if (WEXITSTATUS(st) == 26) hits++;
        fd = open(path, O_WRONLY | O_TRUNC);
        write(fd, "#!/system/bin/sh\necho ok\n", 25);
        close(fd);
    }
    printf("ETXTBSY hits after close: %d/200\n", hits);
    return hits > 0 ? 26 : 0;
}
EOF
clang -O2 -o $HOME/etxtbsy_probe $HOME/etxtbsy_probe.c   # 或 /data/service/hnp/bin/clang
$HOME/etxtbsy_probe $HOME/etxtbsy_probe.sh hold;  echo "hold rc=$?"    # 期望 rc=26
$HOME/etxtbsy_probe $HOME/etxtbsy_probe.sh close; echo "close rc=$?"   # 期望 rc=0（打印 ok）
$HOME/etxtbsy_probe $HOME/etxtbsy_probe.sh loop;  echo "loop rc=$?"    # >0 命中即证实写回存活；0 不构成反证
```

（探针路径避开 "tmp" 命名——设备工作目录命名纪律。）

## 方案空间

**rec（主方案）：文本锚定的一次重试**

- 定向形态（推荐，test_package 实装）：`proc.returncode != 0 and "Text file busy" in output` 才重试一次——真实编译错误第二轮照样失败并抛出，不掩盖任何真问题。
- catch-all 形态（本 run 主 conanfile `build()` 的 `_run_with_retry`）：失败即重试一次。收敛性相同，权衡：对非 ETXTBSY 失败多做一轮无害工作；flake 频率被部分吸收，观察成本略升。两种形态都比不设防好——预检第一轮的失败若发生在无人值守 CI 即红。

**fallback（退路）**：`cargo build -j1` / conan `build.jobs=1` 收敛并发，从根上缩小竞态窗口。确定性更高但显著拖慢构建，仅作重试失效时的退路。

**forbid（反模式）**：
1. 固定 sleep / 无界重试循环——时序膏药 + 掩盖 flake 频率。
2. 往上游源码打 sleep/retry 补丁——这是构建宿主文件系统语义问题，不是上游缺陷（态度审计第 2 条）。
3. 把 os error 26 误归类为编译错误去"修代码/换依赖"——方向性误诊。

## 证据路径（zram-1.2.1 run）

- 命中日志：设备 `~/zram-work/logs/preflight.log:119-129`
- 守卫实装：`archives/z/zram/1.2.1/conanfile.py`（`_run_with_retry`）、`archives/z/zram/1.2.1/test_package/conanfile.py`（`_run_upstream_tests` 内 `"Text file busy" in output` 定向重试）
- 修复后门禁：`runs/zram-1.2.1/logs_ci_run1.log`（run1 PASS）

## 原则挂钩与申报域

- principles：**P-HMDFS-001**（HMDFS 限制必须用替代方案/守卫应对）、**P-FS-001**（同族：cargo 在 HMDFS 上的文件操作语义——硬链接 EPERM 之旁例）。
- 申报域（八分类）：**构建系统语义**（主）+ **工具链行为**（辅）。形态选择：机理叙事 + 方案空间，走 kv 条目形态。
- 配额使用：zram-1.2.1 run **次条**（主条 `DRAFT-rust-preohos-musl-cfg-gate-ohos-misfire`），共 2/2。
