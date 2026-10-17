# Conan 2.29 的 Requirement 没有 `name` 属性：遍历 `self.dependencies.items()` 用键取 `.name` 定位被测包，会在任何断言跑起来之前就抛 AttributeError

- **包/版本**：prank 250331（机制与 prank 本身无关，任何配方或 `test_package` 里遍历依赖并"用键认包"的写法都吃这一条）
- **判定**：路径 B / create
- **关联 Issue**：#3467
- **实测环境**：HarmonyOS PC（aarch64）A 机真机，Conan 2.29.1

## 症状

`test_package/conanfile.py` 里按"遍历依赖找被测包"的直觉写法：

```python
for ref, dep in self.dependencies.items():
    if ref.name == "prank":          # ← 抛在这里，此时任何断言都还没开始跑
        bindir = ...
```

G2（test_package）直接红，日志形态是"消费者测试没跑起来 / 脚本异常"，
而被测二进制、依赖、配方主体全都是好的。

## 一手取证（零构建，10 秒可复现）

```
$ python3 -c "import conan; print(conan.__version__)"
2.29.1

$ python3 -c "
from conan.internal.model.requires import Requirement
r = Requirement('zlib/1.3.1')
print('has_name=', hasattr(r, 'name'))
print('public=', sorted(a for a in dir(r) if not a.startswith('_')))
"
has_name= False
public= ['aggregate', 'alias', 'build', 'consistent', 'consistent_policy_new', 'copy_requirement',
 'deduce_package_id_mode', 'defining_require', 'direct', 'files', 'force', 'headers', 'is_test',
 'libs', 'no_skip', 'options', 'override', 'override_ref', 'overriden_ref', 'package_id_mode',
 'process_package_type', 'ref', 'required_nodes', 'run', 'serialize', 'skip', 'test',
 'transform_downstream', 'transitive_headers', 'transitive_libs', 'version_range', 'visible']
```

⇒ `Requirement` 的公开面里**没有** `name`；包名在 `ref.name`（以及 `pkg_name`）之下。
`self.dependencies` 又是一个以 `Requirement` 对象为键的映射，所以"拿循环键的 `.name`"这条路在 2.29 上是死的。

## 为什么这条容易把人带偏

失败点发生在 `test()` 组装命令之前，所以**看起来像消费者测试自身的毛病**。此时最省事的三种"修法"——
放宽断言数、砍场景数、把 `test_package` 改成只打印/只查文件——**全都是缩分母**，属硬禁，
而且改完 G2 还会红（因为异常在断言之前的取属性那一步）。真问题只有一个：**依赖定位方式**。

## 正解（本包 conan create 内真跑通过）

按包名直查，不去迭代键：

```python
prank = self.dependencies["prank"]                       # 字符串键走 pkg_name 匹配
bindir = os.path.join(prank.package_folder, prank.cpp_info.bindirs[0])
```

这也是本仓主流写法（`archives/a/abcde`、`archives/a/aaudit` 等大量在库配方同一形状）。
被测引用本身仍按交付门禁 §9 优先用 `self.tested_reference_str` 定位，
⛔ 把"被测包"和"其它依赖"混在一个循环里猜名字。

修好后本包实测（`archives/p/prank/250331/reports/conan-create.log`）：

```
:130  HMBS_TEST_PACKAGE_RESULT={… "passed": true, "passedCount": 37}
:131  prank/250331@ohpcd/stable (test package): consumer MSA harness: 37/37 assertions passed
```

## 适用范围与不适用

- **适用**：任何对 `self.dependencies` 做 `items()` 迭代**并且使用循环键**取包名的地方（`build()`、`package_info()`、`test_package/conanfile.py` 都可能）。
- **不适用**：只取 value、忽略键的循环——例如本仓 E499 的
  `for _ref, dependency in self.dependencies.items(): … dependency.cpp_info.libdirs …`，
  迭代形状相同但不碰键，**不受影响**，别照本条去"修"它。
- **不适用**：Conan 1.x 的依赖模型不同；本条只针对 2.x（实测 2.29.1）。
- **不适用**：报错来自 value（依赖对象）而不是键的情形——那是另一类 API 问题。

## 自查

```bash
# 命中后再逐条看那 1–2 行里有没有对循环键取 .name；⛔ 命中 items() 就当缺陷
grep -rn "dependencies\.items()" archives/<字母>/<包>/<版本>/ test_package/
```

影响面口径（**按包根去重 + 给分母**）：本仓 `archives/` 下 **419 个包根**的 `conanfile.py` 出现
`dependencies.items()`；其中 **47 个包根**同文件内另含 `.name` 字样——这是**上限口径**，
未逐一确认那 47 处的 `.name` 就是循环键，不得对外说成"47 个坏配方"。
分母参考：`archives/` 共 11189 个 `conanfile.py`、约 6739 个包根。
