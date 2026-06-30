# E112 — HMDFS 大小写不敏感文件系统导致测试用例失败

## 错误特征

测试用例在 HarmonyOS 上运行 `make check` 时，涉及大小写文件名区分的测试失败：

```
Testing exclusion list: case_insensitive
--------------------------------------------------------------------
3d2
< /boo
FAIL tests/test-imagex-capture_and_apply (exit status: 1)
```

或：

```
$ touch BOO && touch boo
$ stat -c '%i' BOO boo
2305843009213756809   ← 相同 inode，文件系统大小写不敏感
2305843009213756809
```

## 触发条件

- 文件系统: HMDFS (鸿蒙分布式文件系统)
- 测试类型: 创建不同大小写文件名验证大小写区分能力的测试用例
- 典型场景: `case_insensitive` / `case_sensitive` exclusion list 测试

## 根因分析

HMDFS 是**大小写不敏感**的文件系统，与 macOS 的 APFS/HFS+ 行为一致。

- `touch BOO` 和 `touch boo` 创建的是**同一个文件**（共享 inode）
- 这与 Linux 标准 ext4/xfs（大小写敏感）行为不同
- 因此涉及大小写文件名区分的测试在 HMDFS 上必然失败

**验证命令**：
```bash
touch BOO && touch boo && stat -c '%i' BOO boo
# 相同 inode → 大小写不敏感
# 不同 inode → 大小写敏感
```

## 解决方案

### 推荐方案

像 macOS (Darwin) 一样，在测试脚本中检测 HarmonyOS 系统，跳过 `case_*sensitive` 测试用例：

```bash
case_insensitive_fs=false
if [ "$(uname -o 2>/dev/null)" = "HarmonyOS" ] || uname -a | grep -qi "HarmonyOS"; then
    case_insensitive_fs=true
fi
for t_file in "$srcdir/tests/exclusionlists"/*; do
    if $case_insensitive_fs && [[ $t_file == */case_*sensitive ]]; then
        # 跳过大小写敏感测试（HMDFS 大小写不敏感）
        continue
    fi
    exclusionlist_test "$t_file"
done
```

macOS 已有相同处理：
```bash
macOS=false
if [ "$(uname)" = Darwin ]; then
    macOS=true
fi
for t_file in ...; do
    if $macOS && [[ $t_file == */case_*sensitive ]]; then
        continue
    fi
    ...
done
```

### 禁止做法

- ❌ 不要试图修改 HMDFS 大小写敏感性 — 这是内核特性，无法通过挂载选项改变
- ❌ 不要硬编码跳过所有测试 — 只跳过明确依赖大小写文件名区分的测试

## 验证

```bash
# 1. 确认文件系统大小写不敏感
touch TEST test
stat -c '%i' TEST test
# 输出同一 inode → 确认

# 2. 验证测试跳过
make check 2>&1 | grep -i "case"
# 不应出现 case_insensitive 或 case_sensitive 测试
```

## 已知受影响软件

| 软件 | 版本 | 影响的测试 | 修复方式 |
|------|------|-----------|---------|
| wimlib | 1.14.5 | test-imagex-capture_and_apply | 同 macOS 策略跳过 case_*sensitive |

## 关联条目

- 相关: macOS 同样处理方式
- 相关: E007 (config.guess) — 平台检测
- 相关: E011 (umask 077) — HMDFS 文件系统其他差异
