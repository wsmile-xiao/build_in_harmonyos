# E335 — Conan test() 每次运行在 test_package 再生构建/测试残留，交付前必须清理

## 错误特征

Conan test()/`conan create` 在 test_package/ 目录生成构建/测试残留，交付或评审时可见，典型残留文件：

```
mlton-consumer
__pycache__/
conanbuild.sh
conanrun.sh
conanbuildenv-release-armv8.sh
conanrunenv-release-armv8.sh
deactivate_conanbuild.sh
deactivate_conanrun.sh
deactivate_conanrunenv-*.sh
metadata/
```

残留使 test_package 非 pristine，web-review 以 REVISE B1/B2 检出。

## 触发条件

- Conan 2.x 的 `test()`/`conan create` 在 test_package/ 目录生成 CMake/环境脚本与运行残留（mlton-consumer 测试 ELF、`__pycache__/`、`conanbuild.sh`、`conanrun.sh`、`conanbuildenv-*`、`conanrunenv-*`、`deactivate_*`、`metadata/` 等）；
- 每次 CI/本地运行都会重新生成这些文件；
- 交付、commit、评审（REVISE）环节未清理即混入脏产物。

## 根因分析

Conan 2.x 的 `test()`/`conan create` 在 test_package/ 目录生成 CMake/环境脚本与运行残留：mlton-consumer（测试 ELF 二进制）、`__pycache__/`、`conanbuild.sh`、`conanrun.sh`、`conanbuildenv-release-armv8.sh`、`conanrunenv-release-armv8.sh`、`deactivate_conanbuild.sh`、`deactivate_conanrun.sh`、`deactivate_conanrunenv-*.sh`、`metadata/` 等。这些文件不属于配方输入，每次 CI/本地运行都会重新生成；若直接 commit/push 会把脏产物混入仓库（MLton Round 18 web-review 即以 REVISE B1/B2 检出）。交付前必须清理使 test_package 保持 pristine（仅配方输入），并以 KEEP-OK 清单 + RESIDUAL-CLEAN 校验留证。

## 解决方案

### 推荐方案

交付/commit 前对 test_package 做残留清理：删除运行时生成的二进制（如 mlton-consumer）、`__pycache__/`、`conanbuild.sh`/`conanrun.sh`/`conanbuildenv-*`/`conanrunenv-*`/`deactivate_*` 脚本与 `metadata/`，仅保留配方输入（MANIFEST.yml、conanfile.py、测试源、测试脚本），并以 KEEP-OK 清单（5/5）+ 残留校验（10/10 RESIDUAL-CLEAN）留证；CI 之后再次清理并留证，保证提交态与产物态一致。

```bash
rm -rf mlton-consumer __pycache__ conanbuild.sh conanrun.sh \
  conanbuildenv-release-armv8.sh conanrunenv-release-armv8.sh \
  deactivate_conanbuild.sh deactivate_conanrun.sh \
  deactivate_conanrunenv-release-armv8.sh metadata
ls            # 仅剩配方输入
git status    # 确认 test_package 干净
```

### 回退方案

将残留模式加入 `.gitignore` 作为兜底防止误入 commit；但 `.gitignore` 不能证明 source 零污染，仍需交付前清理并留证。

### 禁止做法 ❌

- 禁止残留文件 commit / `git add mlton-consumer` / `git add __pycache__`——提交脏产物违反交付卫生，web-review 会判 blocker，评审 REVISE 打回，交付延迟。
- 禁止只清理不校验、清理后不核对清单——清理后必须核验仅剩配方输入，避免漏清或误删配方输入，否则再次 CI 后残留复发，交付仍带脏文件。

## 验证

```bash
find test_package -maxdepth 2          # 列出全部文件，对照配方输入清单
grep -rl "mlton-consumer\|__pycache__\|conanbuild.sh" test_package
# 应无输出
git status                             # 确认 test_package 无未跟踪残留
```

MLton 20241230 Round 18 web-review REVISE B1/B2 检出残留后清理，仅剩 5 个配方输入（KEEP-OK 5/5、RESIDUAL-CLEAN 10/10），CI 后再清理并留证，Round 18 CI PASS。

## 关联条目

- 原则：P005
- 状态：draft
- 正式文档：doc/E335.md
- 相似条目：DRAFT-polyml-test-package-source-integrity（test_package source 零污染）——同类交付卫生问题
- 事件源：MLton 20241230 Round 18 web-review REVISE B1/B2 检出 test_package 混入 mlton-consumer、__pycache__、conanbuild.sh、conanrun.sh、conanbuildenv-*、deactivate_*、metadata/ 残留；清理后仅剩 5 个配方输入（KEEP-OK 5/5、RESIDUAL-CLEAN 10/10），CI 后再清理并留证，Round 18 CI PASS

---
*draft/E335-draft-MLTN.md · knowledge graph draft · MLTN*
