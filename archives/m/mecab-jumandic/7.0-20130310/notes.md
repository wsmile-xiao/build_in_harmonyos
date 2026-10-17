# mecab-jumandic 7.0-20130310 适配笔记

## 任务身份

- 平台库名: mecab-jumandic
- 平台版本: 7.0-20130310
- Issue: #10707 分支附带任务
- 分支: feat/mecab-jumandic-7.0-20130310
- 路径: 路径 A（普通适配）

## 上游身份

- 项目: mecab-jumandic（MeCab 日文 JumanDic 词典）
- 上游主页: https://taku910.github.io/mecab/
- 上游版本: 7.0-20130310（2013-03-10 快照）
- 许可证: BSD-3-Clause（COPYING 文件，Copyright (c) 2005 University of Tokyo / NTT）
- 源码: 上游 canonical 托管在 Google Drive（构建不稳定）
  - 采用 Debian 官方 pool 镜像的同源 orig tarball（SHA256 与
    mecab-jumandic_7.0-20130310-7.dsc 记录一致）:
    `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/m/mecab-jumandic/mecab-jumandic_7.0-20130310.orig.tar.gz`
    （deb.debian.org / mirrors.ustc.edu.cn 作备选 URL）
  - SHA256: eaf216758edee9a159bc3d02507007318686b9537943268c4565cc1f9ef07f15

## 归档身份

- Conan name/version: mecab-jumandic/7.0-20130310
- 归档路径: archives/m/mecab-jumandic/7.0-20130310/
- 软件类型: 数据包（无编译），软件级 commands.json 不适用（R38：仅命令行工具需要）

## 软件形态

- 16 个 CSV 词典文件（ContentW/Wikipedia/Auto/Noun.*/Verb/Adj/Adv 等）、
  9 个 DEF 定义文件（char/feature/left-id/matrix/model/pos-id/rewrite/right-id/unk）、
  dicrc 配置
- CSV 总行数: 751,185（精确校验）；ContentW.csv 551,145 为最大文件
- 编码: **UTF-8**（同 mecab-ko-dic，异于 mecab-ipadic 的 EUC-JP）
- 已知数据瑕疵（上游固有，不 patch）: 4 个文件
  （AuxV.csv 6 行 / left-id.def 6 行 / right-id.def 6 行 / model.def 2919 行）
  行尾带截断的 2 字节 UTF-8 序列（`\xe3\x81` 缺第 3 字节）。Debian
  官方包（7.0-20130310-7）未打数据补丁直接发布；mecab-dict-index 编译
  容忍（本机实测成功）；校验按精确坏行预算放行、其余 22 文件严格 UTF-8
- 二进制索引（char.bin/matrix.bin/model.bin/sys.dic/unk.dic）由
  tool_requires mecab/0.996 的 mecab-dict-index 确定性生成
  （`-f utf-8 -t utf-8`，同上游 Makefile.am 的 `@MECAB_DICT_INDEX@` 调用）

## 适配方案（E251 nlp-dictionary-package-pattern + 确定性索引生成）

- conanfile.py: 数据包（settings 四项满足 CI L0p）；source() 用 get() +
  SHA256 严格校验（TUNA 主源 + USTC/deb.debian.org 备选）；build() 校验
  16 CSV/9 DEF/751,185 总行数/UTF-8（含上游瑕疵预算）；build() 经
  tool_requires mecab/0.996 确定性调用 mecab-dict-index 生成 5 个二进制
  索引并断言全部生成成功（优于 ipadic/ko-dic 的 PATH 可选探测模式——
  本仓制品库已有 mecab/0.996，索引生成成为硬保证而非可选项）；
  package() 复制 CSV/DEF/dicrc + 二进制索引 + COPYING
- conandata.yml: Debian 官方镜像 URL（3 个）+ 真实 SHA256；无 patch
- test_package/: 双层测试
  1. test_mecab_jumandic.py（独立脚本，80 断言）: 文件存在性、CSV/DEF
     数量、UTF-8 校验（含 4 文件坏行预算精确匹配）、核心条目计数、
     总行数精确等于 751,185、二进制索引 5 文件必备（含 dicrc 同目录）
  2. HarmonyOS 专项（src/test_package.cpp，CMake 链接 libmecab）:
     OHOS 目标环境原生 C++ 消费——mecab_model_new2 加载本包词典对
     3 个固定日文样例分词，与 golden 输出精确比对首行 + EOS 校验

## OHOS 关键发现（本次适配实证）

1. **mecab 默认 rcfile 硬编码 `//etc/mecabrc`**（mecab 0.996 构建期
   MECAB_DEFAULT_RC 展开为 `//etc/mecabrc`），OHOS 只读根文件系统该
   路径不存在，mecab_model_new2 直接失败且错误信息易被吞
   （探针最初表现为空错误串）。消费端必须显式
   `--rcfile <dicdir>/dicrc`。
2. **dicrc 必须与 .bin 同目录**: mecab load_dictionary_resource()
   （mecab/src/utils.cpp:384-388）无条件加载 `<dicdir>/dicrc`，缺失即
   失败。mecab-dict-index 只生成 5 个二进制文件不复制 dicrc，故配方
   build() 显式将 dicrc 复制到索引输出目录（上游 Makefile.am 通过
   dic_DATA 安装达到同等效果）。
3. **OHOS aarch64 交叉一致**: 制品仓 mecab/0.996（OHOS aarch64）的
   mecab-dict-index 在 OHOS PC（aarch64）上原生运行编译出的索引，
   被 OHOS aarch64 libmecab 正确消费（3 样例 golden 全对）——工具与
   库同架构，无交叉字节序/ABI 问题。

## 上游测试

- mecab-jumandic 上游无自动化测试套件: Makefile.am 无 check target
  （仅 dic_DATA 安装与字典编译规则）；RESULT 文件是 Juman 词典精度
  基准报告（Chasen/Chaum/Juman 对比 precision/recall），非可执行测试
- 因此上游测试计数为 **0**；用消费者测试 + HarmonyOS 专项测试覆盖

## 验证记录（2026-09-20）

- conan create 真机构建（ohos-aarch64 profile，本机 OHOS PC aarch64）:
  通过（源码下载 SHA256 校验 → 数据完整性 → mecab-dict-index 索引生成
  → test_package 全绿）
- 消费者测试: 80 断言全通过（文件/编码/条目/二进制索引/dicrc 布局）
- HarmonyOS 专项: C++ 原生消费 3/3 样例 golden 精确比对通过
- 上游测试: 0（无测试套件，见上）
- conan-verify（ohc CLI）: 8/8 门禁 PASS（G0/G1/G2/G3/G4/L2/L4/L5），
  报告在 reports/conan-verify-report.md
- finish mecab-jumandic 7.0-20130310 built: 完成

## 知识库判断（路径 A + 一项可复用新知）

- E251（nlp-dictionary-package-pattern）已覆盖词典构建模式主体 → 沿用，
  未为构建模式新建条目；但按 E391（L0p 门禁）先例将 settings 保留四项
  （E251 文档中 settings = None 是 L0p 之前的旧写法，勿照抄）
- 全库查证（3775 文件 grep）: `mecabrc`/`rcfile`/`MECAB_DEFAULT_RC`/
  `dicrc` 零命中；E251 只管构建期，无条目覆盖"MeCab 词典在 OHOS 的
  运行期消费"问题
- 新知具备可复用性（所有 MeCab 系词典消费者 + 词典配方布局设计都会遇到，
  且有 strace/源码级根因实证）→ 按草稿流程贡献:
  knowledge/drafts/DRAFT-mecab-rcfile-ohos-consumer.{kv,md}
  （默认 rcfile 硬编码 //etc/mecabrc + 失败错误被吞 + dicrc 必须与
  索引同目录；消费端 --rcfile 用法 + 配方端 dicrc 共装方案）

---

**编译结束**: 2026-09-20
**最终状态**: built
