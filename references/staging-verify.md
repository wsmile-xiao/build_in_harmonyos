> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# Staging 目录验证

来源: SKILL.md §2.8

---

> **目的**：验证 `$TEST_PREFIX/$DEFAULT_PREFIX/` 中的安装产物完整且功能正常。
> **时机**：`make install DESTDIR=$TEST_PREFIX` 成功之后、ohc-run.py package 之前。
>
> DESTDIR 模式下，`configure --prefix=$DEFAULT_PREFIX`，`make install DESTDIR=$TEST_PREFIX` 将文件安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/`。

## G0: 干净构建验证（补丁自包含性检查）

> **目的**：验证补丁集 + hints/configure 参数足以让构建从零完成，无需任何人工介入。
> **时机**：refresh-patch 之后、verify-build (G1-G4) 之前。
> **执行者**：`ohc-run.py clean-verify`（脚本自动执行，finish Step 3 前置关卡）。

### 验证步骤

```bash
# G0 由 ohc-run.py clean-verify 自动执行：
# 1. 解压原始 tarball 到临时目录
# 2. 应用所有 patches/*.patch
# 3. 运行 ./configure（使用 manifest 中的 configure_options + hints）
# 4. make -j1
# 5. make install DESTDIR=...
# 6. 检查是否有二进制产物
# 7. 清理临时目录
```

### 结果判定

| 结果 | 条件 | 后续 |
|------|------|------|
| **PASS** | configure + make + make install 全部无人工介入完成 | → G1-G4 质量门禁 |
| **FAIL** | 任何步骤失败或需要人工介入 | → 输出 HANDOFF 块，AI 修复后重新验证 |

### HANDOFF 格式（脚本 → AI）

```
╔═══ G0 HANDOFF ══════════════════════════════════╗
║ G0_CHECK: clean-build-verify                    ║
║ RESULT: FAIL                                     ║
║ FAILED_STEP: configure|make|make_install         ║
║ ERROR_LOG: <日志路径>                             ║
║ PATCHES_APPLIED: N/N                             ║
║ AI NEXT ACTIONS:                                 ║
║   1. 读取错误日志，诊断根因                        ║
║   2. 修复补丁或 hints                            ║
║   3. 重新运行 ohc-run.py clean-verify            ║
╚══════════════════════════════════════════════════╝
```

### 设计理念

此步骤解决的核心问题：Phase 3 编译过程中，AI 可能通过手动操作（直接改 config.sh、手动运行编译命令、手动 cp/mv 文件等）绕过了问题，但这些手动操作没有被固化为补丁或构建规则。G0 通过从干净源码重建来暴露这些遗漏。

典型遗漏场景：
- 手动修改了 config.sh 但没有通过 Configure -D 参数或 hints 文件替代
- 手动编译了某个 .o 文件但没有修复 Makefile 规则
- 手动运行了辅助脚本但没有集成进 Makefile
- 补丁遗漏了某个必要的源码修改

---

## 验证内容（Staging 产物检查，G1-G4 前置）

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

> **标记文件说明**：`.staging-verified` 是编译流程的运行时状态标记，由 `.gitignore` 管理且不提交到仓库。它作为 `ohc-run.py finish` 关卡的前置检查，但**不作为归档必检项**（归档完整性由 finalize-archive 校验）。同类标记文件还包括 `.g0-verified`、`.verify-passed`、`.knowledge-done` 等，均属运行时状态，在 `.gitignore` 中统一管理。
> 
> ```bash
> # 创建标记（脚本自动执行）
> touch "${BUILD_ARCHIVE_DIR}/.staging-verified"
> ```
