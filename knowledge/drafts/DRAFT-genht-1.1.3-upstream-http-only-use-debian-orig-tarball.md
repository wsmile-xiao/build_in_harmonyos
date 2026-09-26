# 上游只有明文 http 时，用 Debian pool 的原始 `.orig` tarball 满足 https 源要求

**条目**: `DRAFT-genht-1.1.3-upstream-http-only-use-debian-orig-tarball`
**来源**: genht 1.1.3 适配（repo.hu 发布页无 TLS）
**状态**: DRAFT

## 现象

| 约束 | 内容 |
|------|------|
| 上游 | `http://www.repo.hu/projects/genht/releases/genht-1.1.3.tar.bz2`（:443 无监听，https 连不上） |
| 仓库 | R39/PF7：源 URL 必须 https 官方源；明文 http、镜像域名、`file://`、Debian 重打包均被拦 |

## 处理

1. 取上游 http 包哈希，并与第三方独立记录（FreeBSD ports `distinfo`）交叉验证。
2. 从 Debian pool 取**未改动**的 `.orig.tar.bz2`（非 `+dfsg` 重打包）。
3. 三方 sha256 与体积一致 → 认定为上游原始 tarball，URL 满足 https。
4. 三行哈希写进 `notes.md` 留证。

## 实证（genht 1.1.3）

| 来源 | SHA256 | 体积 |
|------|--------|------|
| 上游 repo.hu（http） | `9861a35c30b5d0023c5f50fa8bb44c3e1df15c232de155888faa492f71f3b1cc` | 10936 |
| FreeBSD ports devel/genht distinfo | 同上 | 10936 |
| Debian pool `.orig.tar.bz2` | 同上 | 10936 |

## 要点

- **不要**为了绕 http 限制改回 http 或写镜像前缀（PF7 黑名单 14 个域）。
- `.orig.tar.*` 与 `+dfsg` 有本质区别：后者是 Debian 下游删除/替换文件后的重打包。
- 若 PF7 仍按 `deb.debian.org` 域名判为「Debian 下游重打包源」（main 上已有 800+ 包使用该域）：
  按既有惯例以 `--no-preflight` 提交，并在 PR 正文写明证据链。
