# DRAFT — perl 依赖包只声明 `runenv_info`（无 `buildenv_info`）时，其 `PERL5LIB` 不进下游 build 上下文

> 触发事件：test-metrics-any 0.01 HarmonyOS PC 适配（PR #11279，2026-09-20 真机实测）
> 依赖方：`metrics-any/0.10`（已合入 main + ohpcd）
> 相关先例：`DRAFT-perl-module-build-makemaker-substitution`（同批适配中的构建脚本替换）

## 现象

下游 perl 包在 `build()` 内跑上游测试（`make test`）时，明明已在
`requirements()` 里声明了依赖，测试仍报**找不到依赖模块**：

```text
Can't locate Metrics/Any/Adapter/Test.pm in @INC (you may need to install the
Metrics::Any::Adapter::Test module) (@INC entries checked: ...)
```

而该模块**确实**存在于依赖的制品包里（遍历 `dependencies["metrics-any"].package_folder`
能找到 `Metrics/Any/Adapter/Test.pm`）。

## 根因（实测）

Conan 的两个 env 通道语义不同：

| 声明 | 生效范围 |
|------|---------|
| `runenv_info` | **运行**上下文（消费方运行时、`test_package` 的 `env="conanrun"`） |
| `buildenv_info` | **构建**上下文（本包 `build()` 内执行的命令、`env=["conanbuild"]`） |

`metrics-any/0.10` 的 `package_info()` **只声明了 `runenv_info`**：

```python
# archives/m/metrics-any/0.10/conanfile.py（已合入，勿改动）
self.runenv_info.define_path("PERL5LIB", site)   # ← 仅 runenv，没有 buildenv_info
```

因此下游包在 `build()` 里执行 `make test` 时，`PERL5LIB` **不包含**依赖的 site
目录，上游测试的 `use Metrics::Any::Adapter::Test` 必然失败。这与"依赖是否声明
正确"无关——**依赖声明是对的，缺的是 env 通道声明**。

## 适用面（非个例）

**实测全库统计**（`origin/main` 上 perl 类包）：

| 情形 | 数量 |
|------|------|
| 声明了 `runenv_info` 的 perl 类包 | 84 |
| 其中**同时**声明 `buildenv_info` | 29 |
| 其中**仅**声明 `runenv_info` | **55（65%）** |

即本形态是**多数派**：任何"下游 perl 包的 `build()` 内要 `use` 依赖模块"的组合
都会命中。典型场景是**配套测试组件**——如本条的 `Test::Metrics::Any`（断言
`Metrics::Any` 指标）依赖 `Metrics::Any`，其上游测试必须在 build 期载入后者。

## 推荐方案

**不改动已合入的依赖配方**（R21：协作者不得改他人路径），在下游包 `build()` 内
**自行定位依赖的 perl lib 根并显式注入**：

```python
def _find_site(self, base, rel):
    """在 base 下查找包含相对模块路径 rel 的目录（即 perl lib 根）。"""
    for root, _dirs, _files in os.walk(base):
        if os.path.isfile(os.path.join(root, rel)):
            return root
    return None

def _dep_perl5lib(self):
    dep = self.dependencies["metrics-any"]
    site = self._find_site(dep.package_folder, os.path.join("Metrics", "Any.pm"))
    if not site:
        raise ConanException(f"dependency module not found: {dep.package_folder}")
    return site

def build(self):
    dep_site = self._dep_perl5lib()
    env_prefix = f'export PERL5LIB="{dep_site}:$PERL5LIB" && '
    self.run(env_prefix + "make test", cwd=self.source_folder)
```

**要点**：

1. 遍历依赖的 `package_folder` 定位模块（**不要硬编码安装前缀**——perl 的 site
   路径随其构建而异，实测 `.../perl_5.42.0/lib/site_perl/5.42.0`）；
2. 注入时用 `"<dep_site>:$PERL5LIB"` **前置拼接**，保留既有取值；
3. 若依赖将来补上 `buildenv_info`，该注入可移除，但保留亦无害（重复路径在
   `@INC` 里不影响解析）。

## 配套要点：本包的 `package_info` 用 `prepend_path` 而非 `define_path`

下游包自己也要暴露 `PERL5LIB` 时，**不要**照抄依赖的 `define_path`：

```python
# ❌ 覆盖语义：会把依赖的 PERL5LIB 取值整个挤掉
self.runenv_info.define_path("PERL5LIB", site)

# ✅ 追加语义：本包与依赖的取值都保留
self.runenv_info.prepend_path("PERL5LIB", site)
```

`define_path` 是**覆盖**语义。若链上每个包都用它，最终消费方只会拿到**最后一个**
包的路径，其余依赖模块全部不可见——本例中 `use Test::Metrics::Any` 后立即
`use Metrics::Any::Adapter`，会直接失败。

## 禁止做法

- ❌ **不要**为了让测试跑通而修改已合入的依赖配方（R21：越权改他人路径；且会让
  该 PR 变成"两个包"从而触发 CI JC6 硬失败）。
- ❌ **不要**把测试用 `skip` 或删掉依赖用例来"变绿"（R51：掩盖而非解决）。
- ❌ **不要**硬编码依赖的 site 路径（随 perl 构建漂移，换环境即失效）。
- ❌ **不要**用 `define_path` 暴露 `PERL5LIB`（见上，会让下游依赖断链）。

## 验证证据

- **主证据**：test-metrics-any 0.01（PR #11279）实测 —— 不加注入时 `make test`
  报 `Can't locate Metrics/Any/Adapter/Test.pm`；加入 `PERL5LIB` 注入后
  `Files=4, Tests=10, Result: PASS`；`conan create` exit=0，消费者 15/15。
- **规模证据**：`origin/main` 上 84 个 perl 类包声明了 `runenv_info`，其中 **55 个
  （65%）未声明 `buildenv_info`** —— 本形态是多数派，非个例。
- **依赖事实**：`conan list "metrics-any/0.10:*" -r=ohpcd` → 1 个 package_id；
  其包内含 `Metrics/Any/Adapter/Test.pm`（本包运行时依赖）。
- **环境**：HarmonyOS PC / aarch64 / hnp perl 5.42.0 / conan 2.29.1。

## 查重结论

- 对 `buildenv_info` 检索 `knowledge/`：无同主题条目（本条为首个记录）。
- 对 `PERL5LIB` 检索：命中 `DRAFT-perl-module-build-makemaker-substitution`
  （讲**构建脚本替换** Module::Build → Makefile.PL，其中提到用
  `runenv_info.define_path` 暴露 PERL5LIB，但**未涉及** env 通道缺失导致下游
  build 期取不到依赖、也未涉及 `prepend_path` vs `define_path` 的覆盖差异）。
- 对 `runenv_info` 检索：无条目覆盖"仅 runenv 声明 → 下游 build 上下文缺变量"。
- **两草稿关系**：`DRAFT-perl-module-build-makemaker-substitution` 解决"**构建
  入口**从哪来"，本条解决"**依赖模块**在 build 期如何可见"——同一批适配中两个
  独立问题，不重复。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
