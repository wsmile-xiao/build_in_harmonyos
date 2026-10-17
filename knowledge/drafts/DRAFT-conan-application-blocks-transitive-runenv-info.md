# DRAFT-conan-application-blocks-transitive-runenv-info — application 型包阻断依赖的 runenv_info 传播

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: conan / dependency-graph / runtime-env

## 症状

`package_type = "application"` 的包，其**运行期依赖**声明的环境变量在消费者环境里
**完全缺失**。以 debarchiver → opalmod 为例：

```sh
$ conan install --requires=debarchiver/0.11.7 -g VirtualRunEnv
$ grep -o 'export PERL5LIB=.*' conanrunenv-*.sh | tr ':' '\n' | grep -c opalm
0                        # ← opalmod 的 PERL5LIB 一条都没有
$ debarchiver --version
Can't locate OpaL/action.pm in @INC
```

而同一条命令的 `conan install` 日志里能看到：

```
Skipped binaries
    opalmod/0.2.2.1
```

## 根因

opalmod 的 `package_info()` 用 `runenv_info` 声明自己的 Perl 模块路径：

```python
self.runenv_info.append_path("PERL5LIB", ...)
```

但当**中间包是 application 类型**时，该依赖在消费者图中被判为 **Skipped binaries**
（`package_folder` 为 None），其 `runenv_info` **不会**进入消费者聚合的 runenv 文件。

> **机制解释（推断，未逐行追 Conan 源码）**：application/executable 类包的
> headers/libs trait 为 False，Conan 认为消费者不需要其依赖的二进制 → 跳过依赖。
> 但 **`runenv_info` 属运行期环境，与 headers/libs 无关**，被一并跳过就产生了本问题。
> 条目中**事实部分为可复现实测**，机制部分为推断。

## 决定性对照实验

合成包，**唯一变量是中间包的 `package_type`**（conan 2.29.1）：

| 中间包类型 | 消费者 runenv 中依赖路径数 | Skipped binaries 含该依赖 |
|-----------|--------------------------|--------------------------|
| `static-library` | **2** ✅ | 否 |
| **`application`** | **0** ❌ | 是 |

无 `package_type` 的普通包（默认 library）实测亦**正常传播**（1 条）。

### 真实场景验证（debarchiver + opalmod）

| 消费者依赖声明 | runenv 中 opalmod 路径数 |
|--------------|------------------------|
| 仅 `debarchiver/0.11.7`（经传递） | **0** ❌ |
| `debarchiver/0.11.7` + `opalmod/0.2.2.1`（直接声明） | **8** ✅ |
| 仅 `opalmod/0.2.2.1`（对照，证明 opalmod 自身声明有效） | **2** ✅ |

## 修法

**消费者侧直接声明该运行期依赖**（不必依赖中间包的传递）：

```python
def requirements(self):
    self.requires("debarchiver/0.11.7")   # application 型包本身
    self.requires("opalmod/0.2.2.1")      # ★ 显式再声明其运行期依赖
```

对 **`test_package` 尤其重要** —— test 本就需要被测程序的**全部**运行期依赖，
直接声明是**语义正确**的做法，不是 workaround。

真实消费者若要运行该程序，也应在自己图中直接声明（或在文档中明确该使用要求）。

## 排查方法

```sh
conan install . -g VirtualRunEnv
# ① 该依赖的路径是否传播（0 = 未传播）
grep -o 'export PERL5LIB=.*' conanrunenv-*.sh | tr ':' '\n' | grep -c '<dep-name>'
# ② 该依赖是否被 skip
grep -A4 'Skipped binaries' <install 输出> | grep '<dep-name>'
```

## 实证

**debarchiver 0.11.7**（`feat/debarchiver-0.11.7`，PR #9710）：

| 阶段 | 结果 |
|------|------|
| 修正前 test_package | **4 项失败**：`OpaL::*` 未解析、`--help`/`--version` 均报 `Can't locate OpaL/action.pm in @INC` |
| test_package 中直接声明 `opalmod/0.2.2.1` 后 | **9/9 通过** |

## 与既有条目的差异

| 既有条目 | 关系 |
|---------|------|
| `DRAFT-conan-skipped-binaries-package-folder-null-guard` | 同样涉及 **Skipped binaries / `package_folder=None`**，但讲的是 **SHARED 库的 STATIC 子依赖**被标 skip 后，**配方依赖循环未判空即 TypeError 硬崩** → 修法是"每处循环先判空"。本条讲的是 **application 型包**导致 skip 后 **`runenv_info` 环境变量不传播** → 修法是"消费者直接声明依赖"。**触发类型不同、失败表现不同、修法不同**（该草稿中 `runenv_info`/`PERL5LIB`/`application` 命中均为 0）|
| `DRAFT-conan-shared-pkgconfig-requires-drop` | 同为 skip 造成下游影响，但讲 **PkgConfigDeps 把依赖从 `.pc` Requires 链丢弃**；本条是 **runenv/环境变量**，且触发类型是 application 而非 shared |

> 查重（2026-09-12）：`application.*runenv` = **0**、`runenv.*application` = **0**、
> `Skipped.*runenv` = **0**。

## 禁止

- ❌ **把中间包的 `package_type` 从 `application` 改成 `library`** 让传播恢复 ——
  该包**确实是可执行程序**，application 才是正确类型；改类型会误导下游、破坏包的
  语义（消费者会拿到错误的 headers/libs 语义），属于"为了绕开环境问题而引入更隐蔽
  的语义错误"
- ❌ **在中间包 `package_info()` 里用 `self.dependencies["<dep>"]` 自行补 `runenv_info`**
  —— 实测该阶段取不到被 skip 依赖的 `package_folder`（输出
  `WARN 未取到 <dep> 的 package_folder`），依赖已被跳过；配方看似处理了，实际路径
  仍为空，问题原样保留且只在 CI 暴露
