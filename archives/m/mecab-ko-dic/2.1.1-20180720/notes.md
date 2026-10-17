mecab-ko-dic 2.1.1-20180720 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-28

## 数据统计
- CSV 文件: 40
- DEF 文件: 9（char.def, feature.def, left-id.def, right-id.def, matrix.def, model.def, pos-id.def, rewrite.def, unk.def）
- dicrc: 1
- CSV 总行数: 816,283
- 二进制索引文件: char.bin, matrix.bin, model.bin, sys.dic, unk.dic

## 外部工具依赖
- mecab-ko (mecab-config, mecab-dict-index, mecab CLI): 来自 archives/m/mecab-ko/0.996-ko-0.9.2（已合入 main #3514）

## 验证结果
- conan create: PASS
- conan-verify: PASS
- test_package: ALL PASSED (data integrity + UTF-8 validation)
- 上游测试 seed/test/test.sh: **1/1（100%）**——29 句输入 diff 零差异，exit 0
- 固定样本 `화학 이외의 것` 分词输出精确匹配 golden

## 已知限制
- mecab-ko 作为外部工具需要单独安装, 源码不混入本 PR
- 二进制索引由 mecab-dict-index 生成, 上游 source 为 CSV/DEF/dicrc
---

**编译结束**: 2026-07-31 11:56
**最终状态**: built
