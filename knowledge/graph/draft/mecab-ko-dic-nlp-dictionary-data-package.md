# mecab-ko-dic — NLP 词典/分词数据包在 OHOS 上的固定源码 hash、UTF-8 编码校验、词典文件/条目统计、mecab-dict-index 索引生成、固定韩语样本文本分词输出精确比对方法

## 使用说明

当适配 OHOS 平台的 NLP 词典/分词数据包（需固定源码 hash、UTF-8 编码校验、词典文件统计、mecab-dict-index 索引生成、固定韩语样本文本分词输出精确比对）时使用本条目。本条目以 mecab-ko-dic 2.1.1-20180720（Korean MeCab Dictionary Data）为例，说明完整的 NLP 词典数据包适配模式。

## 适用范围

- 韩语/其他语言 MeCab 词典数据包（mecab-ko-dic、mecab-ipadic 等）
- 任何以 CSV/DEF 为词典源文件、以 mecab-dict-index 为索引生成工具的 NLP 数据包
- 需要固定版本 SHA256 校验的词典资源
- 需要 UTF-8 编码校验的 CSV/DEF 文件集
- 需要固定样本文本精确分词比对的词典数据

## 输入定义

- 上游 tarball 下载 URL + SHA256（参考值：fd62d3d6d8fa85145528065fabad4d7cb20f6b2201e71be4081a4e9701a5b330）
- 词典 CSV 源文件（40 个文件，~816,283 条目）
- 词典 DEF 配置文件（char.def, pos-id.def, rewrite.def, unk.def, feature.def）
- dicrc 配置文件
- 外部工具依赖：mecab-ko（提供 mecab-config、mecab-dict-index、mecab 可执行）
- 固定韩语样本文本：`화학 이외의 것`
- 预期分词输出（来自上游 seed/test/expected_output.txt）

## 输出定义

- `conandata.yml`：固定源码 URL + SHA256（含备用镜像 URL）
- `conanfile.py`：NLP 词典数据包配方（settings=None，无编译，package 阶段打包 dic/ 目录）
- `test_package/conanfile.py`：含数据完整性校验（CSV/DEF 文件存在性、UTF-8 编码、条目统计）
- `smoke/golden/mecab-ko-dic-golden.txt`：固定样本文本的预期分词输出
- 二进制索引文件（char.bin, matrix.bin, model.bin, sys.dic, unk.dic）：由 mecab-dict-index 生成

## 数据完整性校验

### CSV/DEF 文件统计
```
CSV 文件: 40
DEF 文件: 9 (char.def, feature.def, left-id.def, right-id.def, matrix.def, model.def, pos-id.def, rewrite.def, unk.def)
dicrc: 1
user-dic CSV: 3
CSV 总行数: 816,283
核心文件:
  NNG.csv: ~208,524 (普通名词)
  Person.csv: ~196,459 (人名)
  Hanja.csv: ~125,750 (汉字)
```

### UTF-8 编码校验
所有 CSV/DEF/dicrc/user-dic 文件必须通过 UTF-8 iconv 校验（失败数=0）。

### 固定样本文本分词比对
```
输入: 화학 이외의 것
预期输出:
  화학  NNG,*,T,화학,*,*,*,*
  이외  NNG,*,F,이외,*,*,*,*
  의    JKG,*,F,의,*,*,*,*
  것    NNB,*,T,것,*,*,*,*
  EOS
```

## 外部工具依赖

| 工具 | 用途 | 来源 |
|------|------|------|
| mecab-ko (mecab-ko) | 提供 mecab-config、mecab-dict-index、mecab CLI | archives/m/mecab-ko/0.996-ko-0.9.2 |
| mecab-dict-index | CSV → 二进制索引转换 | mecab-ko 自带 |
| mecab CLI | 样本文本分词测试 | mecab-ko 自带 |

## OHOS 适配注意事项

1. **platform recognition**: mecab-ko 的 config.guess/sub 需补丁以识别 aarch64-unknown-linux-ohos（参考 archives/m/mecab-ko/0.996-ko-0.9.2/patches/0002 和 0004）
2. **Hardcoded paths**: `tools/add-userdic.sh` 和 `seed/build.sh` 硬编码 `/usr/local/libexec/mecab`，需适配 OHOS 路径
3. **static linking**: mecab-ko 在 OHOS 上需静态链接 libmecab.a 解决动态链接问题
4. **locale**: OHOS 可能缺少 en_US.UTF-8 locale，需设置合适 locale 或使用 C.UTF-8
5. **Shell**: OHOS 默认 /bin/sh（非 bash），测试脚本需兼容

## 相关已有知识库条目

| ID | 条目 | 相关性 |
|----|------|--------|
| E023 | locale 支持不完整 | 部分相关（mecab 需要 UTF-8 locale） |
| E039 | musl iconv 不支持 //IGNORE | 间接相关（CSV 编码转换） |
| E241 | 数据/规则清单型库适配模式 | 高度相关（数据包通用模式） |

## 参考归档

- mecab: archives/m/mecab/0.996/
- mecab-ko: archives/m/mecab-ko/0.996-ko-0.9.2/
- mecab-ko-dic: archives/m/mecab-ko-dic/2.1.1-20180720/
