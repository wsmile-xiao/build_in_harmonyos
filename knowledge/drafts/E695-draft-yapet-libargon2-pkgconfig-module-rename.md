# `Package 'libargon2' was not found`：PKG_CHECK_MODULES 模块名 ≠ conan 包默认 .pc 名时的消费侧改名正解

> Draft: E695
> Stem: `yapet-libargon2-pkgconfig-module-rename` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: E695
- **严重度**: 2
- **类别**: build-system|dependency|pkg-config|conan
- **触发工具**: configure|pkg-config|conan
- **阶段**: configuration

## 错误特征

`./configure` 阶段，上游 `PKG_CHECK_MODULES([ARGON2], [libargon2])` 探测失败：

```
Package libargon2 was not found in the pkg-config search path.
Perhaps you should add the directory containing `libargon2.pc'
to the PKG_CONFIG_PATH environment variable.
Package 'libargon2', required by 'yapet', not found
configure: error: Package requirements (libargon2) were not found
```

而依赖本身**确实在档**：`conan list -r=ohpcd argon2/*` 有 `argon2/20190702`，
`conan install --build=missing` rc=0，generators 目录里 `argon2.pc` 也真实生成了——
唯独文件名对不上上游要的**模块名** `libargon2`。

## 根因分析

conan 包默认产出的 pkg-config 文件名 = 包名（`argon2` → `argon2.pc`），
因为 `argon2` 配方的 `package_info()` 没有
`self.cpp_info.set_property("pkg_config_name", ...)`。
上游 configure 的 `PKG_CHECK_MODULES` 按**模块名**查文件
（`libargon2.pc`），两个命名体系各自合理、合在一起就错位。
pkg-config 的报错极具误导性——它让你去设 `PKG_CONFIG_PATH`，
但路径设得再对也救不了**文件名**不匹配。

## 解决方案

**主方案**: consumer-side-pkgconfig-rename

配方 `generate()` 里用 conan **文档化的** PkgConfigDeps 消费者改名 API：

```python
from conan.tools.gnu import PkgConfigDeps

pkg = PkgConfigDeps(self)
pkg.set_property("argon2", "pkg_config_name", "libargon2")
pkg.generate()
```

生成物即为 `libargon2.pc`，与 `cppunit.pc` 走同一条
`PKG_CONFIG_PATH`（在 `AutotoolsToolchain` 的 `environment()` 里
`prepend_path("PKG_CONFIG_PATH", self.generators_folder)`，即 E468 的修法），
零环境双源。

**两案对比（为何不选它们）**：

| 方案 | 机制 | 缺点 |
|------|------|------|
| A. `ARGON2_CFLAGS`/`ARGON2_LIBS` 环境覆盖 | pkg.m4 官方出口，configure 前导出即可跳过 pkg-config | 要从 `self.dependencies` 手工拼 `-I/-L/-l`（含 `rt`/`dl` 附加库），与 `cpp_info` 双源，依赖选项（shared/static）一变就漂移 |
| C. 手写 `libargon2.pc` 垫片 | 文件直给 | 字段（`Version:`、`Libs:`、`Requires:`、soname）全部手工同步，是三案里文件面最大的 |
| **B. `set_property` 改名（采用）** | conan 官方文档 API | 无：`.pc` 内容仍由 PkgConfigDeps 从 `cpp_info` 权威生成，只有文件名被改 |

## 验证命令

```sh
# 设备（落 $TASK_DIR，不用 /tmp）：
. "$HOME/tmp/yapet-2.6/env.sh"
grep -l "Name: *libargon2" "$BUILD_GENERATORS_DIR"/libargon2.pc   # generate 后
PKG_CONFIG_PATH=<generators目录> pkg-config --exists libargon2 && echo OK
```

复现（不带配方修正时）：

```sh
PKG_CONFIG_PATH=<generators目录> pkg-config --exists libargon2; echo rc=$?   # 1
PKG_CONFIG_PATH=<generators目录> pkg-config --exists argon2; echo rc=$?      # 0 ← 名字错位实证
```

## 关联陷阱（同一任务内一并登记）

- `PkgConfigDeps` 只写 `.pc` 不扩 `PKG_CONFIG_PATH` → 见正式条目 **E468**。
- `AM_GNU_GETTEXT([external])` 的 `msgfmt`：设备 harmonybrew 有、CI worker PATH 无
  （设备全绿 ≠ CI 绿）→ `tool_requires("gettext/…")` 显式供给。
- 新件 `config.guess`（2026-05-17）在 HarmonyOS 上仍会失败（先撞 HMDFS
  `umask 077` 草稿目录不可写，再打回 unable to guess），必须注入
  `*:HarmonyOS:*:* → ${MACHINE}-unknown-linux-ohos` 分支且置于编译探针之前
  → 既有条目 **E007** 族。
