# DRAFT — conandata.yml 注释里的裸 URL 会被 CI 预下载步骤改写

> Status: DRAFT (contributor 8543) | Source: looktxt/1.4.1 adaptation, task #8543
> Environment: HarmonyOS PC aarch64, Conan 2.29.1 (OHOS), `ci/conan/build_and_test.sh` 本地 CI 模拟

## 1. 症状

同一个配方，两条验证路径给出相反结论：

| 路径 | 结果 |
|---|---|
| `ohc-run.py conan-verify looktxt 1.4.1` | 通过：G1/G2/G3 显示 PASS（G0 为知识图谱预查询，G4/L2/L4/L5 同轮执行），末行「配方验证通过」退出码 0，源码从官方 HTTPS 直下 |
| `ohc-run.py finish` 的 W3 本地 CI 模拟 / `ci/conan/build_and_test.sh` | L1 `conan create` 失败 |

失败信息指向一个不存在的本地路径：

```
NotADirectoryError: [Errno 20] Not a directory:
  '.build-cache/predl_cache/acb8fbe0_looktxt/-/archive/v1.4.1/looktxt-v1.4.1.tar.gz'
```

`acb8fbe0_looktxt` 是缓存文件名（预下载按 URL 哈希命名），后面却还跟着 GitLab 的路径残段——正常改写结果应当恰好停在文件名处。

## 2. 根因

`build_and_test.sh` 的预下载步骤为了在受限设备上避免真下载，做了两件事：

1. 用正则把 `conandata.yml` 里出现的 **所有** http(s) URL 抓出来（不区分注释与字段）；
2. 对每个抓到的 URL 执行一次 `content.replace(url, 'file://<下载好的缓存文件>')`，
   把改写后的临时副本交给 `conan create`。

当注释里的 URL 是 `sources.url` 的**严格前缀**时——本案写的是项目主页
`…/looktxt`，而真实地址是 `…/looktxt/-/archive/v1.4.1/…tar.gz`——替换顺序决定了结果：
注释 URL 在文件中先出现，先被替换掉自己那一小段，真实 URL 因此被切成
`file://<GitLab 主页 HTML 的缓存文件>` + `/-/archive/v1.4.1/looktxt-v1.4.1.tar.gz`，
一个把 HTML 缓存文件当目录的路径。`source()` 解包时抛 `NotADirectoryError`。

因为 `conan-verify` 不改写 `conandata.yml`，它看不到这个差异，于是形成
“本地能建、门禁不能建”的误导性组合。

## 3. 处置

`conandata.yml` 里**只允许出现一处 URL**，即 `sources.url`。上游主页、来源核验
（Debian `.dsc` 的 Homepage + orig sha256 与 GitLab tag 归档 sha256 同一，即 `deb.debian.org/debian/pool/main/l/looktxt/looktxt_1.4.1-3.dsc` 的 Checksums-Sha256 记录值）等
信息写在软件级 `README.md`、版本级 `manifest.yaml` 与 `notes.md`——这三个文件不被
预下载步骤解析。并在 `conandata.yml` 顶部用不含 URL 的措辞写下该约束，防止后来者
为了“方便”把主页地址补回注释。

```yaml
# 本文件注释中**不得出现 sources.url 的前缀型 URL**：CI 预下载阶段会按找到的
# 每个 URL 做 str.replace 改写成 file:// 路径，前缀 URL 先被替换会拼出不存在的路径
```

同时必须清掉已被污染的缓存条目：`conandata.yml` 修好后，`.build-cache/predl_cache/acb8fbe0_looktxt`
（存的是主页 HTML）仍在，门禁会再次拿它去替换，症状不变。删除该文件后门禁 100% 通过：

```
L0/L0k/L0e/L1/L1a/L1b/L1e/L2/L4/L5 → pass   Pass rate: 100.0% (1/1)
```

## 4. 与既有知识的关系

| 条目 | 覆盖内容 | 未覆盖 |
|---|---|---|
| E333 | 预下载抓 URL 的正则字符类排除 `-`，导致含连字符的 sdist URL 被截断 | 抓取范围含注释、以及前缀碰撞的 `str.replace` 顺序问题 |
| E415 | 镜像 fallback **原地改写** worktree 的 conandata.yml，CI 后必须核验恢复 | 改写机制本身把注释当下载源 |
| E372 | 无 curl/无 SSL 的 worker 上按哈希回落到 HTTP 镜像 | 与本案同一段代码，但失败在路径拼接而非网络 |

本案的独立价值：它说明“`conandata.yml` 中任意一处 URL 文本都会被视为下载源”，
因此该文件必须按单 URL 约束书写；并给出 `conan-verify` 与 `W3` 结论相反时优先查
预下载改写的判别顺序。
