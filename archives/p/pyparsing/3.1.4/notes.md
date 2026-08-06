# pyparsing 3.1.4 适配笔记

## 编译环境
- 构建系统: setuptools（纯 Python 包）
- 编译日期: 2026-07-28
- 编译器: 无（纯 Python，无需 C 扩展）
- 状态: built

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build pyparsing 3.1.4 \
  --url=https://github.com/pyparsing/pyparsing/archive/refs/tags/3.1.4.tar.gz
```

### 2. 安装依赖
```bash
# pyparsing 无外部 Conan 依赖：构建用 Conan 运行时的 python（sys.executable），
# 运行时 python3 由设备/CI 环境提供（同 cpython-tkinter 惯例）
```

### 3. 安装 pyparsing
```bash
cd $BUILD_SRC_DIR
# 注意：不要使用 --no-build-isolation。pyparsing 3.1.4 的 pyproject.toml
# 声明 flit_core 为构建后端，CI 的 HNP Python 未预装 flit_core，
# 需由 pip 自动创建隔离环境下载构建依赖。
python3 -m pip install . --prefix=$DEFAULT_PREFIX --no-deps
```

### 4. 验证
```bash
python3 -c "import pyparsing; print(pyparsing.__version__)"
# 应输出: 3.1.4
```

## 遇到的问题与解决方案

pyparsing 是纯 Python 库，使用 setuptools 构建系统，无 C 扩展，无平台特定代码，适配过程中未遇到问题。

## 源码修改

无补丁。纯 Python 库，无需修改源码。

## 依赖关系

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| （无外部 Conan 依赖） | — | — | 构建用 Conan 运行时 python（sys.executable）；运行时 python3 由设备/CI 环境提供 |
| setuptools | 系统自带 | 构建工具 | pip install 时自动使用 |

## 知识沉淀

1. **纯 Python 库适配模式**：纯 Python 库使用 setuptools/pip 安装，不需要传统 ./configure && make 流程。conanfile.py 中 build() 直接调用 `pip install` 即可。
2. **库文件类型**：pyparsing 是 library 类型（提供 Python 模块），不是命令行工具，不需要 commands.json（R38 不适用）。
3. **产物结构**：安装后产出的文件位于 `lib/python3.12/site-packages/pyparsing/` 目录下，包含 pyparsing 模块和子模块。
4. **无平台依赖**：pyparsing 全部用标准 Python 实现，无 C 扩展，无平台特定代码，可在任何支持 Python 3 的平台上运行。

## 验证结果

### 功能测试

```bash
# 模块导入
python3 -c "import pyparsing; print(pyparsing.__version__)"
# 输出: 3.1.4

# 基本解析功能
python3 -c "
from pyparsing import Word, alphas
word = Word(alphas)
print(word.parse_string('hello'))
"
# 输出: ['hello']

# DOT 语法解析
python3 -c "
from pyparsing import Word, alphas, nums, Literal, Suppress, Group
node_id = Word(alphas + '_', alphas + nums + '_')
result = node_id.parse_string('node1')
print('Node:', result[0])
"
# 输出: Node: node1
```

### 质量门禁（G0-G4）

- G0（预构建风险评估）：PASS（纯 Python，无已知风险）
- G1（配方完整性）：PASS（conanfile.py + conandata.yml + test_package/ 完整）
- G2（conan create）：PASS（从源码构建成功）
- G3（系统同名库隔离）：PASS（纯 Python，无 .so 产物）
- G4（产物完整性）：PASS

### 测试通过率

**上游 pytest 套件实际运行**（本地 python3 3.12.9 环境，`python3 -m pytest tests/`）：
- **1717 passed, 1483 subtests passed**（exit 0，耗时约 41s）
- 覆盖 test_unit / test_examples / test_simple_unit / test_diagram / json_parser_tests 全部上游用例
- 依赖：railroad-diagrams（diagram 测试所需，按 pyproject.toml 声明安装）

本地 CI 模拟验证（`CI_PACKAGES=archives/p/pyparsing/3.1.4`）：
- L0 质量门禁：7/7 通过（结构/MANIFEST/R33/R36/R37/R38/R40）
- L1 conan create：✅ 通过
- L1 smoke test：5/5（100%）
  1. 模块导入（pyparsing.__version__ == 3.1.4）✅
  2. 基础 Word 解析（Word.parse_string('hello')）✅
  3. ParseException 异常处理 ✅
  4. DOT 语法节点解析（node_id.parse_string('node1')）✅
  5. 属性键值对解析（kv_pair.parse_string('label=center')）✅
- L1e 破坏性负向测试：✅ 确认（移走 lib/ 后 import 失败，测试真实依赖包）
- L2 命令行检查：跳过（纯 Python 库，无 bin/）
- L4 安全扫描：PASS（无补丁）
- L5 产物检查：PASS（lib/ 有内容）
- **总体：L0/L1/L4/L5 全部通过，L2 跳过，exit 0**

## 交付物

| 文件 | 说明 |
|------|------|
| archives/p/pyparsing/manifest.yaml | 软件级元数据 |
| archives/p/pyparsing/README.md | 软件描述 |
| archives/p/pyparsing/3.1.4/manifest.yaml | 版本级元数据 |
| archives/p/pyparsing/3.1.4/conandata.yml | 源码声明 |
| archives/p/pyparsing/3.1.4/conanfile.py | Conan 配方 |
| archives/p/pyparsing/3.1.4/test_package/ | L1 测试 |
| archives/p/pyparsing/3.1.4/notes.md | 适配笔记 |

## 注意事项

1. **无外部 Conan 依赖**：纯 Python 库，构建用 sys.executable；R27（@user/channel 依赖格式）已废弃
2. **R32 平台兼容**：validate() 中使用 `settings.os in ("Linux", "OHOS")`
3. **R33 环境变量**：build() 使用 `sys.executable` 而非 shell 环境变量
4. **R34 实质性测试**：test_package 验证模块导入 + 基本解析功能 + DOT 语法兼容性
5. **R38 不适用**：pyparsing 是库（library），不是命令行工具，不需要 commands.json

---

**编译结束**: 2026-07-28
**最终状态**: built

---

## Finish 流程执行记录

执行时间: 2026-07-28
执行步骤:

| 步骤 | 内容 | 结果 |
|------|------|------|
| [1/9] refresh-patch --auto | 补丁生成 | ✅ 跳过（无补丁） |
| [2/9] close-archive | 归档关闭 | ✅ 通过 |
| [3/9] clean-verify 重建 | 干净构建验证 | ✅ 通过（非阻塞） |
| [4/9] conan-verify | Conan 配方验证 | ✅ 通过 |
| [5/9] W2结构+R36依赖+W3编译 | 结构检查/L0a-L0e/依赖发布/conan create → .ci-result.json | ✅ 通过 |
| [6/9] commands.json 检查 (R38) | 命令行工具声明验证 | ✅ 通过（library 类型，不需要） |
| [7/9] finalize-archive | 清理+校验+版本索引 | ✅ 通过 |
| [8/9] check-knowledge-gap | 知识完整性检查 (W5) | ✅ 通过 |
| [9/9] gen_summary + PR 原子性 | 重新生成 SUMMARY.md (W2 检查) | ✅ 通过 |

### 关键验证

- **W2 结构完整性**: test_package/ ✓, conanfile.py ✓, conandata.yml ✓, MANIFEST.yml ✓
- **R36 依赖发布**: 无外部 Conan 依赖（无需发布）✅
- **W3 conan create**: 本地编译验证通过 ✅
- **R38**: pyparsing 是 library 类型，不需要 commands.json ✅
- **状态**: built（待 CI merge + upload 后标记 published）
- **published_as**: pyparsing/3.1.4@ohpcd/stable

**最终状态**: built
