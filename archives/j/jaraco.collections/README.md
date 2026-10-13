# jaraco.collections

## 软件描述
`jaraco.collections` 是一组**集合模型（collections models）**：为 Python 标准库的容器类型补上常用的语义化包装与适配器。纯 Python（无编译），MIT 许可。

## 功能概述
| 类/函数 | 作用 |
|---|---|
| `Projection` / `Mask` | 把函数施加在 Mapping 的值/键上而不复制数据 |
| `RangeMap` / `WeightedLookup` | 以区间为键的映射（按值反查区间） |
| `KeyTransformingDict` | 在读写时自动变换键的 dict 基类 |
| `FoldedCaseKeyedDict` | 键大小写折叠的 dict（**内部调用 `jaraco.text.FoldedCase`**） |
| `DictStack` / `IdentityOverrideMap` | 多层字典叠加视图 |
| `BijectiveMap` / `Enumeration` | 双向映射与枚举 |
| `FrozenDict` | 不可变且可哈希的 Mapping |
| `FreezableDefaultDict` / `Accumulator` / `Least` / `Greatest` | 冻结默认字典、累加器与极值 |
| `dict_map` / `invert_map` / `sorted_items` / `pop_all` | 常用字典工具函数 |

## OHOS 适配

### 打包方式
- **纯 Python 模块包**：沿用仓库同族范式（`archives/m/more-itertools`）——`package_type=application`，模块装到 `lib/python3/site-packages`
- **无编译**：`source()` 取 PyPI sdist，`package()` 直接拷贝模块树

### 关键攻坚点
1. **运行期依赖必须在导入期就位**：本库在 `__init__.py` 顶部 `import jaraco.text`（并在 `FoldedCaseKeyedDict` 里用 `jaraco.text.FoldedCase`）——不是可选依赖，删不掉
2. **该依赖在制品仓不存在**：`jaraco.text` / `jaraco.functools` / `jaraco.context` 两种拼写 × 多版本 `conan install` 实测均 `Unable to find`，`archives/` 下亦无
3. **处置：包内捆绑这 3 个纯 Python 小模块**（各 URL+sha256 钉死），已发布的 `more-itertools/11.1.0` 仍走 Conan requires；**R36 张力与替代路线在 notes/PR 中如实披露**（更彻底做法是先发布这 3 个配方再声明 requires）
4. **命名空间合并**：`jaraco` 是 PEP 420 命名空间包 → 本体与捆绑依赖各装各自的 `jaraco/<mod>` 目录即可自然合并，无需 `__init__.py`
5. **上游 pytest 真跑**：`build()` 内跑 `python3 -m pytest -q tests`，按 `passed/failed/errors` 统计；出现 `ModuleNotFoundError`/`ImportError` 或解析不到通过计数均判不成立（不把"没真跑"记成通过）

### 与 Linux 的差异
- 纯 Python，无平台相关代码路径 → 差异集中在**依赖来源**（制品仓缺 3 个 jaraco.* 模块 → 随包捆绑）与**打包路径**（`lib/python3/site-packages`）
- 消费者校验里 `FoldedCaseKeyedDict` 一项同时验证了"捆绑依赖真被使用"与"命名空间合并成功"

## 依赖关系
- **Conan requires**：`more-itertools/11.1.0`（已合入）
- **包内捆绑**：`jaraco.text 4.3.0`、`jaraco.functools 4.6.0`、`jaraco.context 6.1.2`（均为纯 Python；`jaraco.context` 仅在 Python < 3.12 时需要 `backports.tarfile`，本环境 3.12 不需要）
- 上游声明的其它 extras（`pytest-checkdocs`/`sphinx` 等）只用于开发与文档，未引入

## 版本记录
| 版本 | 状态 | 打包日期 | 备注 |
|------|------|---------|------|
| 5.1.0 | built | 2026-10-07 | 纯 Python 模块包 + 3 个未发布依赖包内捆绑（已披露） |

## 参考资料
- 上游仓库: https://github.com/jaraco/jaraco.collections
- PyPI: https://pypi.org/project/jaraco.collections/
