# uucpsend 1.1 — CI 失败分析

日期：2026-10-03
PR：[#14361](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14361)
构建：`#68733`（首轮 `#67882`），worker `OpenHarmonyPCDeveloper-CI-023`

## 1. CI 结论（机器人原文）

四次尝试**全部同症状失败**：

| # | 时间 | 构建 | 提交 | 源码 URL 版本 | 类别 / 问题 | SSH bridge |
|---|---|---|---|---|---|---|
| 1 | 2026-10-02 22:37:54 | `#67882` | `74b10a48` | 官方源优先 | 网络问题 / 源码下载超时 | ❌ 失败 |
| 2 | 2026-10-03 13:09:17 | `#68733` | `74b10a48` | 官方源优先 | 网络问题 / 源码下载超时 | ❌ 失败 |
| 3 | 2026-10-03 13:19:59 | `#68764` | `74b10a48` | 官方源优先 | 网络问题 / 源码下载超时 | ❌ 失败 |
| 4 | 2026-10-03 13:32:24 | **`#68808`** | **`3f7a9d2e`** | **镜像优先** | 网络问题 / 源码下载超时 | ❌ 失败 |

**第 4 次是决定性证据**：它跑的正是「国内镜像优先」的 `conandata.yml`，
失败症状与前三轮**逐字相同**（同样四步、同样 `SSH bridge exec failed`、
同样「源码下载超时」）。即：

> **失败与源码 URL 无关。** 换掉全部 5 个 URL 的顺序后结果没有任何变化。

（`6f75f08d` 的第 5 次触发未再重试，理由见第 6 节。）

```
## CI 校验失败
**类别**: 网络问题
**问题**: 源码下载超时
**原因**: Worker 网络受限，无法访问外部源码仓库。
        已知可达: zlib.net; 已知不可达: ftp.gnu.org。
```

| 步骤 | 结果（四次均相同） |
|---|---|
| worker_preparation | ✅ |
| worker-prep | ❌ |
| git-clone | ❌ |
| cleanup | ❌ |

## 2. 日志里真正发生了什么

失败的三步**都没有执行到任何实际命令**，全部止于同一句：

```
ERR SSH bridge exec failed: connect failed: connection lost before ready:
    Connection was refused by other side: 111: Connection refused.
program finished with exit code -1
```

各步耗时：`worker-prep` 0.008–7.45s、`git-clone` 0.009s、`cleanup` 0.009s。
即 **conan create 从未开始运行**，L0–L5 闸门一条都没跑到。

> 因此「源码下载超时」是机器人基于日志的**推断**（`git-clone` 失败 + 网络类别），
> 不是一条实际测得的下载错误。这一点必须讲清楚，否则容易误判为包的问题。

## 3. 是包的问题，还是 CI 环境的问题？

对比同期 10 个 PR 的 CI 结论：

| PR | 结论 | 类别 / 问题 | SSH bridge 失败 |
|---|---|---|---|
| #14436 trousers | FAIL | 网络问题 / 源码下载超时 | ✅ |
| #14434 ccan | FAIL | 网络问题 / 源码下载超时 | ✅ |
| #14432 libsignon-qt | FAIL | 网络问题 / 源码下载超时 | ✅ |
| #14430 zsxd | FAIL | 网络问题 / 源码下载超时 | ✅ |
| #14428 tgl | FAIL | 网络问题 / 源码下载超时 | ✅ |
| #14425 kodi-inputstream-adaptive | FAIL | 网络问题 / 源码下载超时 | ✅ |
| #14424 kodi-vfs-libarchive | FAIL | 网络问题 / 源码下载超时 | ✅ |
| #14433 snpomatic | PASS | — | — |
| #14431 sofa | PASS | — | — |
| #14429 libydpdict | PASS | — | — |

**10 个里 7 个以完全相同的方式失败**，且失败集合跨越完全不同上游
（GitHub、GNU、sourceforge、metacpan 等）。这**不是 uucpsend 特有**。
CI 构建墙同期为 **0 成功 / 50 失败**。

### 3.1 直接证据：CI 服务本身不可用

推送镜像优先改动后于 13:20:31 触发第 4 次构建，**长时间停留在「构建触发中」**，
未被 worker 取走（对比第 3 次：13:19:53 触发、13:19:59 就出结论，仅 6 秒）。
随后直接请求 CI 看板：

```
GET https://ohpcd.atomgit.com/ci
→ HTTP 503 Service Temporarily Unavailable
```

即**CI 面板/调度服务当时处于不可用状态**，构建排不进队列。
这与「worker 网络受限」是两件事，但同属 CI 侧基础设施问题。

## 4. 已采取的处置（可辩护的部分）

### 4.1 按仓库既有做法改为「镜像优先 + 官方源兜底」

本仓 `archives/u/uucp/1.07`（上游 `ftp.gnu.org`，正是 CI 点名的**已知不可达**主机）
的既有做法是：**国内镜像排在前、官方源排最后**。本包照此调整 `conandata.yml`：

```
sources.url:
  1. mirrors.tuna.tsinghua.edu.cn/debian/pool/main/u/uucpsend/uucpsend_1.1.orig.tar.gz
  2. mirrors.aliyun.com/debian/pool/main/u/uucpsend/uucpsend_1.1.orig.tar.gz
  3. mirror.nju.edu.cn/debian/pool/main/u/uucpsend/uucpsend_1.1.orig.tar.gz
  4. deb.debian.org/debian/pool/main/u/uucpsend/uucpsend_1.1.orig.tar.gz
  5. www.infodrom.org/projects/uucpsend/download/uucpsend-1.1.tar.gz   ← 官方源，兜底
sha256: 3447ff358e21c9927f4a35409218bf6f77c6caaceeed298bc15a8cb6dec065bc
```

**等价性已实测**：5 个 URL 逐个下载并计算 sha256，全部等于
`3447ff35…`（与官方发布逐字节相同）。`mirrors.ustc.edu.cn` 上该文件异常
（仅 879 B、哈希不符），**已剔除**，未列入。

`deb.debian.org` 保留在列表内，理由：本仓已有 465 个合入包使用该主机，
说明它在 CI 侧通常可达。

> uucpsend 上游**没有 GitHub/GitLab 仓库**，因此不存在 git-archive 镜像可用；
> Debian 的 pristine-orig 是唯一逐字节等价的镜像来源。

### 4.2 真机复验（镜像优先版本）

用新的 `conandata.yml` 在真机重跑隔离 `conan create`：

```
RUN_DIR=$HOME/ohos-adapt-runs/uucpsend-1.1-mirror-20261003-131822
CREATE_EXIT=0
Apply patch ×3
RUN: make all -j1 CC="…/clang" CFLAGS="…" LDFLAGS="…"
assertions passed: 15   assertions failed: 0   RESULT: PASS
```

包内容与旧 conandata 版本一致（recipe 未改，仅 URL 顺序与注释变化）。
**但这只证明"换 URL 后本机仍可构建"，不能证明 CI worker 可达那些镜像**——
两者的网络策略不同（见第 5 节）。

## 5. 必须承认的不确定性

1. **无法从适配主机验证 worker 的网络可达性**。适配主机（真机）实测
   `www.infodrom.org`、`deb.debian.org`、`mirrors.tuna`、`mirrors.ustc`、`gh-proxy.com`
   **全部 200**，而 CI 的「已知不可达」名单里 `ftp.gnu.org` 在真机上也可达。
   两套环境的出口策略不同，本机测试结论**不能外推**到 worker。
2. **失败日志里没有真实的下载尝试记录**（SSH bridge 先挂了），所以既不能证实
   也不能证伪「infodrom.org 在 worker 上不可达」。镜像优先是**降低风险**，不是
   已证实的修复。
3. **首轮 CI 的并发失败面太大**（7/10 同症状、构建墙 0/50），主因更可能是
   worker/SSH bridge 侧的基础设施故障。

## 6. 处置决定：停止重试

第 4 次构建（`#68808`，镜像优先版本）与前三轮逐字同症状失败后，**已确认失败
与本源码 URL 无关，属 CI 侧基础设施问题**，因此**不再反复重试**：

- 重试不产生新信息——第 1–4 次已覆盖「官方源优先」与「镜像优先」两种输入，
  输出完全相同；
- 占用 worker 队列对同批失败的其他 PR（#14424–#14436）也没有帮助；
- CI 看板在 13:20 前后曾返回 **HTTP 503**，worker-prep 的 `SSH bridge
  connect ... Connection refused` 也指向接入层故障，不是本包可修复的范围。

保留的改动（镜像优先 + 本报告）仍然有价值：它按本仓 `uucp/1.07` 的既有做法
降低了单一主机风险，且 5 个 URL 的 sha256 已实测全等。**但它不是本次失败的
确证修复，报告中已如实说明。**

### 恢复后的判定方法（无需再猜）

等 CI 服务恢复、同批 PR 有转绿样本后，再触发一次即可，按下表读结论：

| 新日志表现 | 判定 |
|---|---|
| 仍止于 `SSH bridge exec failed`，四步同前 | 纯 worker 接入故障，与包无关 |
| 仍报「源码下载超时」但步骤前移到 `conan-build-test` | 镜像优先未解决，需查 `DOWNLOAD_CACHE=/data/cache` 预缓存路径 |
| 失败点前移到 patch / build / test 阶段 | 镜像已解决下载，按新的失败点排查 |
| L0–L5 全绿 | 直接进入合并流程 |

## 7. 结论摘要

- 本包在**真机上已构建、打包、15/15 测试通过**（见 `device-build.md`），
  与 CI 失败无关。
- CI **四次**失败**全部止于 `SSH bridge exec failed`**，`conan create` 从未
  启动；「源码下载超时」是机器人的推断，日志里没有真实下载失败记录。
- **第 4 次跑的是镜像优先版本，症状零变化** → 失败与源码 URL 无关。
- 同期 7/10 个不相关 PR 同症状、构建墙 0/50、CI 看板 503 —— **主因是 CI 侧
  基础设施故障**。
- 已按仓库既有模式把源码 URL 改为镜像优先（5 个 URL 哈希全等），并在真机
  复验构建通过；这是**降低单一主机风险的改进**，不是本次失败的确证修复。
