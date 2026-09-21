# DRAFT-ada-gnats-native-only-toolchain-cross-build-trap

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-17
> **Severity**: 🔴 high | **Category**: toolchain / ada / cross-build / dependency
> **Source**: task #13329 `libncursesada@6.3.20211021`（Ada 绑定，autotools）

## 使用说明（何时用）

当目标库的语言是 **Ada**，或 `build_requirements()` 里要引入的工具链**只有目标平台制品**时：

1. 先查 settings，而不是先试编译：
   ```
   $ conan list "gcc-ada/9.5.0:*" -r=ohpcd
                 settings
                   arch: armv8
                   os: OHOS          <- 只有 OHOS/armv8，没有 Linux 交叉版
   ```
2. 只要 `cross_building(self)` 为真（WSL 用 `-pr:b=default`），就在 `validate()` 里**尽早拒绝**，
   并在异常信息里给出正确命令，而不是留给链接阶段的晦涩报错。
3. 构建/交付一律用**原生两 profile**（`ci/conan/profiles/ohos-aarch64` 头部注释原文）：
   ```
   conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   ```

## 适用范围

- **直接**：Ada/GNAT（`gcc-ada`）；实测同为 OHOS/armv8 的还有 `binutils/2.46.0`、`gcc/9.5.0`、`flang-ohos/20.1.0`。
- **同构**：任何 `tool_requires` 到"只有目标平台制品"的工具链的项目（Rust 工具链、交叉编译器、
  目标平台专用的代码生成器）。
- **不适用**：工具链在制品仓同时有宿主平台产物时——那才走常规交叉。

## 输入 / 输出定义

**输入**

| 项 | 说明 |
|---|---|
| host profile | 目标平台（本例 `os=OHOS, arch=armv8`） |
| build profile | 执行构建的平台（WSL 交叉为 `default` = Linux/x86_64） |
| 工具链 settings | `conan list "<pkg>:*" -r=ohpcd` 的 `os`/`arch` |

**输出 / 判定**

| 条件 | 结论 | 动作 |
|---|---|---|
| 工具链无 build 平台制品 且 `cross_building` | 交叉不可行 | `validate()` raise，给出原生两 profile 命令 |
| `cross_building` 为假（build==host） | 原生构建 | `tool_requires` 正常解析并执行 |
| Ada 库的 C 胶水 | 必须与 Ada 同源 | `generate()` 覆写 `CC`/`CXX` 回 `gcc`/`g++` |

## 示例

```python
from conan.tools.build import cross_building
from conan.tools.gnu import AutotoolsToolchain

def build_requirements(self):
    self.tool_requires("gcc-ada/9.5.0")     # GNAT 编译器
    self.tool_requires("binutils/2.46.0")   # as / ld（gcc-ada 包内不含）

def validate(self):
    if cross_building(self):
        raise ConanInvalidConfiguration(
            "requires a NATIVE OHOS build: gcc-ada/binutils are OHOS/armv8 "
            "binaries. Use -pr:h=ci/conan/profiles/ohos-aarch64 "
            "-pr:b=ci/conan/profiles/ohos-aarch64")

def generate(self):
    tc = AutotoolsToolchain(self)
    env = tc.environment()
    env.define("CC", "gcc")     # 否则 profile 注入的 OHOS clang 抢先
    env.define("CXX", "g++")
    tc.generate(env)
```

典型报错序列（若不做上述处理，会依次撞上）：

```
# 1) 交叉 profile 下 tool_requires 解析失败
ERROR: ConanInvalidConfiguration: gcc-ada is prepared for a native OHOS build only
# 2) 缺 binutils 时
gcc.real: fatal error: cannot execute "as": execvp: No such file or directory
# 3) 缺 ADA_INCLUDE_PATH 时
fatal error, run-time library not installed correctly / cannot locate file system.ads
# 4) 缺 /bin/sh（用了 bin/gcc proxy）时
gcc-ada shell proxy: No such file or directory
```

## 查重差异表

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-gcc-ada-ohos-link-only-libunwind` | 草稿 | gcc-ada **链接期** libunwind 注入缺失 | 非本题 —— 那是编译器包**内部**的链接契约；本条是**能否/在哪构建**的前置判定 |
| `DRAFT-gcc-ada-ohos-xpm-seed-loader` | 草稿 | Ada 前端自举需要 Alpine GNAT seed | 非本题 —— 那是 **gcc-ada 自身的构建**方式；本条是**消费方**如何选对 profile |
| `DRAFT-flang-minimal-runtime-link-contract` | 草稿 | flang-ohos 最小运行库链接契约 | 相邻但不同 —— 本条覆盖"同为 OHOS/armv8 工具链"的**共性判定规则**，不限于 Fortran |
| `DRAFT-below-ohos-unsigned-rust-toolchain` | 草稿 | Rust 工具链无签名 | 相邻 —— 同属"工具链仅目标平台可得"，本条给出**统一判定 + 报错口径** |
| E001 / E012（toolchain not found） | 正式 | 编译器/`ar` 找不到 | 非本题 —— 那是 PATH/环境变量问题，本条是**制品仓根本没有宿主平台产物** |

> 全库查证（2026-09-17）：`knowledge/` 全文检索 `native OHOS build only` / `cross_building` /
> `tool_requires.*OHOS/armv8` 等关键词，**无正面撞车**；本条为真增量。

## 验证证据

**① 制品仓 settings（决定性证据）**

```
$ conan list "gcc-ada/9.5.0:*" -r=ohpcd
ohpcd  gcc-ada/9.5.0  6b129b068851896169fae42d399fa922d239ce8a
         settings: arch: armv8, os: OHOS, compiler: clang 15, libcxx: libc++, build_type: Release
$ conan list "binutils/2.46.0:*" -r=ohpcd     # 同为 os: OHOS / arch: armv8
$ conan list "gcc/9.5.0:*"        -r=ohpcd     # 同为 os: OHOS / arch: armv8
```

**② 工具链包内没有汇编器/链接器**（`as`/`ld` 必须来自 binutils）

```
$ <gcc-ada>/bin/gcc.real -print-prog-name=as
as
$ ls <gcc-ada>/bin            # 25 个条目：gcc.real/gcc.ohos-wrapper/gnatmake/gnatbind/gnatlink/... 无 as/ld
```

**③ CI 用的是原生两 profile**

```
$ sed -n "14,15p" ci/conan/profiles/ohos-aarch64
#   conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

**④ 本地执行通路（fallback）实测**

- `qemu-aarch64-static` 直接跑 `gnatmake --version` → `GNATMAKE 9.5.0` ✅（gnatmake 为静态链接）
- 动态的 `gcc.real`/`cc1`/`gnat1` 需 `/lib/ld-musl-aarch64.so.1`；SDK 的 `libc.so`（72 KB，static-pie）当 loader 会 **segfault**；
  换 musl loader 后 `gcc.real --version` → `gcc.real (GCC) 9.5.0` ✅
- 缺 `-isystem <sysroot>/usr/include/aarch64-linux-ohos` → `fatal error: bits/alltypes.h: No such file or directory`；补上即通过
- GNU `ld` 在 qemu+proot 下报 `cannot find crt1.o: Invalid argument`；换 SDK 自带 host-native `ld.lld` 后链接成功
- 端到端：`gnatmake main.adb` → `qemu-aarch64-static -L <root> ./main` → `ADA_OK`，产物 `ELF 64-bit ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1`
- **局限**：`gcc.ohos-wrapper` 注入设备绝对路径 `/data/service/hnp/.../libunwind.a`，proot 的 bind 对嵌套 exec 出的 qemu 进程不可见
  → 本地可完成编译与 `gnatbind`，链接阶段以 CI 为准

## 平台侧修法建议

1. `validate()` 的报错信息应**直接给出可复制的原生两 profile 命令**（本条目已采用），减少一轮试错；
2. 这类"仅目标平台可得"的工具链包，其 recipe 的 `validate()` 信息建议统一注明"需要 build==host"；
3. 若平台希望支持宿主侧交叉编 Ada，需要一个真正的 Linux→aarch64-linux-ohos Ada 交叉工具链制品
   （当前不存在；Ada 前端无法由 C-only 编译器构建，需 seed 自举）。
