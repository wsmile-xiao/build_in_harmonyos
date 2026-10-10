# Draft: libfuse 3.16.1 on OHOS — W3 预下载的「还原」把镜像 URL 写回 conandata.yml（日志说还原、文件被污染）

> Draft: `DRAFT-LIBFUSE-3161-W3-PREDL-MIRROR-RESTORE-POLLUTES-CONANDATA`
> Stem: `libfuse-3.16.1-w3-predl-mirror-restore-pollutes-conandata` — pairs with the same-stem `.kv`

## 现象

`finish` 的 Step 5（W3 本地 CI 模拟）**全绿通过**，日志末段也打印：

```
[step] Pre-download: conandata.yml 已还原为官方 URL
```

但收工后 `git diff` 里 `conandata.yml` 变成了：

```diff
 sources:
-  url: "https://github.com/libfuse/libfuse/releases/download/fuse-3.16.1/fuse-3.16.1.tar.gz"
+  url:
+    - "https://gh-proxy.com/https://github.com/libfuse/libfuse/releases/download/fuse-3.16.1/fuse-3.16.1.tar.gz"
+    - "https://github.com/libfuse/libfuse/releases/download/fuse-3.16.1/fuse-3.16.1.tar.gz"
```

也就是说：**没有任何人手写过镜像 URL，配方文件却被写入了镜像前置源**，
而且提示信息声称它已还原成官方 URL。

后果是刚性的：`gh-proxy.com` 在 PF7/R39 的镜像域名黑名单里（语料实证 14 域之一），
一旦被提交即命中硬闸；本包在 W4 独立审计中被判 **P1 / verdict=fail**。

## 根因（`ci/conan/build_and_test.sh` 的两个步骤顺序颠倒）

| 顺序 | 位置 | 动作 |
|------|------|------|
| 1 | 镜像回退改写（`replace_url` / `get_mirrors`，约 1040–1163 行） | 把 `url:` 单值行就地改写成 `url:` + `- <镜像>` + `- <官方>` **列表**，写回磁盘 |
| 2 | Pre-download 备份（约 1179 行） | `cp "$CONANDATA" "$PREDL_BACKUP"` ——**在步骤 1 之后**才取备份 |
| 3 | 预下载改写 | 把 URL 全部换成 `file://<predl_cache 路径>` |
| 4 | `trap _restore_conandata EXIT` | `cp "$PREDL_BACKUP" "$CONANDATA"` ——还原的是**步骤 2 的镜像版**，不是原作者写的官方单值版 |

关键点在步骤 2：备份取的是**已被改写**的内容，所以 EXIT 陷阱里的
「还原为官方 URL」在语义上是错的——它还原的是「镜像回退列表」。
原始单值 URL 在步骤 1 写回磁盘那一刻就已经永久丢失（文件内不再有任何副本）。

同一日志还有两条可交叉验证的旁证：

- `[done] Pre-downloaded 2 files` ——镜像改写把 URL 变成 2 条，预下载就真的下了 2 份；
  （正常单源配方这里应为 1）
- `Sources correctly downloaded from file:///...predl_cache/032caa7b_fuse-3.16.1.tar.gz`
  ——两份都下成功，构建不受影响，所以**失败是静默的**：CI 全绿、文件被污染。

## 与既有知识的关系

- `DRAFT-8543-conandata-comment-url-predl-rewrite` 与
  `DRAFT-8960-raqm-0.11.0-conandata-comment-url-predl-pollution` 记录的是
  predl **URL 提取**缺陷（注释里的裸 URL 被当源码 URL 抓走），后果是构建失败
  （`NotADirectoryError` / 下到 HTML 页）。
- 本草稿记录的是**备份/还原**缺陷，后果不是构建失败而是**静默的产物污染**
  （提交里出现镜像源 → PF7/R39 硬闸 + W4 审计 P1）。
- 三者同属「predl 步骤会改写你磁盘上的 conandata.yml」这一族，但根因与症状完全不同：
  那两个是「读错 URL」，本条是「写回错的 URL」。

## 可复用处置

1. **每次 `finish` / `conan-verify` / W3 之后，都要 `git diff` 检查
   `conandata.yml` 与 `manifest.yaml`**，并把这两个文件恢复成「只含官方源」的形态
   再提交（本包实测 `conan-verify` 的还原是正常的，**只有 W3 的
   `build_and_test.sh` 会留下污染**）。
2. 顺手清掉 `conandata.yml.ghfast-bak` / `conandata.yml.orig` 等残留
   （`conan-verify` 的 ghfast.top 注入也会留备份文件，见 JC3 的
   `\.(bak|orig|rej|ghfast-bak)$` 拦截项）。
3. 提交前跑 `git diff -- archives/<x>/<pkg>/` **逐行读一遍**，不要只看
   「构建是否通过」——本例正是「全绿 + 被污染」。
4. 目前没有可用的自动修复入口（既不能改 CI 脚本，也不该让配方自带镜像），
   所以处置只能是**提交前人工核对 + 还原**。若将来能改 CI，正确做法是把
   `PREDL_BACKUP=...; cp` 挪到镜像改写**之前**，并且改写前先确认
   `url:` 已是单值形态。

## 证据

- `archives/l/libfuse/3.16.1/reports/w3-local-ci.log:96,103,413`
- `archives/l/libfuse/3.16.1/reports/audit-result.json`（P1 / R39）
- `ci/conan/build_and_test.sh` 约 1163–1181 行（改写 → 取备份的顺序）
