# mecab-ipadic 2.7.0-20070801 适配笔记

## 任务身份

- 平台库名: mecab-ipadic
- 平台版本: 2.7.0-20070801
- Issue: #2167
- 分支: feat/mecab-ipadic-2.7.0-20070801
- 路径: 路径 A（普通适配）

## 上游身份

- 项目: mecab-ipadic（MeCab 日文 IPA 词典）
- 上游主页: https://taku910.github.io/mecab/
- 上游版本: 2.7.0-20070801（2007-08-01 发布）
- 许可证: NAIST-2003（COPYING 文件，含 ICOT Free Software 条款）
- 源码: 上游 canonical 托管在 Google Drive（`0B4y35FiV1wh7MWVlSDBCSXZMTXM`，构建不稳定）
  - 采用 Debian 官方 pool 镜像的同源 orig tarball（与 Homebrew/Ubuntu 记录的
    SHA256 一致）:
    `https://deb.debian.org/debian/pool/main/m/mecab-ipadic/mecab-ipadic_2.7.0-20070801+main.orig.tar.gz`
  - SHA256: b62f527d881c504576baed9c6ef6561554658b175ce6ae0096a60307e49e3523

## 归档身份

- Conan name/version: mecab-ipadic/2.7.0-20070801
- 归档路径: archives/m/mecab-ipadic/2.7.0-20070801/
- 软件类型: 数据包（无编译），软件级 commands.json 不适用（R38：仅命令行工具需要）

## 软件形态

- 26 个 CSV 词典文件（Noun/Verb/Adj 等词类）、8 个 DEF 定义文件
  （char/feature/left-id/matrix/pos-id/rewrite/right-id/unk）、dicrc 配置
- CSV 总行数: 392,126；核心文件行数: Noun.csv 60,477 / Verb.csv 130,750 / Adj.csv 27,210
- 编码: **EUC-JP**（dicrc 中 config-charset = EUC-JP），与 mecab-ko-dic（UTF-8）不同
- 二进制索引（char.bin/matrix.bin/model.bin/sys.dic/unk.dic）由外部
  mecab-dict-index 工具生成，本包不内嵌 mecab 工具（R18 预编译包优先）

## 适配方案（E251 nlp-dictionary-package-pattern）

- conanfile.py: 数据包（settings 四项满足 CI L0p，构建无编译）；source() 用 get() + SHA256 严格校验；
  build() 校验 CSV/DEF 数量、条目数、EUC-JP 编码；有 mecab-dict-index 时可选生成
  二进制索引；package() 复制 CSV/DEF/dicrc + 许可证（COPYING）
- conandata.yml: 官方镜像 URL + 真实 SHA256
- test_package: 独立脚本 test_mecab_ipadic.py，覆盖文件存在性（24 asserts）、
  CSV/DEF 数量、EUC-JP 编码校验、核心词条计数、总行数、条件性 mecab 分词冒烟测试
  （mecab 工具不可用时如实 skip，不属于错误伪装）

## 上游测试

- mecab-ipadic 上游无自动化测试套件：Makefile.am 无 check target；RESULT 文件是
  词典精度基准报告（20060408/20060707/20070610/20070801 的 precision/recall），
  不是可执行测试
- 因此上游测试计数为 0；用消费者测试（test_package 数据完整性 + 可选分词）覆盖主要产物

## 验证记录（2026-08-14）

- conan create 真机构建（ohos-aarch64 profile）: 通过
- 消费者测试断言: 见 test_package 输出（文件/编码/计数断言全通过）
- conan-verify: 8 道门禁通过
- finish mecab-ipadic 2.7.0-20070801 built: 完成
---

**编译结束**: 2026-08-14 19:03
**最终状态**: built
