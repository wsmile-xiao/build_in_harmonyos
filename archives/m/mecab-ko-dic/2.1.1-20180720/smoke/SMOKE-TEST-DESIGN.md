# mecab-ko-dic 2.1.1-20180720 Smoke Test Design

## 前置条件
- mecab-ko 已安装 (mecab-config, mecab-dict-index, mecab 可执行)
- 本词典已构建 (make 生成 model.bin, matrix.bin, char.bin, sys.dic, unk.dic)
- rcfile 指向正确 dicdir

## 固定样本文本
화학 이외의 것

## 预期输出 (从 upstream seed/test/expected_output.txt 提取)
화학	NNG,*,T,화학,*,*,*,*
이외	NNG,*,F,이외,*,*,*,*
의	JKG,*,F,의,*,*,*,*
것	NNB,*,T,것,*,*,*,*
EOS

## smoke 测试步骤

### 1. rcfile dicdir 验证
```bash
mecab -D | grep dicdir
# 应指向已构建的词典目录
```

### 2. mecab 可执行验证
```bash
mecab --version
mecab -d <dicdir> --help
```

### 3. 固定样本输出比对
```bash
echo "화학 이외의 것" | mecab -d <dicdir> > /tmp/mecab-test-output.txt
diff /tmp/mecab-test-output.txt golden/mecab-ko-dic-golden.txt && echo "PASS"
```

### 4. 生成词典文件存在性
```bash
for f in model.bin matrix.bin char.bin sys.dic unk.dic; do
    [ -s "$dicdir/$f" ] && echo "$f OK" || echo "$f MISSING"
done
```

## golden 文件存放路径
archives/m/mecab-ko-dic/2.1.1-20180720/smoke/golden/mecab-ko-dic-golden.txt

## 当前状态 (2026-07-28)
- [x] 样本文本已确认
- [x] 预期输出已从 upstream seed/test/expected_output.txt 提取
- [ ] mecab-ko 工具不可用，暂无法执行实际测试
- [ ] golden 文件待 mecab-ko 安装后生成
