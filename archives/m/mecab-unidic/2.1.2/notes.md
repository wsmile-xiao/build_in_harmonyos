# mecab-unidic 2.1.2 适配笔记

## 任务身份

- 平台库名: mecab-unidic
- 平台版本: 2.1.2
- 分支: feat/mecab-unidic-2.1.2
- 路径: 路径 A（普通适配）

## 上游身份

- 项目: mecab-unidic（MeCab 日文 UniDic 词典，NINJAL 日本国立国语研究所）
- 上游主页: https://clrd.ninjal.ac.jp/unidic/
- 上游版本: unidic-mecab 2.1.2（2.1.2 系列，2014-02-18 发布）
- 许可证: GPL-2.0-or-later OR LGPL-2.1-or-later OR BSD-3-Clause（三选一，
  COPYING + GPL + LGPL + BSD 四个文件）
- 源码: 上游 canonical 托管在 OSDN（unidic 项目 58338，dl 界面限速 ~22KB/s）
  - 采用 dotsrc.org 官方 OSDN 镜像（Homebrew mecab-unidic formula 的主源）:
    `https://mirrors.dotsrc.org/osdn/unidic/58338/unidic-mecab-2.1.2_src.zip`
  - SHA256: 6cce98269214ce7de6159f61a25ffc5b436375c098cc86d6aa98c0605cbf90d4
    （140,517,811 字节，与 Homebrew 记录一致）

## 归档身份

- Conan name/version: mecab-unidic/2.1.2
- 归档路径: archives/m/mecab-unidic/2.1.2/
- 软件类型: 数据包（无编译），软件级 commands.json 不适用（R38：仅命令行工具需要）

## 软件形态

- 单一 lex.csv（756,463 条目）+ matrix.def（514MB，131,610x131,610 连接矩阵）
  + char.def/unk.def/left-id.def/right-id.def/rewrite.def/feature.def + dicrc
- 编码: **UTF-8**（与 mecab-ipadic EUC-JP 不同；索引生成 `-f utf8 -t utf8`）
- dicrc: cost-factor=700、output-format-type=unidic（17 列特征输出）
- 二进制索引（char.bin/matrix.bin/sys.dic/unk.dic）由外部 mecab-dict-index
  工具生成（本机 OHOS aarch64 实测约 15 秒），本包不内嵌 mecab 工具

## 适配方案（E251 nlp-dictionary-package-pattern）

- conanfile.py: 数据包（settings 四项满足 CI L0p，构建无编译）；source() 用
  get() + SHA256 严格校验；build() 校验核心文件、lex.csv 条目数
  （==756463）、matrix.def 大小（>500MB）、UTF-8 编码、dicrc 内容；有
  mecab-dict-index 时生成二进制索引；package() 复制数据文件 + dicrc + 四个
  许可证文件
- conandata.yml: dotsrc.org（OSDN 官方镜像）URL + 真实 SHA256
- test_package: 独立脚本 test_mecab_unidic.py，覆盖文件存在性、条目数、
  矩阵大小、UTF-8 编码、dicrc 校验、**OHOS 包布局专项测试**（dic/ 安装目录、
  dicrc 无构建机路径泄漏、数据包无 bin/lib 泄漏、三重许可证随包）、
  **条件性真实 mecab 消费测试**（从 conan 缓存找 mecab/0.996 OHOS 包，编译
  小消费者链接 libmecab.a 真实加载本词典做分词，验证安装产物可用而不仅是
  文件存在）

## 上游测试

- mecab-unidic 上游无自动化测试套件：unidic-mecab-2.1.2_src 源码内 Makefile.am
  无 check target，无测试文件；unidic-mecab.pdf 是词典说明文档，不是测试
- 因此上游测试计数为 0；用消费者测试（test_package 数据完整性 + OHOS 布局
  + 可选真实分词）覆盖主要产物

## 关键实测结论（2026-09-21，本机 OHOS aarch64 工具链）

- mecab-dict-index（mecab/0.996 OHOS 构建缓存）生成完整 UniDic 索引约 15 秒
- 生成的二进制体积: sys.dic 133,863,109 B / matrix.bin 71,544,726 B /
  char.bin 262,496 B / unk.dic 5,492 B
- 真实消费验证: 编译 consumer.cpp 链接 libmecab.a（mecab/0.996 OHOS 缓存包），
  `mecab_new2("-d <dicdir> -r <dicdir>/dicrc")` 成功加载本词典，
  「すもももももももものうち」输出 UniDic 特征格式（表层/读音/lemma/PoS 列）
- **重要**: libmecab 加载 UniDic 时必须显式 `-r <dicdir>/dicrc`——不带 -r 时
  mecab_new2 失败且 strerror 返回空串（静默失败）；这是 UniDic dicrc 的
  dictionary-charset 行被注释（utf-8 为默认）与 rc 文件查找路径共同作用的
  行为，ipadic 无此问题
- conan 下载缓存: `~/.conan2` 即 core.sources:download_cache，源缓存布局为
  `s/<sha256>`（文件本体）+ `s/<sha256>.json`（references 元数据）；预置后
  conan create 的 get() 直接命中，避免重复下载 140MB

## 验证记录（2026-09-21）

- conan create 真机构建（ohos-aarch64 profile）: 通过
  （Package '6b129b068851896169fae42d399fa922d239ce8a' created，
  二进制索引 4/4 生成，包体积 827MB）
- 消费者测试断言: 33 项全部通过（核心文件 18 + lex 条目数 1 + 矩阵大小 1 +
  UTF-8 1 + dicrc 2 + OHOS 包布局 7 + 真实 mecab 消费 3）
- 真实消费样例: すもも → スモモ/スモモ/李/名詞-普通名詞-一般（UniDic 特征列）
---

**适配完成**: 2026-09-21
**最终状态**: built（未提交，等待 review）

## 复验记录（2026-09-23，终端中断后恢复）

- 恢复确认: source（下载缓存 s/6cce98... 命中）/ build / package（缓存包
  6b129b068851896169fae42d399fa922d239ce8a）上次均已完成，本次为真机复跑
- 复跑命令: `PATH="$HOME/.conan2/p/mecabdd2fd7c5299d5/p/libexec/mecab:$PATH" \
  conan create archives/m/mecab-unidic/2.1.2 -pr:h=ohos-aarch64-local`
  （mecab-dict-index 来自缓存 mecab/0.996 OHOS 包的 libexec/mecab/，注入
  PATH 后 recipe 的 _find_mecab_dict_index 才能找到；不带 PATH 复跑时二进制
  索引为 0/4 且消费测试降级为 SKIP，属预期条件性行为）
- 复跑结果: Forced build from source，二进制索引 4/4 生成，包
  6b129b068851896169fae42d399fa922d239ce8a#cd02fe6713be0e5fd3eb5a797dcdfaa6
  重建成功（与 9-21 记录同 ID 同 revision），包体积 808MB，dic/ 17 文件
- test_package: 33 项断言全部通过（核心文件 18 + lex 条目数 1 + 矩阵大小 1
  + UTF-8 1 + dicrc 2 + OHOS 包布局 7 + 真实 mecab 消费 3），
  真实分词样例 すもも → スモモ/スモモ/李/名詞-普通名詞-一般
- git diff --check: 通过（无空白错误）；libXext 无关修改未触碰，未 commit

## tool_requires 改造复验（2026-09-23，第二次复跑）

- 改造内容: conanfile.py 增加 `tool_requires("mecab/0.996")`，
  `_find_mecab_dict_index` 从依赖包 package_folder/libexec/mecab/ 显式解析
  （mecab package_info 未声明 libexecdir），build()/package() 全部 fail-closed；
  test_package requires mecab/0.996，消费测试改为显式传入 mecab 包路径，
  二进制索引与真实分词测试不再有 SKIP 路径
- 复跑命令（无 PATH 注入）: `conan create archives/m/mecab-unidic/2.1.2 \
  -pr:h=ohos-aarch64-local -pr:b=ohos-aarch64-local --build="mecab-unidic/*"`
  注意: 须带 -pr:b=ohos-aarch64-local，否则 build context 走 default profile
  （Linux x86_64）导致 mecab/0.996 Missing binary
- 复跑结果: Forced build from source；mecab-dict-index 自动解析自
  `~/.conan2/p/mecabdd2fd7c5299d5/p/libexec/mecab/mecab-dict-index`；
  二进制索引 4/4 生成；包 6b129b068851896169fae42d399fa922d239ce8a#cd02fe6713be0e5fd3eb5a797dcdfaa6 重建成功
- test_package: 46 项断言全部通过（核心文件 18 + lex 条目数 1 + 矩阵大小 1 +
  UTF-8 1 + dicrc 2 + 二进制索引 8 + OHOS 包布局 7 + 真实 mecab 消费 8），
  真实分词样例 すもも → スモモ/スモモ/李/名詞-普通名詞-一般
- git diff --check: 通过（无空白错误）；未 commit
