# E561 — HTTP Content-Encoding 透明解压导致源码归档跨下载器 SHA256 不一致的诊断与修复

- 贡献者：4FE2
- 状态：draft（未 promote）
- 实例：morse 2.7（Morse Classic）源码真实性核验
- 关联：E406（多网络路径交叉验证）、E231（官方归档与成员真实性绑定）

## 使用说明

当同一源码 URL 在不同下载客户端下产生不同的 SHA256（典型组合：本地 curl 核验通过、
Conan/CI 报 checksum mismatch），先不要改 SHA、不要换源、更不要怀疑上游漂移。按本文
的"三层字节模型 + 通用诊断算法"逐步取证，先证明两个哈希各自对应的字节层，再决定
修复方式。本文提供可直接执行的诊断命令链与 fail-closed 边界。

## 适用范围

- Conan `tools.files.get`/`download` 及其底层 requests/urllib3 下载路径。
- curl/wget 与 Python HTTP 客户端交叉核验源码哈希的场景。
- `.tar.gz`/`.tgz`/`.gz` 源码归档。
- 服务器、代理或镜像对本身已是 gzip 的资源返回 `Content-Encoding: gzip/x-gzip`。
- 本地 curl SHA 正确但 CI/Conan checksum mismatch。
- 跨客户端源码真实性核验（证明两个哈希都对应真实数据）。

## 不适用范围

- 上游真实替换了发布物（应用 E406 多网络路径交叉验证，换哈希是正确修复）。
- HTML 错误页或代理认证页（非 gzip 封装层差异问题）。
- 下载截断（Content-Length 与实际字节不符）。
- codeload URL basename 无扩展名导致 BadZipFile（E276/E483）。
- GitLab 418（E347）。
- 单文件资产被错误解压（E271）。
- 仅 Content-Type 不同但响应字节完全相同（无层错位）。
- 普通稳定 tarball 的真实哈希变更（直接更新哈希即可）。

## 输入定义

| 输入 | 说明 |
|------|------|
| URL | 出现跨下载器哈希不一致的源码 URL |
| SHA_expected | 配方/conandata 中声明的 SHA256 |
| SHA_curl | curl 下载原始字节的 SHA256 |
| SHA_conan | Conan（requests/urllib3）下载字节的 SHA256 |
| HDR | 完整响应头（Content-Type/Encoding/Length、ETag、重定向链） |
| RAW_FILE / DECODED_FILE / TAR_FILE | 诊断用临时文件占位符 |

## 输出定义

| 输出 | 说明 |
|------|------|
| 层等价证明 | gunzip(raw) == decoded 逐字节一致（`cmp` 退出码 0） |
| 源码树等价证明 | 两个归档解包后共有文件列表与逐文件哈希完全一致 |
| 替代归档验证 | tag/commit、来源、SHA256、curl 与 Conan 字节稳定 |
| 修复 commit | 更新 conandata/manifest/notes 中的 URL/SHA/证据 |
| 验证结果 | make check、test_package、git diff --check 通过 |

## 错误表现

真实文本（Conan 2.29.1，`conan/internal/util/files.py:110`）：

```text
ERROR: sha256 hash failed for 'morse-2.7.tar.gz' file. Provided hash: 6ae4a76fc5aa57a520dca38380676142fd427a1748501a71cadd352c3f187fe3,
Computed hash: 48fc1b2b4656dad804caf7f912e86e3c50b393890c8cf16b5172982da902f236, Provided in downloaders: []
ERROR: Remotes have probably failed...
```

通用形式（可迁移正则，不绑定 morse 固定哈希）：

```text
sha256 hash failed.*Provided hash:.*Computed hash:
checksum mismatch.*sha256
different sha256.*same (url|source)
expected checksum.*actual checksum
gzip 原始文件与透明解码后的 tar 流大小不同
```

## 三层字节模型

| 层 | 内容 | morse 2.7 CATB 实测 |
|----|------|---------------------|
| L1 传输层原始字节 | curl 保存的响应体（gzip 封装） | 47093 B / 6ae4a76f… |
| L2 Content-Encoding 解码层 | requests/urllib3 交付的纯 tar 流 | 184320 B / 48fc1b2b… |
| L3 源码内容层 | tar 成员 36 个共有源码文件 | 逐文件一致 |

关键点：SHA256 作用在字节序列上；L1≠L2 必然产生不同哈希；L1/L2 是同一数据的两种
封装，不是两个版本。根因是服务端对本身已是 gzip 的资源返回 `Content-Encoding:
x-gzip`——urllib3 2.3.0 按 RFC 9110 §8.4.1 将 x-gzip 等价 gzip 并自动解码，curl
默认保存原始传输字节（`--raw`/`--compressed` 才改变该行为）。

## 根因分析

1. 服务端对本身已经是 gzip 归档的资源返回 `Content-Encoding: gzip/x-gzip`。这违反
   HTTP 语义意图（Content-Encoding 应描述传输编码，而非资源本体编码），catb.org 即
   如此。
2. curl 默认保存传输层原始响应体。
3. requests/urllib3 按 HTTP 语义自动解码 Content-Encoding，交付 L2 字节。
4. Conan 下载器（requests 底层）取得 L2，与本地 curl 的 L1 哈希必然不同。
5. SHA256 是对字节序列计算的，封装层不同必然产生不同哈希——两个哈希都对应真实数据。
6. 两个哈希不同不等于源码内容不同（L3 一致）；但配方需要的是确定、可重复、跨 CI
   下载器稳定的字节身份，不能将客户端偶然观察到的解码后哈希直接替换为新的标准哈希
   （那会把 L2 固化为标准，curl/CI 场景再次 mismatch）。

## 通用诊断算法

1. 保存完整响应头，记录 Content-Type、Content-Encoding、Content-Length、ETag、重定向链。
2. 用能保存原始响应体的方式下载 raw bytes（curl 默认行为）。
3. 用与 Conan 相同或等价的 requests/urllib3 路径下载 decoded bytes。
4. 分别记录文件大小、SHA256、`file` 类型和 magic bytes。
5. 若 raw 是 gzip、decoded 是 tar，计算 gunzip(raw)。
6. 比较 gunzip(raw) 与 decoded 是否逐字节一致（`cmp`）。
7. 分别解包并做成员列表与逐文件哈希比较。
8. 区分封装差异与源码内容漂移。
9. 查找同版本的其他官方归档或官方仓库 tag archive。
10. 验证替代归档的 tag/commit、来源、SHA256 和源码树等价性。
11. 用 Conan 宲下载器至少下载两次，确认字节稳定。
12. 更新 conandata、manifest 和 notes 中的 URL/SHA/真实性证据。
13. 重新执行完整构建、上游测试和 test_package。
14. 无法建立来源和源码树等价关系时必须 fail closed。

## 推荐修复方案

优先切换到同一上游维护者、同一 tag/commit、无 Content-Encoding 字节歧义、能够被
curl 与 Conan 下载器稳定获取的官方归档。

morse 2.7 实例：CATB `http://www.catb.org/esr/morse/morse-2.7.tar.gz` → GitLab
官方 tag archive `https://gitlab.com/esr/morse-classic/-/archive/2.7/morse-classic-2.7.tar.gz`
（提交 3713268d38）。

## fallback

仅当没有等价官方归档可用时讨论：

- 在下载层显式控制 raw response 读取、关闭自动 decode；
- 固定实际校验层级（校验 L1 或 L2，并显式声明）；
- 保存响应头和原始字节证据；
- 必须确保 CI、Conan 和维护工具全部使用同一字节层；
- 如果 recipe 标准下载器无法保证该行为，应拒绝使用该 URL，而不是依赖本地缓存。

不把 file://、predl_cache 或个人本地 tarball 作为 fallback。

## fail-closed 安全边界

见 KV 中 forbid_1 ~ forbid_8。核心：未检查响应头禁止改 SHA；禁止把透明解码后的哈希
写成对所有客户端下载都成立的哈希；禁止只比较文件大小；禁止只依赖扩展名判断字节层；
禁止把所有 hash mismatch 归因于上游漂移；禁止把 HTML/认证页当源码；禁止只比较能否
解包而不比较源码树；禁止 file:///predl_cache/个人缓存掩盖远端不稳定；禁止切换非官方
镜像而不验证 tag/commit 与源码树等价；无法证明来源真实性时必须终止，不得伪造成功。

## 实际示例：morse 2.7

| 项目 | CATB .tar.gz（curl 原始） | CATB decoded | GitLab 2.7 archive |
|------|---------------------------|--------------|--------------------|
| 大小 | 47093 B | 184320 B | 49429 B |
| SHA256 | 6ae4a76fc5aa57a520dca38380676142fd427a1748501a71cadd352c3f187fe3 | 48fc1b2b4656dad804caf7f912e86e3c50b393890c8cf16b5172982da902f236 | 61d6ddaf2365fb767f321a13a0bed82d96e5729e396a4ca5914d207819efd1b0 |
| 层 | L1 gzip 封装 | L2 纯 tar 流 | L1 gzip 封装 |
| 成员 | 41 项（38 文件） | 41 项 | 42 项（39 文件） |
| Content-Encoding | x-gzip | —（已解码） | 无 |

- CATB：HTTP 200、`Content-Type: application/x-gzip`、`Content-Encoding: x-gzip`、
  合法 gzip、`tar -tzf` 成功。
- CATB `.tar` 路径存在相关 Content-Encoding 行为；HTTPS 存在证书主机名问题——均按
  实际记录，不扩大结论。
- 修复：切换为 GitLab 官方 tag archive（tag 2.7、commit 2af424ba1a12）。
- 修复后：Conan SHA 校验通过、make check 2/2、test_package 28/28、
  `git diff --check` 通过（提交 3713268d38）。
- 本知识根因不涉及本地 profile CC 路径错误和 testqso 高负载偶发挂起（notes.md 中
  另有记录，属独立问题）。

## CATB 原始 gzip 与透明解码 tar 的等价证明

```bash
# raw = curl 原始字节（L1），decoded = requests 交付字节（L2）
sha256sum raw decoded      # 6ae4a76f… / 48fc1b2b…
gzip -dc raw > gunzip_raw  # gunzip(raw)
cmp gunzip_raw decoded     # 退出码 0：逐字节一致
```

实测：`gunzip(raw)` 大小 184320 B、SHA256 48fc1b2b…，与 requests 交付的 decoded
逐字节一致。因此 48fc… 不是 HTML 错误页、代理污染、上游漂移、下载截断或不同版本
源码——它是同一源码的 L2 表示。CATB/GitLab 解包后 36 个共有源码文件逐字节一致，
差异仅为打包层文件（CATB 独有预生成 man 页 morse.1/QSO.1；GitLab 独有 .gitignore、
control、morse-logo.png）。不声称两个 tarball 整体字节一致。

## GitLab 官方归档真实性证明

- URL：`https://gitlab.com/esr/morse-classic/-/archive/2.7/morse-classic-2.7.tar.gz`
- tag 2.7、commit 2af424ba1a12（GitLab API 实测）。
- 49429 B / 61d6ddaf2365fb767f321a13a0bed82d96e5729e396a4ca5914d207819efd1b0。
- 响应不返回导致透明解压歧义的 Content-Encoding。
- curl 重复下载字节一致；Conan 实际下载与 curl 字节一致。
- 与 CATB 归档源码内容经逐文件比较一致（36 共有文件，差异仅打包层文件）。

## 修复后验证

- Conan SHA 校验通过（conandata.yml 中 URL/SHA 已更新为 GitLab archive）。
- `make check` 2/2 通过。
- `test_package` 28/28 通过。
- `git diff --check` 通过。
- 参见提交 3713268d38：`fix(morse/2.7): switch source to official GitLab 2.7 tag archive`。

## 与现有知识条目的区别

- E231：官方源码归档与成员真实性绑定——不涉及 Content-Encoding 透明解压，也不涉及
  curl 与 requests/urllib3 获得不同封装层字节。
- E406：源码 SHA256 多网络路径交叉验证——不解释"两个哈希都对应真实数据"的机制，
  也不提供 gunzip(raw)==decoded 等价证明方法。
- E276/E483：codeload URL basename 无扩展名导致误判 zip——误判发生在"格式识别"层，
  不是传输字节层。
- E347：GitLab 418——服务端限流/拒绝，不是响应体解码层差异。
- E271：单文件发布物被误判为压缩归档——同样是格式识别层问题。

本文独有：Content-Encoding 导致 HTTP 客户端透明解压；curl 与 requests/urllib3 获得
不同封装层字节；两个不同 SHA256 都对应真实数据；gunzip(raw) 与 decoded body 建立
等价关系；区分传输层原始字节、Content-Encoding 解码层和归档内容层；选择跨下载器
字节稳定的官方等价归档。

## 关联条目

- E406 源码 SHA256 多网络路径交叉验证（similar_to）
- E231 官方源码归档与成员真实性绑定（similar_to）
- E276/E483 codeload basename/显式 filename（相关，非 similar）
- E347 GitLab 418（相关，非 similar）
- E271 单文件资产误判归档（相关，非 similar）

原则引用：P013（环境限制不因重试改变，必须降级而非绕过；E406 已将其用于网络路径
来源核验场景——此处"降级"指从有字节歧义的 CATB 双层分发降级到无歧义的 GitLab
单层官方归档，而非绕过验证）。
