# E543 — Conan 2.x `tool_requires` 定义方式错误

> 草稿知识项 — Conan 2.x 构建期工具依赖的声明方式
> 来源：xmlbird 1.2.14 适配（PR #7452，conan-verify G2 报错后修复）
> 同 stem 配对：`knowledge/drafts/E543-draft-31CE.kv`

## 错误特征

`conan create` 加载 conanfile.py 时直接报错，配方无法加载、构建无法启动：

```
ERROR: Error loading conanfile at '.../conanfile.py':
Wrong 'tool_requires' definition, did you mean 'build_requirements()'?
```

## 触发条件

- 构建系统：Conan 2.x（recipe 使用 `build_requirements()` / `tool_requires` 语法）
- 阶段：配方加载（conan create 启动阶段）
- 特征：把 `tool_requires` 定义成了独立方法名

## 根因分析

Conan 2.x 中 `tool_requires` **不是**配方方法名。构建期工具依赖（编译器/构建系统/辅助工具，如 valac）必须在 `def build_requirements(self):` 方法体内通过 `self.tool_requires("pkg/ver")` 声明。把 `tool_requires` 定义成独立方法，conan 在加载配方时直接报错。

## 解决方案

### 推荐方案

```python
# ❌ 错误：tool_requires 不是独立方法
def tool_requires(self):
    self.tool_requires("vala/0.56.18")

# ✅ 正确：在 build_requirements() 方法内声明
def build_requirements(self):
    self.tool_requires("vala/0.56.18")
```

### 禁止做法

- ❌ 定义 `def tool_requires(self):` 独立方法（配方加载直接失败）
- ❌ 把 tool_requires 放在 `requirements()` 方法里（那是 host 依赖，不是构建期工具）

## 验证

- xmlbird 1.2.14 适配：改写为 `build_requirements()` 后 `conan create` 正常加载配方并通过（conan-verify G0-G5 全绿）。
- 验证命令：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
