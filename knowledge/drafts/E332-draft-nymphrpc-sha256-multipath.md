# E332 知识草稿：scout/recipe 创建期 SHA-256 多网络路径交叉验证

> 编号：E332（草稿，待 graph promote 转正式；E321–E330 已占用，按设备端最大 E 编号顺延）
> 文件名：E332-draft-nymphrpc-sha256-multipath
> 实例来源：nymphrpc 0.1.1（scout 误测 5470a997 → 多路径交叉验证定 63bc35e8）
> 检索字段：library=nymphrpc / build=make / error=sha256 / toolchain=clang15 / platform=ohos

## 背景

E299 覆盖"Conan 源码获取失败的分层诊断"，是 CI 期的"事后"诊断工具。本草稿补 E299 的
"事前"前置层：recipe 创建期（scout/探针/conandata 维护）采集上游源码 SHA-256 时，
单一路径可能采到被改动的内容，导致误测。

## 复现（实证）

- scout 阶段 GitHub 直连流式 sha256sum 得 5470a997...，写入 conandata.yml。
- CI round-2a：source() 阶段报 sha256 hash failed: Provided 5470a997, Computed 63bc35e8。
- 多路径交叉验证定论：官方 codeload 直连 ×3 稳定
  63bc35e8d50e34a877c467949691c8d2cf80d2478d02211ca768791511c5f3f8（14125567 字节）；
  本机 Windows 独立网络路径一致；gh-proxy/ghfast 双代理与官方字节 cmp IDENTICAL。
- 修复：conandata.yml / manifest.yaml / ci-metadata 三处统一 63bc35e8，后续 CI PASS。

## 修复方案（可复用流程）

1. 采集：对官方 tag tarball 至少 2 条网络路径流式 sha256sum（官方 codeload/直连 + 独立
   本机路径 + 至少 1 个代理）。
2. 判定：多路径 hash 一致才可写入 conandata.yml；不一致时以官方发布物为准并排查污染源。
3. 记录：把交叉验证结果写进 run 报告，保留可追溯证据。
4. 一致性：conandata.yml / manifest.yaml / ci-metadata 三处必须同一 hash，防漂移。

## Do Not

- 单一路径（尤其只走一个代理或只走直连）的 hash 不得直接写入 conandata.yml。
- 不要把"hash 校验失败"一律当网络问题换镜像；按 E299 分层，再回到本前置层排查采集期污染。

## 验证

- conandata.yml sha256=63bc35e8d50e34a877c467949691c8d2cf80d2478d02211ca768791511c5f3f8，
  与 codeload×3 / 本机 / 双代理一致；ci-round-2f.log PASS（all assertions passed）。

## 关联条目

- E299（前置层关系）：CI 期"事后"分层诊断；本稿为创建期"事前"治理，互补不互斥。
- E271 / E285：下载链路相关既有条目（similar_to 参考）。
- P013：平台限制必须降级而非绕过（采集期误测属可治理流程缺陷，非平台限制；P013 作弱关联）。
