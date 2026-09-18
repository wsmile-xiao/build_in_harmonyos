# E544 — Conan 2 用 self.dependencies["pkg"] 取 tool_requires 抛 KeyError "not found in the dependency set"

> 状态：DRAFT（contributor NGS1，2026-09-16，实测于 ngs 0.2.17 适配）

## 错误特征

`conan create` 在 `generate()` 阶段直接失败，而不是在依赖解析阶段：

```
ngs/0.2.17@ohpcd/stable: Calling generate()
ERROR: ngs/0.2.17@ohpcd/stable: Error in generate() method, line 80
        peg = self.dependencies["peg"]
        KeyError: "'peg' not found in the dependency set"
```

迷惑性在于：报错文本 "not found in the dependency set" 听起来像"制品仓里没有这个包"，
容易把排查方向带偏到 W0 依赖预检 / `dependency_missing` 上报上去。而实际上
`conan list` / 依赖图阶段该包明明存在（日志里 `Build requirements peg/0.1.19 - Cache` 就在上面）。

## 触发条件

- 构建系统：任意（cmake/autotools/meson 均可）
- 阶段：`generate()`（或任何读取依赖对象的时机）
- 前置：配方声明了 `tool_requires("pkg")`，并要把该 pkg 的可执行文件路径
  （`cpp_info.bindirs[0]`）注入构建系统变量 —— 典型场景是把交叉构建期的
  代码生成器（leg、ragel、gperf、bison 之类）钉定为制品仓版本，而不是
  依赖宿主 PATH 上的同名工具。

## 根因分析

Conan 2 的 `self.dependencies` 是一个按 context 分层映射，**默认访问只暴露 host context**。
`tool_requires` 的包属于 build context，不在 host context 里，因此
`self.dependencies["pkg"]` 查不到 → `KeyError`。

`self.requires()` 的包恰好能用单键写法访问，是因为它在 host context；
这个不对称是该坑的根源 —— 同一份配方里 host 依赖写法正确、build 依赖写法错误，
看上去只有一行之差。

## 解决方案

### 推荐方案
取 build context 依赖必须显式走 `.build` 层：

```python
def generate(self):
    tc = CMakeToolchain(self)
    peg = self.dependencies.build["peg"]      # ← tool_requires 走 .build
    tc.cache_variables["LEG"] = os.path.join(peg.cpp_info.bindirs[0], "leg")
    sed = self.dependencies.build["sed"]      # ← GNU sed 同理
    tc.cache_variables["SED"] = os.path.join(sed.cpp_info.bindirs[0], "sed")
    tc.generate()
    # host 侧依赖仍可用 self.dependencies["json-c"] / .host[...]
```

### 禁止做法
- ❌ 因为查不到就报 `dependency_missing` 去补制品仓 —— 包是存在的，只是 context 不对
- ❌ 回退成宿主 PATH 上的 `leg`/`sed`（CI clean 环境可能没有，或版本与配方预期不同，
  生成的解析器/脚本会漂移）
- ❌ 用 `self.build_requires` 之类旧 Conan 1 API 绕

## 验证

```bash
conan create . --build=missing     # generate() 不再抛 KeyError
# 进一步确认注入的是制品仓版本而非宿主版本：
grep -E "LEG|SED" <build_folder>/Release/generators/cmake_toolchain.cmake
#   期望指向 ~/.conan2/p/<peg…>/p/bin/leg 而不是 /data/service/hnp/bin/leg
```

## 关联条目

- 无强关联。`draft-review` 查重：最近邻 E300（相似度 0.32，不同问题）；
  `not found in the dependency set` 这一 error_signature 在正式库 E001-E542 中零命中。
- 互相 link：与本批次 E543（同为"配方自身写法导致 conan create 失败"类）建议标 similar_to。
