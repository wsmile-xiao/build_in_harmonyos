# 上游源站真机不可达：sha256 验证的官方 tarball + CI 预下载 file:// 机制

- **软件**: libdisasm 0.23（泛化到 SourceForge 等源站托管的配方）
- **阶段**: source（conan create）
- **severity**: 2
- **状态**: DRAFT

## 现象

设备上 `curl -sIL https://downloads.sourceforge.net/...` 返回 HTTP 000；`conan create`
在 source 阶段下载失败（conan `get()` 无多源 fallback）。

## 根因

真机网络策略下部分上游源站不可达。仓库 CI（`build_and_test.sh`）的镜像列表覆盖
github/gnu/gnome/kernel.org 等，但对 SourceForge 明确注释"国内有镜像但 URL 结构不同，
保留原始 URL"——即 CI 对 SourceForge 也没有可用镜像。同时 R39 禁止把 conandata.yml
的官方 URL 换成不明镜像。

## 修复

复用 CI 已有的"预下载 + file:// 改写"机制在真机侧落地（不违反 R39，提交的
conandata.yml 始终是官方 URL）：

1. 开发机从官方 URL 下载 tarball 并记录 sha256（与 conandata.yml 同值）；
2. tarball 传到真机 job 目录，设备端 `sha256sum` 二次校验一致；
3. 备份 job 副本 conandata.yml，将 url 改写为 `file://<abs path>`（与 CI
   `predl_cache` 同构）；
4. `conan create`/`test`；结束后还原官方 URL（仓库内文件从不改动）。

等价性证据链：同文件名 + 同 sha256 = 镜像等价；PR 记录主源与校验值。

## 证据

libdisasm 0.23（10.62.178.77）：SourceForge HTTP 000 不可达；开发机同 URL 下载
sha256 `de3e578a...5433da` 与 conandata.yml 一致，传设备复验一致；job 副本
file:// 改写后 conan create 成功解包构建；还原后仓库 conandata.yml 保持官方 URL。
