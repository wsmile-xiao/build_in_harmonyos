# DRAFT-minlzma-1.1.5-github-tag-v-prefix-404：GitHub tag v 前缀导致的 conan source 404

> Contributor: pc4-37 | Status: Draft | Updated: 2026-09-23
> Source: minlzma 1.1.5 适配（Path B 知识库扩展）；触发场景：`conan-verify` G2 conan create source() 阶段
> 对应：`knowledge/drafts/DRAFT-minlzma-1.1.5-github-tag-v-prefix-404.kv`

## 现象

`ohc-run.py conan-verify <lib> <ver>` 的 G2（conan create 干净构建）失败，日志：

```text
ERROR: minlzma/1.1.5@ohpcd/stable: Error in source() method, line 42
    get(self, **self.conan_data["sources"], strip_root=True)
NotFoundException: Not found: https://ghfast.top/https://github.com/ionescu007/minlzma/archive/refs/tags/1.1.5.tar.gz
```

镜像（ghfast.top）返回 404。GitHub API tags 列表显示实际 tag 名为 `v1.1.5`（带 v 前缀）。

## 根因

conan-init 模板按版本号拼接 URL：`refs/tags/1.1.5.tar.gz`；而 ionescu007/minlzma
的官方 tag 是 `v1.1.5`，无 v 的 URL 直接 404。这是 **tag 命名** 问题，与下载通道、
网络、镜像无关——镜像只是把 404 透传回来。

**陷阱**：不要被"镜像 404"误导去换镜像/加代理；先用 GitHub API 确认 tag 真实名称。

## 修复（已验证）

```bash
# 1) 确认 tag 名（GitHub API）
curl -sS https://api.github.com/repos/ionescu007/minlzma/tags   # → "v1.1.5"
# 2) conandata.yml sources.url 补 v 前缀
#    https://github.com/ionescu007/minlzma/archive/refs/tags/v1.1.5.tar.gz
# 3) 重跑 conan-verify → G2 PASS（镜像 200 / 73272 字节下载成功）
```

验证证据：URL 修正后 `curl -sSI …/refs/tags/v1.1.5.tar.gz` 返回 `200`，
`conan create` source() 拉取成功、SHA-256=49811637b6ad… 校验通过，G1-G5 全 PASS。

## 适用边界

- 适用：上游 GitHub tag 带 v 前缀（vX.Y.Z）的仓库；改 URL 补 v。
- 反例：上游 tag 不带 v 的仓库（refs/tags/1.0.0），此时补 v 反而 404。
- 判断标准永远以 GitHub API tags 列表的 `name` 字段为准，不猜测。

## 验证结果

| 项目 | 结果 |
|---|---|
| GitHub API tag 名 | v1.1.5 ✅ |
| 修正后镜像下载 | 200 / 73272 字节 ✅ |
| conan-verify G2 | PASS（G1-G5 全绿）✅ |