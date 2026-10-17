# DRAFT-ohos-job-hmdfs-git-shim-exec-denied-use-hnp-bin：真机 conan job 的 git "permission denied"（HMDFS shim 无执行权）

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-ohos-job-hmdfs-git-shim-exec-denied-use-hnp-bin.kv`

---

**匹配关键词**：permission denied: git, HMDFS, ohpc-ci-shadow, build_and_test.sh:164, G0e, 隔离 job, env.sh

## 错误签名（error_signature）

```text
ci/conan/build_and_test.sh:<行号>: permission denied: git
```

## 错误摘录（error_excerpt）

```text
ci/conan/build_and_test.sh:164: permission denied: git
```
（164 行是 G0e 根目录白名单检查的 `git ls-files --full-name`）

## 根因（root_cause）

隔离 job（ohos-prepare-isolated-conan-job.sh）生成的 env.sh 把
`$HOME/ohpc-ci-shadow/python-user/bin` 放在 PATH 首位，该目录里有一个 67 字节的
git shim（`exec .../git2 ...`），但整个 `/storage`（HMDFS）分区**不允许执行**
（避坑清单"HMDFS 无执行位"），zsh 报 `permission denied: git` 而非
`command not found`——git 文件"存在"但 exec 被 FUSE 层拦截，且它遮蔽了 PATH
后面的真 git。2026-09-27 当天 maxflow 等其他 job 的多次 run 同样死于该点。

## 推荐方案（rec_approach）

只改**本 job 的 env.sh**（job 本地配置，非仓库基础设施）：

```sh
export PATH=/data/service/hnp/bin:$PATH
```

`/data/service/hnp/bin` 在非 HMDFS 分区，自带完整 git 2.45.x（git/git-ls-files
等全都在），可执行。改完 `command -v git` 应指向 `/data/service/hnp/bin/git`。
同时确认 repo-source 拷贝**带 .git**（`git ls-files` 需要工作区元数据），否则
G0e 无法执行。识别信号：真机 run 的 stderr 出现
`build_and_test.sh:<行>: permission denied: git` → 先查 PATH 首位的 HMDFS shim。

## 与既有条目的关系（查重说明）

- **E540 / zlib-shadow-ci-hnp-tool-path**（"Makefile 需要 /data/service/hnp/bin
  里的 as/ld"）：解法方向相同（hnp/bin 进 PATH），但错误签名不同——E540 是
  `cannot execute 'as'`（工具缺失），本条是 `permission denied: git`
  （git 文件存在、被 HMDFS 拦 exec 且 shim 遮蔽真身）。互补不重复，本条补
  "文件存在却 permission denied" 的判别与 shim 遮蔽机制。
- 图谱查重：`permission denied: git` 0 命中（2026-09-27）。

---

*来源：libshrinkwrap 1.2.0 真机 shadow CI r1（2026-09-27，run
codex-1.2.0-libshrinkwrap-…-152915 / -153304）；修复后 r3 全绿。*
