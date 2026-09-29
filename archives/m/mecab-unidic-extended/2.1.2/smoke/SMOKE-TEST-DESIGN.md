# mecab-unidic-extended 2.1.2 Smoke Test Design

## 前置条件
- mecab/0.996 conan 包已安装（bin/mecab 可执行、libexec/mecab/mecab-dict-index）
- 本词典包已构建（res/unidic 下含 char.bin, matrix.bin, sys.dic, unk.dic, dicrc）
- HarmonyOS 无系统 mecabrc（/usr/local/etc/mecabrc 不存在），必须用 `-r` 显式指定空 rcfile
- 词典目录自带 dicrc（unidic 8 列输出格式，含 aType アクセント列）

## 固定样本文本
すもももももももものうち

## 预期输出
7 个形态素 + EOS，unidic 8 列格式（表層, pron, lForm, lemma, pos1-pos4, cType, cForm, aType）。
字节级 golden 见 golden/mecab-unidic-extended-golden.txt。
注意：助词行（も/の）行尾为 3 个空字段（cType/cForm/aType 均为空，即行尾制表符），
名词/形容词行 aType 列为 0。

## smoke 测试步骤

### 1. 词典文件存在性
```bash
dicdir="<package_folder>/res/unidic"   # conan cache path 查询，或 source conanrun.sh 后用 $UNIDIC_EXT_DICDIR
for f in char.bin matrix.bin sys.dic unk.dic dicrc; do
    [ -s "$dicdir/$f" ] && echo "$f OK" || echo "$f MISSING"
done
```

### 2. mecab 可执行与词典信息验证
```bash
mecab --version          # mecab of 0.996
: > /tmp/empty-mecabrc
mecab -D -d "$dicdir" -r /tmp/empty-mecabrc | head -5   # sys.dic charset: utf-8 等
```

### 3. 固定样本输出比对（核心）
```bash
echo "すもももももももものうち" | mecab -d "$dicdir" -r /tmp/empty-mecabrc > /tmp/unidic-ext-smoke.txt
diff /tmp/unidic-ext-smoke.txt golden/mecab-unidic-extended-golden.txt && echo "SMOKE PASS"
```

### 4. UNIDIC_EXT_DICDIR 环境变量（包的 conanrun 契约）
```bash
. conanrun.sh
test -n "$UNIDIC_EXT_DICDIR" && echo "UNIDIC_EXT_DICDIR OK: $UNIDIC_EXT_DICDIR"
mecab -d "$UNIDIC_EXT_DICDIR" -r /tmp/empty-mecabrc <<< "すもももももももものうち"
```

## golden 文件存放路径
archives/m/mecab-unidic-extended/2.1.2/smoke/golden/mecab-unidic-extended-golden.txt

## 当前状态 (2026-09-23)
- [x] 固定样本与 golden 已从真机构建捕获（mecab-dict-index 生成索引 + libmecab 消费，
      机制与 test_package 完全一致：`mecab_new2("-d <dicdir> -r <空rcfile>")`）
- [x] golden 字节级保存（8 行，含行尾空字段制表符）
- [ ] 包级 smoke（步骤 1-3 对 conan 包产物执行）— 随 conan create / test_package 验证后勾选
