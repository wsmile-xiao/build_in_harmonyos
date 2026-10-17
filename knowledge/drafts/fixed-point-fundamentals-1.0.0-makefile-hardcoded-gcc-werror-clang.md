# fixed-point-fundamentals 1.0.0 — 纯 Makefile 项目硬编码 CC=gcc 与 clang -Werror 的教学示例适配

> 草稿（DRAFT，路径 B 候选）— 随 fixed-point-fundamentals 1.0.0 归档 PR 交付，经审核后可 promote 为正式条目。

## 问题

教学/示例类小型 C 项目（纯 Makefile、无 configure）在 OHOS（无 gcc，仅 clang）下构建失败：

```
make: gcc: No such file or directory            # 顶层与各 lesson Makefile 硬编码 CC = gcc
# 且 Makefile 用 2>/dev/null || true 吞错 → make 返回成功但二进制缺失

lessons/.../format_comparison.c:35:23: error: unused function 'float_to_q1_15'
                                     [-Werror,-Wunused-function]
lessons/.../rounding_modes.c:186:24: error: implicit conversion from 'int64_t' (aka 'long')
                                      to 'double' may lose precision [-Werror,...]
```

## 根因

两个独立断点：

1. **CC=gcc 硬编码** — 纯 Makefile 项目无 configure，配方套用 autotools 模板必然失败；
   上游 Makefile 硬编码 `CC = gcc`，而 OHOS/CI 只有 clang。`2>/dev/null || true`
   使失败静默（构建"看似成功"但产物缺失），必须显式验证产物存在并运行。
2. **clang 比 gcc 更严格的 -Werror** — `static inline` 未使用函数
   （`-Wunused-function`）与 `int/int64→float/double` 隐式截断
   （`-Wimplicit-int-float-conversion`）在 gcc 下不告警或仅告警，clang 在
   `-Werror -Wconversion` 下直接升级为错误。实测 17 个示例中 5 个因此失败
   （unused static inline ×3、隐式转换 ×2）。

## 方案

配方 build() 两步（不改上游源码、不打补丁）：

```python
def build(self):
    apply_conandata_patches(self)
    comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = comp_execs.get("c") or "clang"            # R33: 编译器取自 Conan Toolchain
    cflags = "-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -O2 -g"  # 去 -Werror
    self.run(f'make examples CC="{cc}" CFLAGS="{cflags}"', cwd=self.source_folder)
```

另在 test_package 显式逐一运行产物验证（make 吞错的对冲）。

## 验证

- conan create（OHOS aarch64 profile）干净构建通过，test_package 双脚本全绿。
- 17/17 示例编译成功并逐一运行 exit=0、输出非空（上游无独立测试框架，make test
  扫描的 src/tests 模式不存在，实例化 0 用例；示例程序为可运行入口）。

## 适用边界

- 仅影响纯 Makefile、无 configure、硬编码 `CC=gcc` 且 CFLAGS 含 `-Werror` 的教学/示例类项目。
- `-Wimplicit-int-float-conversion` 是 clang 特有信号（gcc 无此告警名），仅 clang 平台触发；
- `-Wunused-function` 对 `static inline` 在 gcc 不告警、clang 告警——头文件内联工具函数密集的库也可能踩中。
- 本方案对库型项目（有 .h/.a 产物）不适用，那种场景应走既有 E063 逐类 `-Wno-error=...` 方案或常规 CC 注入。

## 与既有知识关系

- similar_to: E001（cc not found，configure/PATH 环境变量维度）、E053（gcc C++ 前端缺失）、
  E063（-Werror → -Wno-error 逐类处理）
- 新增差异: ① make 调用点注入 CC（非 E001 的 PATH 环境变量，R33 工具链来源）；
  ② E063 收录的四类信号不含 -Wunused-function（static inline）与
  -Wimplicit-int-float-conversion；③ 教学示例仓库整体去 -Werror 比逐类 -Wno-error 更省，
  且必须处理 Makefile `|| true` 吞错导致的伪成功。