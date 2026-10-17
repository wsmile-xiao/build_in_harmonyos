# mecab-ko-dic - 韩语形态分析词典数据

## 软件简介
mecab-ko-dic 是 MeCab 韩语版（mecab-ko）的词典数据包，包含韩语形态分析所需的词典文件（CSV 词典、定义文件、配置文件）。通过 mecab-dict-index 工具可编译为二进制索引文件供 mecab 运行时使用。

- **官方网站**: https://bitbucket.org/eunjeon/mecab-ko-dic
- **构建系统**: 无（数据包，可选 mecab-dict-index 生成二进制索引）
- **数据类型**: NLP 词典数据（非 C/C++ 编译）
- **许可证**: Apache-2.0

## 功能特性
- 韩语形态分析词典（40 个 CSV 文件，816,283 条目）
- 词典定义文件（9 个 DEF 文件：char.def, pos-id.def 等）
- 配置文件 dicrc
- 可选二进制索引生成（char.bin, matrix.bin, model.bin, sys.dic, unk.dic）

## 版本历史

### 2.1.1-20180720 (2026-07-28)
- **状态**: built
- **编译平台**: HarmonyOS (aarch64-unknown-linux-ohos)
- **数据统计**: 40 CSV, 9 DEF, dicrc, 816,283 条目
- **UTF-8 编码校验**: 全部通过
- **外部依赖**: mecab-ko (mecab-dict-index) 来自 archives/m/mecab-ko/0.996-ko-0.9.2
- **注意事项**:
  - 纯词典数据包，无 C/C++ 编译
  - settings = None（平台无关）
  - 二进制索引文件由 mecab-dict-index 外部生成，源码为 CSV/DEF/dicrc

## 使用方法
```bash
# 安装词典
conan install --requires=mecab-ko-dic/2.1.1-20180720

# 使用词典（需配合 mecab-ko）
mecab -d <dic_dir>
```
