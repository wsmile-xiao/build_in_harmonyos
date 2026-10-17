# DRAFT-ohos-static-tool-bypass-dlopen-limit — 构建期工具无法执行时，从源码静态编译替代

> Contributor: 8D52 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-static-tool-bypass-dlopen-limit`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E488` | 图谱 | HMDFS 强制文件 owner 为 `20001006:file_manager`（权限 770）导致 **dlopen 被拒**；修法是 **copy-rewrite**（复制包到可写目录 + 逐字节重写 `.so` + `chmod 777` + rename）| 那条解决的是"**自有/产物**共享库在本机加载被拒"，手段是文件系统层规避；本条面对的是"**制品仓提供的构建期工具**在构建另一包时无法执行"，且解法是**从源码静态重建工具**（不碰缓存、不改权限）。本条把 copy-rewrite 明确降为回退方案 |
| `E331` | 图谱 | HMDFS 上 CMake 版本化共享库的**符号链接链**问题 | 那是构建**产物**时的链接命名问题；本条是消费**既有工具**时的执行问题 |
| `E461` | 图谱 | AF_UNIX `bind()` EPERM / `/tmp` EROFS / `/dev/shm` EACCES（沙箱能力限制）| 那是**socket 类**能力被禁；本条是**动态链接器**层面的加载被拒，报错与处置完全不同 |

**全库查证**：对 `静态编译` / `-static` / `内嵌工具` / `scanner` / `dlopen.*缓存` /
`从源码编译.*工具` / `statically.*bypass` 等关键词，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep —— **命中 0 条**
（仅 `DRAFT-libjpeg-turbo-...-NEEDED-ctest-loading` 在"反例"里提到纯静态链接库不受影响，
非同一问题层）。

## Scope（何时用）

**构建期必需的工具**由制品仓依赖提供、且它链接了共享库 → 在 HMDFS 上执行失败。

典型形态：**协议/IDL 代码生成器**。

实测实例（wayland-protocols）：

```
wayland 包自带 wayland-scanner
    ↓ 链接
libexpat.so / libxml2.so（位于 Conan 缓存）
    ↓ 在 HMDFS 上执行
error while loading shared libraries / cannot execute binary file
```

而上游 `wayland-protocols` 的 `meson.build` 需要它：

```meson
dep_scanner = dependency('wayland-scanner', native: true)
prog_scanner = find_program(dep_scanner.get_variable(pkgconfig: 'wayland_scanner'))
```

**与"工具缺失"的关键区别**：工具**存在、可读、权限正常**，只是**执行时动态加载失败**。
因此 `find_program` 能找到它，故障推迟到真正运行时才暴露。

## Symptom

```console
$ <pkg>/bin/wayland-scanner --help
error while loading shared libraries: libexpat.so.1: cannot open shared object file

$ ldd <pkg>/bin/wayland-scanner | grep -v libc
    libexpat.so.1 => /path/to/conan-cache/.../libexpat.so.1
    libxml2.so.2  => /path/to/conan-cache/.../libxml2.so.2
```

若在 meson 里，表现为 `find_program` 成功但 `generator()` 运行时报错，
或直接 `cannot execute binary file`。

## Root Cause

HMDFS 对 **Conan 缓存目录中的共享库禁止动态加载**。这不是权限位问题——
文件可读、权限正常，改 `chmod` 无效（这也是本条与 `E488` 的分界：E488 是权限/属主，
本条是加载被拒）。

而该工具**不可放弃**：它是构建另一个包的必要环节（生成协议头文件与封送代码），
不是可选测试的附属品。故只有两条路：

1. **从源码重建一个静态工具**（本条推荐）——绕过共享库依赖；
2. 复制包到可写目录并重写其 `.so`（`E488` 的 copy-rewrite，本条降为回退）。

## Recommended Solution

### 主方案（priority 1）— `build-static-tool-from-source`

**五步**（实测于 wayland-protocols 1.47）：

**① 额外下载工具所在包的源码**

```yaml
# conandata.yml
scanner_sources:
  url: "https://.../wayland-1.24.0.tar.gz"
  sha256: "..."
```

```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)
    get(self, **self.conan_data["scanner_sources"],
        strip_root=True, destination="wayland-scanner-src")
```

**② 手工生成该工具所需的最小配置头**

上游通常用构建系统生成 `config.h` 与 `*-version.h`。脱离构建系统时要手工补：

```python
# config.h
f'#define HAVE_EXPAT 1\n#define PACKAGE "wayland"\n#define VERSION "{ver}"\n'

# 由 .h.in 模板替换占位符
for key, val in [("@WAYLAND_VERSION@", ver),
                 ("@WAYLAND_VERSION_MAJOR@", major), ...]:
    content = content.replace(key, val)
```

内嵌数据用上游脚本生成（如 `embed.py <dtd> wayland_dtd > wayland-dtd.h`）。

**③ `-static` 编译，静态库按序查找、找不到即报错**

```python
cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
self.run(f'{cc} -o {scanner_bin} -include {config_h} '
         f'-I{src} -I{src}/src -I{src}/protocol '
         f'{src}/src/scanner.c {src}/src/wayland-util.c '
         f'-I{expat_inc} {expat_lib} -lm -lpthread -static')
```

> ⭐ 静态依赖（如 `libexpat.a`）的查找要**按序尝试多路径**（SDK 自带 → 依赖包内），
> **全部失败则抛 `ConanException` 显式报错**，不要静默降级——否则会在链接期以
> 晦涩的 undefined symbol 暴露。实测写了 `_find_expat_static()` / `_find_expat_include()`
> 两个 helper 承担这个职责。

**④ 把产物交给构建系统找到**

写一份 `.pc` 指向自编译的工具，必要时注入 native file 的 `[paths]`：

```python
# wayland-scanner.pc
f"prefix={self.generators_folder}\n"
f"bindir=${{prefix}}\n"
f"wayland_scanner=${{bindir}}/wayland-scanner\n"
f"Version: {SCANNER_WAYLAND_VERSION}\n"     # ← 必须满足下游的门槛要求
```

```ini
# conan_meson_native.ini 的 [paths]
pkg_config_path = '<fixed_pkgconfig>'
```

因为 `dependency('wayland-scanner', native: true)` 会在 **native 侧**查找。

**⑤ 构建顺序：必须在 configure 之前**

`find_program()` 会检查文件是否存在，故 `_build_static_scanner()` 要放在
`meson.configure()` 之前调用。实测把它放在 `build()` 的第一行。

### 回退方案（priority 2）— `copy-rewrite`

若工具功能无法从源码完整重建（依赖大量外部库），退回到 `E488` 的 copy-rewrite：
复制包到可写目录、逐字节重写 `.so` 内容、放宽权限后执行。脆弱且需在 notes.md 详述。

### 禁止做法

- ❌ 因工具无法执行就关掉对应功能（如 `-Dtests=false`）了事 —— 该工具是**构建另一包所必需**的，关掉会让产物缺功能或让下游构建不了，把环境问题转嫁成功能缺失。
- ❌ `chmod 777` 缓存里的 `.so` —— 本限制不是权限位问题，改权限无效，还会污染 Conan 缓存（后续可能报脏状态）。

## 实测证据（2026-09-16）

| 项 | 结果 |
|---|---|
| 故障复现 | wayland 包自带的 scanner 在 HMDFS 上无法执行（链接 `libexpat.so` / `libxml2.so`）|
| 静态重建 | 用 wayland **1.24.0** 源码编译 `-static` scanner（仅依赖 libc），配合 SDK 自带 `libexpat.a` |
| 交给构建系统 | 自造 `wayland-scanner.pc` + native file `[paths]` 注入 |
| 结果 | wayland-protocols 1.47 上游测试 **179/179 全过**（scan / pedantic C99 / C++ build 三类均使用该静态 scanner）；打包 57 XML + 60 头文件 |

**附带约束（实测踩到）**：工具版本受**下游门槛**反向约束——wayland-protocols 1.47
在 `tests=true` 时要求 `wayland-scanner >= 1.23.0`，故内嵌 scanner 的源码不能沿用旧的
1.22.0，必须升到 1.24.0，且 `.pc` 的 `Version:` 要同步。此项与
`DRAFT-ohos-downstream-version-threshold-bump` 相衔接。

## 测试覆盖边界

本条只解决"工具**执行时动态加载失败**"。若工具是**功能缺失或版本过低**（能执行但报
版本不支持），走的是依赖版本升级路径；若工具**根本不存在**，则是新适配问题。
三者报错与处置均不同，勿混用。

## 关联条目

- 相似：`E488`（dlopen 权限，copy-rewrite）、`E331`（HMDFS 符号链接链）、`E461`（沙箱能力限制）
- 差异：见上方差异化定位表
- 衔接：`DRAFT-ohos-downstream-version-threshold-bump`（工具版本受下游门槛约束）
