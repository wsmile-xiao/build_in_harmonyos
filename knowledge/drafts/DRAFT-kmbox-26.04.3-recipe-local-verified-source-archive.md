# 不要把上游源码包随配方提交；conandata 使用官方单一 URL，source() 调用 get()

## 问题

PR #13448 曾把 `archives/k/kmbox/26.04.3/s/kmbox-26.04.3.tar.xz` 提交进配方，希望 checkout 后不再访问上游。GitCode 的 `pull/13448.diff` 不包含这块二进制补丁数据。CI 在 `checkout-pr` 执行 `git apply`，大约 4–6 秒失败，错误是 `missing binary patch data` / `binary patch does not apply`。机器人把失败标成网络问题或源码下载超时，和原始阶段不符：此时还没有 Conan，也没有请求 `download.kde.org`。

## 根因

Git 对二进制文件的 diff 需要完整的 binary patch。GitCode 导出的 PR diff 丢掉了这段数据，所以 worker 无法把该文件应用到干净的 main。把压缩包留在仓库里不能绕过外网，它会让检出本身失败。

正确的源码入口与已通过 CI 的同系列配方一致：`conandata.yml` 的 `sources` 直接写官方单一地址，`source()` 调用 `get(self, **self.conan_data["sources"], strip_root=True)`。Conan 按 `sha256` 校验下载结果。

## 最小解决与边界

1. 从 PR 中删除全部二进制文件，包括 `s/kmbox-26.04.3.tar.xz`。用普通提交删除，不改写历史。
2. `sources.url` 使用 `https://download.kde.org/stable/release-service/26.04.3/src/kmbox-26.04.3.tar.xz`。不要写镜像列表，不要写明文 `http://`。
3. SHA-256 必须与 KDE 官方索引和实际下载件一致：`ff39d6616f9d56a318cbb4e029bd42960f8a115579bdce7785e0af6f1fe5ee59`。索引见 `https://kde.org/info/releases-26.04.3/` 与 `kmbox-26.04.3.tar.xz.mirrorlist` 的 Known hashes。发布包 33,952 字节。
4. `export_sources()` 只导出补丁。不要再复制 tar 包。

适用前提：官方地址在构建机或真机上可访问。`download.kde.org` 在 HarmonyOS 真机上实测可下载，且哈希与官方索引一致，因此不为这次 checkout 失败改镜像。`worker-prep` / `git-clone` 的 SSH bridge `Connection refused` 发生在检出之前，同样不能靠换源修复。

这条修正只恢复 PR diff 可应用，并让 `source()` 回到官方包。它不改变 `kmime/26.04.3` 必须先发布到制品仓这一依赖关系。

## 验证

| 项目 | 结果 |
|---|---|
| 本机下载官方包 | HTTP 成功，33,952 字节 |
| 真机 `curl` 同一 URL | 33,952 字节，SHA-256 与下表相同 |
| KDE 发布页与 mirrorlist | SHA-256 `ff39d6616f9d56a318cbb4e029bd42960f8a115579bdce7785e0af6f1fe5ee59` |
| 配方内二进制 | 删除 `s/kmbox-26.04.3.tar.xz`，PR diff 不再携带无数据的二进制块 |
| 上游与消费者测试 | 2026-10-10 真机 `conan create` 退出码 0；上游 CTest `mbox-mboxtest` 1/1；消费者打印 `PASS: KMbox wrote and reread one MIME message`（11 项检查） |

## 七轴查重表

| 轴 | 本草稿定位 | 与相近知识的边界 |
|---|---|---|
| 触发条件 | PR diff 含二进制源码包，`git apply` 报 missing binary patch data | `DRAFT-ohos-conan-source-host-unreachable-byte-identical-mirror` 处理的是官方 host 不可达之后的镜像 |
| 阶段 | CI `checkout-pr`，以及其后的 `source()` | `DRAFT-9685-2-conan-sources-download-cache-seed` 是设备下载缓存种子，不改变 PR diff |
| 故障特征 | 4–6 秒失败，日志停在 checkout，未进入源码下载 | SSH bridge 在 `worker-prep` 即拒绝，连 checkout 都没开始 |
| 根因 | GitCode pull diff 不含二进制补丁数据 | 源码站点超时是另一类失败，发生在 Conan `get()` |
| 最小修复 | 删除二进制，官方单一 URL + `get(strip_root=True)` | 重新提交 tar 包会再次让 diff 不可应用 |
| 验证证据 | 官方索引、本机与真机 SHA-256、`conan create` | 镜像站哈希对拍不能代替删除二进制 |
| 适用边界 | 小体积官方发布包，且官方 HTTPS 地址可达 | 官方地址确实不可达时再按仓库规则评估备选，不为本例的 checkout 失败加镜像 |

### 查重检索记录

先前同一草稿文件名主张“把经校验的 tar.xz 随配方提交”。该主张与本次 CI 原始日志矛盾，已撤回。本草稿只保留文件名，内容改为：二进制源码包不能进入 PR，源码地址使用 KDE 官方单一 URL。

## 适用边界

- 适用：GitCode CI 用 `git apply` 应用 PR diff，且 diff 中出现 `Binary files` 或 `missing binary patch data`。
- 不适用：失败停在 `worker-prep`/`git-clone` 的 SSH bridge；制品仓查不到已声明的依赖；官方源站在目标机上确实不可达。
- 文件名仍带 `source-archive`，是为了与已关联的知识草稿路径保持对应。正文描述的是删除该归档，不是继续提交它。
