# mecab-unidic-extended - 日语 UniDic 词典（kana-accent 变体）+ 预编译 MeCab 索引

## 软件简介
mecab-unidic-extended 打包 UniDic 2.1.2 kana-accent（仮名アクセント付き）词典：
包含 MeCab 可直接加载的预编译二进制索引（res/unidic）与原始 UTF-8 源数据
（res/unidic-src，用于复现/重索引）。与 mecab-ipadic / mecab-ko-dic（纯源数据包）
不同，本包在构建期通过 tool_requires mecab/0.996 的 mecab-dict-index 将
756,463 条目的 lex.csv 与 5981x5981 的 matrix.def 编译为二进制索引
（sys.dic ~179MB, matrix.bin ~68MB）。

- **官方网站**: https://clrd.ninjal.ac.jp/unidic/
- **构建系统**: 无（词典数据 + mecab-dict-index 索引编译）
- **数据类型**: NLP 词典数据（非本包 C/C++ 编译）
- **许可证**: GPL-2.0-or-later, LGPL-2.1-or-later, BSD-3-Clause

## 功能特性
- UniDic 2.1.2 kana-accent 词典（lex.csv 756,463 条目，UTF-8）
- 5981x5981 连接代价矩阵 matrix.def
- 预编译二进制索引: char.bin, matrix.bin, sys.dic, unk.dic（+ dicrc）
- 8 列 unidic 输出格式（表層,pron,lForm,lemma,pos,cType,cForm,aType，含重音列）
- 原始源数据随包分发（res/unidic-src）用于复现/重索引

## 版本历史

### 2.1.2 (2026-09-23)
- **状态**: built
- **编译平台**: HarmonyOS PC (aarch64-unknown-linux-ohos)
- **数据统计**: lex.csv 756,463 条目; matrix.def 5981x5981; 6 DEF 文件 + dicrc
- **索引体积**: sys.dic 187,716,561 B; matrix.bin 71,544,726 B; char.bin 262,496 B; unk.dic 5,492 B
- **外部依赖**: mecab/0.996 (tool_requires, mecab-dict-index)
- **注意事项**:
  - 上游 zip 无 pos-id.def/model.def，mecab-dict-index 回退最小 pos-id 表（可用）
  - mecab-dict-index 不复制 dicrc 到输出目录，recipe 手动补齐
  - HarmonyOS 无系统 mecabrc，消费者须 `-d <dicdir> -r <rcfile>` 显式指定

## 使用方法
```bash
# 安装词典
conan install --requires=mecab-unidic-extended/2.1.2

# 加载词典（HarmonyOS 无系统 mecabrc，须 -r 指定空 rcfile）
. conanrun.sh    # 导出 UNIDIC_EXT_DICDIR
: > /tmp/empty-mecabrc
mecab -d "$UNIDIC_EXT_DICDIR" -r /tmp/empty-mecabrc
```

C/C++ API（消费者测试同款机制）:
```cpp
mecab_t *m = mecab_new2(("-d " + dicdir + " -r " + rcfile).c_str());
const char *out = mecab_sparse_tostr(m, "すもももももももものうち");
```
