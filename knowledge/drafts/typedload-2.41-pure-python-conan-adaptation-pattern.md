# DRAFT: typedload-2.41-pure-python-conan-adaptation-pattern

> Draft（待知识库主编审核，拟提升编号 Exxx）｜对应: `knowledge/drafts/typedload-2.41-pure-python-conan-adaptation-pattern.kv`
> 说明：该 md 为 kv 条目的人类可读镜像。

- 条目主题：**纯 Python 包（unittest 系）在 OHOS/HarmonyOS PC conan 生态的适配范式**——`python-require` 布局、测试依赖用 `tool_requires`、`__pycache__` 污染包目录、消费者断言必须按上游真实语义校准。
- 首次实证：`typedload/2.41`（纯 Python，无 C 扩展，`py3-none-any`）——上游 212 用例全绿、消费者 17 用例全绿。
- 状态：草稿（待审核）

## 适用场景

上游是**纯 Python 包**（无 C 扩展 / 无 pybind11 绑定），在 OHOS 上做 conan 适配时。
与本仓既有 127 个 `python-require` 配方同族（`typepy` / `jinja2` / `attrs` / `dominate` …）。

## 范式（照抄要点）

1. **package_type 与落位**
   ```python
   package_type = "python-require"
   settings = "os", "arch", "compiler", "build_type"
   # package(): <pkg>/lib/python3.12/site-packages/<module>/（与 OHOS python3.12
   # sysconfig purelib 布局一致，否则 OHOS 解释器不会命中）
   ```
2. **运行时依赖必须严格按 sdist PKG-INFO 的 `Requires-Dist` 判定**
   - typedload：`PKG-INFO` **无任何 `Requires-Dist` 行** → `requirements()` 留空。
   - **禁止**为「能跑测试」把测试依赖写成 `requires`（会污染下游依赖链，且 W4 审计会判 P0）。
3. **测试依赖用 `tool_requires`（构建上下文，不传播给消费者）**
   ```python
   def build_requirements(self):
       self.tool_requires("attrs/26.1.0")     # 仅 tests/ 需要
   # build() 内经 self.dependencies.build["attrs"].package_folder 取 site-packages
   # 注入 PYTHONPATH；解析失败必须 raise（R51：不得以「跳过」冒充通过）
   ```
4. **上游若用 stdlib `unittest` 则不需要 pytest** —— `python3 -m unittest discover -s tests -v`
   即可全量执行（typedload 15 个 `test_*.py` / 212 用例）。
5. **`__pycache__` 污染包目录（本项目实测踩坑）**
   - 现象：`conan create` 的 test 阶段跑消费者 python 脚本后，包目录出现
     `__pycache__/*.pyc`，导致「payload 是纯 Python 源码」类断言失败、`conan create` RC=1。
   - 对策：test_package 在 `self.run` 前设 `PYTHONDONTWRITEBYTECODE=1`；
     消费者从 conan 缓存包目录 import 时同理（否则包目录会被写脏）。
6. **测试计数不要用「行尾 `... ok`」——用例内 `print` 会与结果行交错**
   - 现象：`Ran 212 tests` 但按行尾计数只得 210。
   - 对策：以汇总行 `Ran N tests` + `OK`/`FAILED (failures=X, errors=Y)` 为权威来源。
7. **消费者断言必须先用上游真实语义校准**（否则写出「自证正确」的假测试）。typedload 实测真值：
   - **裸泛型不可用**：`load([1,2], list)` → `TypedloadTypeError: Cannot deal with value of type list`
     （必须 `list[int]`/`dict[str,int]`/`set[int]`/`tuple[int,str]`）；
   - `Dumper` 默认 `hidedefault=True`：`dump(obj)` 会**省略等于默认值的 dataclass 字段**，
     需要完整往返必须 `dump(obj, hidedefault=False)`；
   - 数值转换是**合法行为**：`load(1.5, int) == 1`、`load(123, str) == '123'`
     （不能拿它当负例）；真正的负例：`load("abc", int)`、`load(None, int)`、
     Literal 越界、`dict[str,int]` 值非法。
8. **「不跳过」的对照实验**：typedload 缺 `attrs` 时实测 `Ran 187 tests` + `FAILED (errors=1)`
   ——187 个也能「跑完」，很容易被误当成全量。补齐依赖后 212/212。

## 验证命令（typedload 实测）

```bash
conan create archives/t/typedload/2.41 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="typedload/*"
# → RC=0
#   upstream unittest: Ran 212 tests | passed=212 failed=0 errors=0 skipped=0 | OK
#   typedload consumer API: 17/17 passed（含 3 项鸿蒙专有断言）

# 独立复核（不依赖 build() 自报）：unittest.TestLoader 枚举 → 212 条，与实测名单逐条 diff 一致
```

## 关联

- 适配 PR：（待创建）`feat/typedload-2.41`
- 相关先例：`archives/t/typepy/2.0.0`（python-require 基线）、`archives/j/jinja2/3.1.6`
  （纯 Python + 测试期 pip 取依赖）、`archives/a/attrs/26.1.0`（tool 依赖方）
