# DRAFT-nicovideo-dl-source-license-provenance：Debian orig 源码归档的来源和许可证治理

> 路径 B 知识库扩展草稿；正式编号及是否提升由知识库维护者和赛事评审决定。
> 来源：nicovideo-dl 0.0.20190126 适配，PR #9377。

## 适用场景

历史项目的官网或原始下载入口可能已经不稳定，但发行版仍保存指定版本的
`orig` 源码归档。发行版归档可以作为可复现来源，前提是明确它是下游托管
文件，并把 URL、版本和 SHA256 固定下来。

## 本案例

本轮使用的源码地址是：

```text
https://deb.debian.org/debian/pool/main/n/nicovideo-dl/nicovideo-dl_0.0.20190126.orig.tar.gz
```

对应 SHA256：

```text
886980d154953bc5ff5d44758f352ce34d814566a83ceb0b412b8d2d51f52197
```

它对应上游项目 `nicovideo-dl` 的 `0.0.20190126` 版本，但 URL 的托管者是
Debian。配方把它写入 `conandata.yml` 的 `sources`，由 Conan `get()` 下载和
校验；`notes.md` 同时记录 Debian orig 的来源身份，避免把下游地址误写成上游
官网地址。

## 许可证差异

Debian copyright 将这份代码的许可证族归类为 Expat，但归档中的 `LICENSE` 在
标准 Expat/MIT 风格授权和免责声明之后，还包含禁止使用版权人姓名宣传或推广
该软件销售的附加条款。仅写 `MIT` 或只写 `Expat` 会丢失这个事实。

本案例因此采用：

- `LICENSE` 原文随包安装；
- `manifest.yaml` 和版本元数据记录 `X11` 变体；
- `notes.md` 解释“Debian 归类为 Expat，但实际文本有 no-promotion 条款”的
  选择依据。

这里的关键不是追求一个完美的 SPDX 名称，而是让元数据与随包许可证文本一致，
并让审查者能够复核选择过程。

## 推荐流程

1. 先确认归档文件对应的项目和版本，不把发行版重新打包版本当成上游版本。
2. 在 `conandata.yml` 中固定 HTTPS URL 和真实 SHA256，禁止占位哈希。
3. 下载并解包后审阅 `LICENSE`、版权文件和必要的 Debian copyright 信息。
4. 在 manifest/notes 中说明来源层级和许可证选择，不隐瞒下游来源或附加条款。
5. 用 `conan create --build=missing` 重新验证下载、解包和打包链路。

## 实证结果

nicovideo-dl 适配中，Conan 成功下载并校验上述归档，源码 smoke、打包和
test_package 均通过；没有源码补丁，也没有把 Debian 打包脚本或 Debian 运行时
依赖混入 Conan 配方。

## 禁止做法

- 不能把 Debian pool URL 写成“上游官方发布地址”。
- 不能用未核验镜像替代固定 SHA256。
- 不能只看发行版的简短许可证分类而跳过实际 `LICENSE` 文本。
- 不能删除或缩短随包许可证文本来迎合某个 SPDX 名称。

## 去重结论

本条聚焦“历史版本源码来源身份 + 下游 orig 归档 + 实际许可证附加条款”的
联合审计，区别于一般的 SHA256 记录或普通许可证复制。它可复用于上游站点失效、
发行版保留原始归档的其他第三方库，因此作为独立路径 B 草稿提交。
