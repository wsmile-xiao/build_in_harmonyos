# Meson 在 OHOS 无头设备上的工具链缺口：无 `meson` 可执行入口与 pkgconf 二进制名差异

- **草稿 ID**: DRAFT-libtypec-0.6.0-meson-ohos-missing-meson-launcher-and-pkgconf-name
- **来源**: libtypec 0.6.0 HarmonyOS PC 适配（Meson + PkgConfigDeps + eudev）
- **分类**: meson / conan / pkg-config / ohos / headless-toolchain
- **状态**: 本地草稿（路径 B 知识库扩展）

## 问题 / 错误签名

在 OHOS PC（aarch64，无 root、headless 构建机）上用 Meson 构建一个依赖
`dependency('libudev')` 的 C 库时，连续踩到三个表面不同、实为同一类的工具链缺口：

1. **meson 不在 PATH**：`meson setup ...` 报
   `sh: meson: inaccessible or not found`（conan build() 退出码 127）。
   但设备上 `python3 -m mesonbuild.mesonmain --version` 正常输出 1.11.2——
   meson 只装成了 python 模块，没有生成 console script `meson`。
2. **找不到 pkg-config**：meson configure 走到依赖探测时报
   ```
   Did not find pkg-config by name 'pkg-config'
   Found pkg-config: NO
   Run-time dependency libudev found: NO (tried cmake)
   ../meson.build:13:0: ERROR: Dependency lookup for libudev with method 'pkg-config'
   failed: Pkg-config for machine host machine not found. Giving up.
   ```
   即便配方里已经 `PkgConfigDeps(self).generate()` 生成了 `libudev.pc`。
3. **pkgconf 二进制名不是 pkg-config**：配方加了 `tool_requires("pkgconf/3.0.5")`，
   conan 也把它的 bin/ 加进了 PATH，但 meson 仍报 "Found pkg-config: NO"——
   因为该包提供的可执行文件叫 `pkgconf`，不叫 `pkg-config`，而 meson 默认按
   `pkg-config` 这个名字查找。

附带第四个环境坑（非 Meson 专属）：clang 临时目录默认 `/tmp`，OHOS 上 `/tmp`
只读，报 `unable to make temporary file: Read-only file system`。

## 根因

1. **meson 的 console script 缺失**：设备上 meson 由 pip 装入 python3.12 的
   site-packages，但 `bin/` 下没有 entry point（或 entry point 未加入 PATH）。
   Meson(self) 工具类直接 `exec meson`，找不到就 127。
2. **headless OHOS 无系统 pkg-config**：系统镜像没有 pkg-config/pkgconf 二进制，
   也没有 `/usr/lib/pkgconfig/*.pc`。PkgConfigDeps 只负责在 generators/ 目录生成
   `.pc` 文件并设置 `PKG_CONFIG_PATH`，它**不会**提供 `pkg-config` 这个可执行程序
   本身。meson 的 `dependency()` 必须 fork 出 `pkg-config` 进程去读 .pc。
3. **pkgconf 包的二进制命名**：ConanCenter / ohpcd 的 `pkgconf` 包构建出的可执行
   文件是 `pkgconf`（上游项目名），不提供 `pkg-config` 兼容名。meson 有一个
   `PKG_CONFIG` 环境变量可以指定替代二进制路径，但默认找 `pkg-config`。

## 最小修复方案

在 `archives/<首字母>/<库名>/<版本>/conanfile.py` 中：

```python
def build_requirements(self):
    # 提供 pkg-config 二进制（ohpcd 上无系统 pkg-config）
    self.tool_requires("pkgconf/3.0.5")

def generate(self):
    PkgConfigDeps(self).generate()
    tc = MesonToolchain(self)
    tc.generate()
    # pkgconf 包的二进制叫 pkgconf，meson 默认找 pkg-config；显式指过去
    os.environ["PKG_CONFIG"] = "pkgconf"
```

再在设备 PATH 上补一个 `meson` 包装（一次性环境修复，非配方内容）：

```sh
# $HOME/usr/local/bin/meson
#!/bin/sh
exec python3 -m mesonbuild.mesonmain "$@"
```

构建命令同时把 TMPDIR 指到可写目录：

```bash
export TMPDIR=$HOME/tmp   # OHOS /tmp 只读
env NINJAFLAGS="-j4" conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

## 实际验证结果

- **设备**: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，clang 15，conan 2.31.1）
- **meson**: 1.11.2（python 模块 + 上述包装）
- **依赖**: eudev/3.2.14（PkgConfigDeps 注入 libudev.pc，经 `pkgconf` 解析成功）
- **构建**: `libtypec.so.0.6.0` + 软链链接成功，configure/build/install 全绿
- **消费者**: 2 个 C 消费者真机通过——
  1. `test_libtypec`：init 后版本串 `"libtypec 0.6.0"`；
  2. `test_query`：调 `libtypec_get_capability`/`libtypec_get_conn_capability(0)`
     返回 -1（无 /sys/class/typec）但进程不崩溃。
- **上游测试通过率**: 0/0 = N/A（上游 meson.build 无任何 `test()` 注册；utils/ 下
  lstypec 等工具需真实 Type-C 硬件，未构建）

## 适用范围

- 用 **Meson** 作为构建系统、且通过 `dependency(<name>)` + pkg-config 探测依赖的
  C/C++ 库（尤其是依赖 eudev/libudev、glib、gstreamer 等走 .pc 的库）。
- 在 OHOS PC headless 构建机上：系统镜像不带 `meson` console script、不带
  `pkg-config` 二进制。
- 依赖通过 `tool_requires` 提供（如 pkgconf/3.0.5）的离线制品仓场景。

## 非适用边界

- CMake 项目：走 CMakeDeps/find_package，不经过 pkg-config 进程。
- 构建机上已经装了系统 `pkg-config` 与 `meson`（如标准 CI runner）：无需此补丁。
- 依赖不通过 pkg-config 暴露（纯 CMake config-file 包）：不需要 PkgConfigDeps。
- 交叉编译从 Linux x86 runner：TMPDIR 通常可写，不用改。

## 查重差异

- 与 `DRAFT-libwebcam-0.2.5-...-pkgconfig-inject`（CMake + pkg_check_modules 手动注入
  INCLUDE/LIBRARY 变量）不同：本条是 **Meson 工具链自身缺失**（meson 入口 +
  pkg-config 二进制 + pkgconf 命名），不改上游构建逻辑，靠 PkgConfigDeps +
  `PKG_CONFIG=pkgconf` 环境变量解决。
- 与通用 "pkg-config 不可用" 条目互补：明确指出 **PkgConfigDeps 生成 .pc 不等于
  提供 pkg-config 可执行程序**，这是最常见的误判。

## 关联交付

- 本草稿与 `archives/l/libtypec/0.6.0/**` 属于同一交付。
- 正式 E 编号由知识库主编审核后分配。

## 禁止模式

1. **以为 PkgConfigDeps 就够了**：
   ```python
   # ❌ 仍会 "Found pkg-config: NO"
   def generate(self):
       PkgConfigDeps(self).generate()   # 只生成 .pc，不提供 pkg-config 二进制
   ```
2. **给 pkgconf 起错名字期望 meson 自动发现**：
   ```python
   # ❌ tool_requires 提供的是 pkgconf，不是 pkg-config
   self.tool_requires("pkgconf/3.0.5")   # 但还要 os.environ["PKG_CONFIG"]="pkgconf"
   ```

## 推荐模式

```python
def build_requirements(self):
    self.tool_requires("pkgconf/3.0.5")   # 提供 pkg-config 可执行程序

def generate(self):
    PkgConfigDeps(self).generate()
    MesonToolchain(self).generate()
    os.environ["PKG_CONFIG"] = "pkgconf"   # meson 默认找 pkg-config，指过去
```

## 关联原则

- P010：尊重上游 meson.build 的 dependency() 探测，用 Conan/PkgConfigDeps 注入而非改写。
- P020：消费者测试必须真实链接并调用库（本例两个 C 消费者均真机运行）。
