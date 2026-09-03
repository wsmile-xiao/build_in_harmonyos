# W4 Pre-PR 独立审计 — 子任务 Prompt 模板

> **此模板用于 createSubTask 的 objective 参数。**
> 每次适配完成后、创建 PR 之前，必须执行此审计。

## 审计目标

对本次 Conan 配方变更进行独立代码审计，确保：
1. 无欺骗性行为 (R34/R9/R8/R19/R40/R52)
2. conanfile.py 配方质量达标 (R26/R32/R33/R37/R38)
3. 文件规范合规 (conandata.yml/patches/test_package)
4. PR 原子性 (W2)

## 审计输入

审计输入文件由 `pre_pr_audit.py generate` 生成，JSON 格式包含：
- `rules.code_style` — 代码规范性标准全文
- `rules.review_memory` — PR 审查规则全文
- `changed_files` — 变更文件列表
- `file_contents` — 每个变更文件的完整内容
- `diff_stat` — diff 统计

## 审计流程

0. **先读门禁阻断性分级表**（防止把非阻断项误判为 P1 引发返工，ki18n PR #7155 教训）：

   | 门禁/检查项 | 阻断性 | 审计处置 |
   |---|---|---|
   | R34/R9/R8/R19/R40 欺骗类 | **阻断（P0/P1）** | 命中即 verdict=fail |
   | L0 结构性门禁（test 源缺失/MANIFEST 缺失/草稿泄漏） | **阻断（P1）** | verdict=fail |
   | L4 安全扫描 warn（补丁含危险函数但已声明） | 非阻断 | 记 P2/P3，不阻断 |
   | L5 存量遥测（已发布包基线差异等历史遗留） | **非阻断** | 记 P2 观察项，注明"存量遥测不阻断发布"，不判 P1 |
   | conandata 含 `file://` 本地路径 | **阻断（P0）** | W3 改写未还原，要求还原官方 URL 后重审 |
   | preflight PF7/PF8/PF9（源URL/配方静态/分支路径） | **阻断（P1）** | verdict=fail——与 CI L0n/L0p/L0m/R39/R38 同口径 |
   | R51 上游测试三步法（清点/运行/如实回填） | **阻断（P1）** | 申报与清点证据不符或占位符申报 → verdict=fail |
   | W4 审计自身的提示/风格建议 | 非阻断 | 标注 `suggestion`（无规则出处），允许作者合理拒绝；有规则出处的标注 `rule_ref` |

1. 读取审计输入 JSON 文件
2. 逐条加载 `rules.review_memory` 中的审查规则：
   - **类别一 (欺骗检测)**: 逐条检查 R34/R9/R8/R19/R40，任何一条命中 = verdict=fail
   - **类别二 (配方质量)**: 检查 R26/R32/R33/R37/R38/R39，P1 问题 = verdict=fail
   - **类别三 (文件规范)**: 检查归档结构/补丁规范/PR禁止文件
   - **类别四 (PR合规)**: 检查 W2 原子性/文件权限边界
3. 逐条加载 `rules.code_style` 中的代码规范：
   - conanfile.py: shebang/docstring/类名/方法顺序/package_info
   - test_package: 文件名/main函数/API调用
   - conandata.yml: HTTPS/sha256/缩进
   - 补丁: 文件名格式/patch_description/patch_type
4. 输出审计报告

## 输出格式

审计报告必须为 JSON，保存到 `/tmp/audit-result-{branch}.json`：

```json
{
  "verdict": "pass",
  "issues": [
    {
      "severity": "P0",
      "rule_id": "R34",
      "file": "archives/s/sqlite3/3.49.1/test_package/test.c",
      "line": 15,
      "description": "问题描述",
      "fix_suggestion": "修复建议"
    }
  ],
  "summary": "审计总结"
}
```

## 严重程度

| 级别 | 含义 | 处理 |
|------|------|------|
| P0 | 欺骗性行为 (空壳测试/伪造状态/伪造sha256/#ifdef __OHOS__/-D__OHOS__ 注入/replace 注入/手动打包/审计文件与实际矛盾) | 一律 fail，禁止提PR |
| P1 | 配方正确性 (硬编码编译器/平台兼容/版本号/commands.json缺失) | 必须 fail，修复后重新审计 |
| P2 | 代码规范 (命名/格式/import顺序) | 警告，建议修复 |
| P3 | 建议性改进 | 提示，不阻塞 |

## 判定规则

- `verdict=pass` 且 P0=0 且 P1=0 → ✅ 审计通过，可以提PR
- `verdict=fail` 或 P0>0 或 P1>0 → ❌ 审计未通过，必须修复后重新审计
- P2/P3 不阻塞提PR，但建议在后续迭代中处理
