# E568 — AC_FUNC_MALLOC 误判致 malloc=rpl_malloc，隐式声明在 aarch64 上截断指针

## 错误特征

configure 阶段固定报"不兼容"：

```
checking for GNU libc compatible malloc... no
checking for GNU libc compatible realloc... no
```

生成的 `config.h` 随即把 malloc 家族整体重定向（ac_cv 判否的标准产物）：

```c
#define malloc rpl_malloc
#define realloc rpl_realloc
```

后续症状分两段出现，容易被误判成两个不相干的 bug：

- 编译期：`error: incompatible integer to pointer conversion assigning to 'void *' from 'int'`（cpu 实测 `src/util/fileaction.c:190:13`）
- 链接期：`undefined reference to 'rpl_malloc'`

## 触发条件

- 构建系统: autotools（AC_FUNC_MALLOC / AC_FUNC_REALLOC 宏）
- 阶段: configure → make → link
- 环境: 交叉编译 / OHOS；运行期探针结果与目标 libc 真实语义不一致时必然命中
- 观察: 同一份 configure 在主机 in-tree 编译可通过，走 conan 交叉编译后必现

## 根因分析

AC_FUNC_MALLOC 是**运行期**探针：它编译并执行 conftest，靠返回码判断 malloc(0) 是否返回非空指针（glibc 语义）。交叉编译场景下探针无法反映目标平台语义（cpu 实测该探针在本平台恒判 no），autoconf 于是走"兼容性修正"分支，把 `malloc` 宏重定义为 `rpl_malloc`（realloc 同理）。

而 rpl_malloc 的实现属于 gnulib 替换模块，上游并未引入——于是只剩一个**没有声明的函数**。C 语言隐式声明规则把它当作返回 `int`，在 aarch64 上 int(32 位) 与 void*(64 位) 宽度不等，赋值处被 clang 判为 pointer conversion 错误；即使编译放过，链接期也会因符号缺失失败。

关键点：这不是源码缺陷，而是**探针结论错误**——修源码、加原型都只是治症状，正解是让探针走"已知答案"。

## 解决方案

### 推荐方案

不改源码，在 conanfile.py 的 `generate()` 中向 configure 注入 autoconf 标准 cache 变量（cache 变量优先级高于探针，autoconf 官方支持）：

```python
tc = AutotoolsToolchain(self)
tc.configure_args += [
    "ac_cv_func_malloc_0_nonnull=yes",
    "ac_cv_func_realloc_0_nonnull=yes",
]
```

cpu 1.4.3 实测：注入后 configure 不再打印 "GNU libc compatible malloc ... no"，`config.h` 不再出现 rpl_malloc，编译与链接一次通过。

### 禁止做法

- ❌ 手改 `config.h` / `configure`（生成文件，任何 regenerate 都会丢失；违反 R6 只改源文件）
- ❌ 在 `config.h` 里补 `rpl_malloc` 原型或 `-Dmalloc=malloc` 硬顶（掩盖探针误判，同一工程其他探针仍会踩同类坑）
- ❌ 用 `--build=` / `--host=` 绕过去（R1 禁用参数，会连带打乱其他探测）

## 验证

```bash
# 1. config.h 不应出现替换宏
grep -E "rpl_malloc|rpl_realloc" config.h   # 期望：无输出
# 2. configure 日志不应再判否
grep "GNU libc compatible malloc" configure.log   # 期望：yes
# 3. 端到端
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify cpu 1.4.3
```

## 关联条目

- 相关: E569（同类"探针/路径语义在交叉环境失效"，方案形态不同：include 路径）
- 相关: E007（平台探针 config.guess/config.sub 层面，本条目是 autoconf 宏层面）
