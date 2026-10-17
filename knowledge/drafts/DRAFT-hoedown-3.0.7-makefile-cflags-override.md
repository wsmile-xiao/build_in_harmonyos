# DRAFT-hoedown-3.0.7：纯 Makefile 库的工具链标志传递（CFLAGS 覆盖）

> Contributor: Tianyi Wang | Status: Draft | Updated: 2026-09-07
> Source: task hoedown-3.0.7-r01-bootstrap-and-adapt-pc2-33-20260906T143857Z

## 背景

hoedown 3.0.7 是纯 Makefile 库（无 configure）。配方 build() 用
`AutotoolsToolchain` 生成工具链环境（CC/CFLAGS/LDFLAGS，含 OHOS target/sysroot
关键标志），再直接驱动上游 Makefile。若不处理 make 变量优先级，工具链标志会整体丢失。

## 问题：Makefile 赋值覆盖环境 CFLAGS

### 现象

上游 Makefile 自带：

```make
CFLAGS = -g -O3 -ansi -pedantic -Wall -Wextra -Wno-unused-parameter
HOEDOWN_CFLAGS = $(CFLAGS) -Isrc
```

GNU make 变量优先级：**命令行参数 > Makefile 内赋值 > 环境变量**。
因此即便 conanbuild 环境注入了 `CFLAGS=--target=aarch64-linux-ohos ...`，
`make` 仍使用 Makefile 自带的 `-g -O3 -ansi ...`，工具链的 target/sysroot 标志
不生效（CC 环境变量因 Makefile 未赋值而生效）。

### 根因

- 纯 Makefile 项目没有 configure 环节来"消费"环境标志；make 直接按上述优先级
  决定每个变量取值。
- `AutotoolsToolchain` 的环境注入只解决"环境里有标志"，不解决"Makefile 赋值
  覆盖环境"。

### 修复

把工具链 CFLAGS/LDFLAGS 作为 **make 命令行参数** 显式传入（命令行优先级最高），
并用 `shlex.quote` 防止含空格的标志串被 shell 分词：

```python
with VirtualBuildEnv(self).vars().apply():
    cflags = os.environ.get("CFLAGS", "")
    ldflags = os.environ.get("LDFLAGS", "")
cmd = "make -j1"
if cflags:
    cmd += f" CFLAGS={shlex.quote(cflags)}"
if ldflags:
    cmd += f" LDFLAGS={shlex.quote(ldflags)}"
self.run(cmd, cwd=self.source_folder, env="conanbuild")
```

CC 仍走环境注入（上游 Makefile 未赋值 CC，环境 CC 生效）。

### 验证

- 修复后 `conan create`（ohos-aarch64 profile）编译命令行含工具链标志；
- `conan-verify hoedown 3.0.7` G0-G4 + L2/L4/L5 全部通过；
- W3 本地 CI 模拟（build_and_test.sh）L0-L5 全 pass。

## 查重差异（为何不与既有条目等价）

| 条目 | 差异 |
|------|------|
| E190 | Perl XS `Makefile.PL` 场景，显式传 CCFLAGS/LDDLFLAGS（同族"显式传参"思想，但工具链/构建入口不同） |
| E158 | GNUmakefile 缺 pkg-config 配置导致的缺头文件，非变量优先级问题 |
| R33 | "编译器/标志必须从 Conan Toolchain 获取"的约束原则；本条是该原则在纯 Makefile 库上的具体落地手法 |
| E540 | runner PATH 缺失（环境级），与 make 变量优先级无关 |

## 适用边界

- 无 configure 的纯 Makefile 库（bzip2/cd-hit/hoedown 类）。
- 有 configure 的 autotools 项目由 `autotools.configure()` 自行处理，不适用。

## 反例 / 限制

- 不要硬编码本机绝对路径标志（不可复现，R49 同族）。
- 不要用 `make -e`（环境全覆盖，副作用大）。
- 若 Makefile 使用 `override CFLAGS := ...`，命令行参数也会被覆盖——此时只能
  打补丁或改 build 方式，属另一类问题。
