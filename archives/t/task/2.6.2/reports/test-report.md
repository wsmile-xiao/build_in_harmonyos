# task 2.6.2 测试报告

**测试日期**: 2026-08-25
**测试环境**: OpenHarmony PC aarch64, Clang 15, Conan 2.29.1
**上游版本**: Taskwarrior 2.6.2

## 上游测试边界

Taskwarrior 2.6.2 源码包含 shell-based 测试套件 (`test/*.t`)，但这些测试需要完整的 test harness 环境且通过 `make check` 运行，不属于 Conan 构建系统的一部分。Conan 配方中的 `test_package` 覆盖了核心功能验证。

## Conan 构建验证

| 项目 | 结果 |
|------|------|
| `conan create` 构建编译 | 通过 |
| `task` 可执行文件打包 | 通过 |
| G0 预构建风险评估 | 通过 |
| G1 配方完整性 | 通过 |
| G2 conan create (干净构建) | 通过 |
| G3 系统同名库隔离 (R26) | 通过 |
| G4 产物完整性 | 通过 |
| L2 smoke test | 通过 |
| L4 安全扫描 | 通过 |
| L5 产物基线 | 通过 |
| W3 本地 CI 模拟 | 通过 |

验证命令：

```bash
python3 ohc-run.py conan-verify task 2.6.2
python3 ohc-run.py finish task 2.6.2 built
```

## 适配后消费侧测试 (test_package)

`test_package/conanfile.py` 在 Conan 运行环境中真实执行打包产物，验证 Taskwarrior 核心功能。

### 用例 1: 版本检查

| 项目 | 内容 |
|------|------|
| 命令 | `task --version` |
| 断言 | 输出 `2.6.2` |
| 结果 | 通过 |

### 用例 2: 任务添加

| 项目 | 内容 |
|------|------|
| 命令 | `task add "Conan test task"` |
| 断言 | 输出 `Created task 1.` |
| 结果 | 通过 |

### 用例 3: 任务列表

| 项目 | 内容 |
|------|------|
| 命令 | `task list` |
| 断言 | 输出包含任务描述和 `1 task` |
| 结果 | 通过 |

### 用例 4: 完成任务

| 项目 | 内容 |
|------|------|
| 命令 | `task 1 done` |
| 断言 | 输出 `Completed task 1` |
| 结果 | 通过 |

### 用例 5: 空列表

| 项目 | 内容 |
|------|------|
| 命令 | `task list` |
| 断言 | 输出 `No matches.` (exit code 1, 预期行为) |
| 结果 | 通过 |

## 已知限制

- **ENABLE_SYNC=OFF**: 同步功能已禁用，因为 GnuTLS 及其依赖链 (nettle, libtasn1, libgcrypt, libgpg-error 等) 尚未在 Conan 制品仓中适配发布。这是历史遗留问题，非本次适配引入的裁剪。待 GnuTLS 依赖链适配完成后可启用。
- **libshared 子模块**: 从 GitHub commit 072e0e0 独立下载，不在主 tarball 中。
