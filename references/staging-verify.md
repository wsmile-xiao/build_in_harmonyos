> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# Staging 目录验证

来源: SKILL.md §2.8

---

> **目的**：验证 $TEST_PREFIX 中的安装产物完整且功能正常。
> **时机**：`make install` 到 $TEST_PREFIX 成功之后、ohc-run.py package 之前。
>
> **重要变化（v4.3）**：由于 configure --prefix 现在直接指向隔离的 $TEST_PREFIX，
> **不再需要"重新解压+二次编译"**。本步骤变为轻量级的产物验证。

## 验证内容

```bash
echo "[Staging 验证] 检查 $TEST_PREFIX 安装产物..."

# 1. 文件完整性
BIN_COUNT=$(find "$TEST_PREFIX/bin" -type f 2>/dev/null | wc -l | tr -d ' ')
LIB_COUNT=$(find "$TEST_PREFIX/lib" -type f 2>/dev/null | wc -l | tr -d ' ')
echo "  二进制: ${BIN_COUNT}, 库文件: ${LIB_COUNT}"

if [ "$BIN_COUNT" -eq 0 ]; then
    echo "[FAIL] staging 目录为空！"
    exit 1
fi

# 2. 功能回归测试（使用 $TEST_PREFIX 环境）
export PATH="$TEST_PREFIX/bin:${PATH}"
export LD_LIBRARY_PATH="$TEST_PREFIX/lib:${LD_LIBRARY_PATH:-}"

PASS=0; FAIL=0
for cmd in "$TEST_PREFIX/bin"/*; do
    [ -x "$cmd" ] || continue
    name=$(basename "$cmd")
    output=$("$cmd" --version 2>&1 | head -1)
    if [ -n "$output" ]; then
        PASS=$((PASS+1))
    else
        FAIL=$((FAIL+1))
        echo "  ❌ $name"
    fi
done
echo "  结果: ${PASS} 通过 / ${FAIL} 失败"

# 3. 恢复环境
export PATH="${PATH#$TEST_PREFIX/bin:}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH#$TEST_PREFIX/lib:}"
```

## 判定标准

| 结果 | 条件 | 后续 |
|------|------|------|
| **PASS** | BIN_COUNT > 0 + FAIL=0 | → 创建 `.staging-verified` 标记 → make check → package |
| **PARTIAL** | BIN_COUNT > 0 + 少量 FAIL（平台限制） | → 记录原因，继续 |
| **FAIL** | BIN_COUNT=0 或大量 FAIL | → 排查 configure/install，修复后重试 |

> **PASS 后必须创建标记文件**（ohc-run.py finish 关卡 B 检查此文件）：
> ```bash
> touch "${BUILD_ARCHIVE_DIR}/.staging-verified"
> ```
