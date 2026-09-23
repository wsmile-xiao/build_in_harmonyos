# Makefile 的 CFLAGS ?= 默认值被环境预置 CFLAGS 覆盖导致 -Iinclude 丢失

- **草稿 ID**: DRAFT-stc-5.0-makefile-cflags-env-override
- **来源**: STC 5.0 HarmonyOS PC 适配（2026-09-07，executor pc2-42，task stc-5.0-r01-bootstrap-and-adapt-pc2-42-20260907T155229Z）
- **分类**: make / cflags / build-system / conan / ohos
- **状态**: 本地草稿（路径 B 知识库扩展，随本库 PR 提交）

## 问题 / 错误签名

- 编译测试/示例报 `fatal error: 'stc/cstr.h' file not found`（include 目录存在但 `-Iinclude` 未生效）
- 错误签名: `fatal error: '[a-z_]+/[a-z_]+\.h' file not found`
- 复现: 构建环境预置 `CFLAGS=-fPIC -O2` 时运行 `make`（Makefile 内为 `CFLAGS ?= -std=c11 -Iinclude -O3 ...`）

## 根因

GNU make 的 `?=`（conditional assignment）仅在变量尚未定义时赋值。构建环境若已 export CFLAGS（本机/OHOS worker 预置 `CFLAGS=-fPIC -O2`），Makefile 的默认 CFLAGS（含 `-Iinclude`、`-std=c11` 等）被静默丢弃。

make 变量优先级：**命令行 > 环境变量 > Makefile 内 `?=` 默认值**。

## 最小修复方案

在 make 命令行显式传完整 CFLAGS（命令行变量优先级最高，覆盖环境与 `?=`）：

```bash
make lib CC=clang CFLAGS='-std=c11 -Iinclude -MMD -O3 -Wpedantic -Wall -Wextra -Werror -Wno-missing-field-initializers -fPIC' BUILDDIR=bld
```

conanfile.py 的 `build()` 同法（R33：编译器从 `self.conf` 的 `tools.build:compiler_executables` 字典获取）：

```python
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = compilers.get("c", "clang")
self.run(f"make lib CC={cc} CFLAGS='{cflags}' BUILDDIR=bld", cwd=self.source_folder)
```

## 验证

- 修复前: 环境预置 CFLAGS 时 `make` → `fatal error: 'stc/cstr.h' file not found`（日志 `/storage/Users/currentUser/tmp/builds/stc-5.0-make.log`）
- 修复后: `make` 0 error，`libstc.a` 生成；上游 `test_all` 33/33 通过

## 适用边界

- 适用: raw Makefile（非 autotools/cmake/meson 生成）且用 `?=` 声明默认标志的库；构建环境 export CFLAGS/CXXFLAGS/LDFLAGS 的场景（OHOS worker、Conan profile buildenv、CI）
- 限制: autotools/cmake/meson 生成的 Makefile 不受影响（标志由生成器按 configure/CMake 选项写入）；GNU make 语义，BSD make 的 `?=` 行为不同；显式传 CFLAGS 时必须完整带上上游默认标志（如 `-Werror`、`-Wpedantic`），否则覆盖后丢失原档位

## 反例

- ❌ 仅依赖 Makefile 内 `?=` 默认值、不在命令行/配方显式传 → 环境一旦 export CFLAGS 即失效，本地与 CI 行为不一致
- ❌ 用补丁把 `?=` 改成 `=` → 违反 R1 最小改动，增加补丁维护成本并破坏可覆盖性

## 查重差异（vs E392 / E276 / E063）

- **E392**（raw makefile 三陷阱: BadZipFile 编码器误选 / compiler_executables 字典获取 / make 默认 cwd）：不涉及 make 变量优先级；本条目与其互补（同属 raw makefile Conan 配方模式族）
- **E276**（codeload BadZipFile → filename 参数）：仅覆盖下载解压阶段；本库已在 conandata.yml 用 `filename: "stc-5.0.tar.gz"` 按 E276 方案处理（等价命中，路径 A 复用）
- **E063**（-Werror 在 musl/clang 下的警告升级）：仅覆盖警告类别，不涉及 `?=` 覆盖机制
- 本条目新增: make `?=` 变量优先级被环境 CFLAGS 覆盖 → 显式传完整 CFLAGS（含 -Iinclude）
