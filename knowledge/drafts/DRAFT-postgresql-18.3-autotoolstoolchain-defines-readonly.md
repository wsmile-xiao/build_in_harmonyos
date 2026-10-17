# DRAFT-postgresql-18.3-autotoolstoolchain-defines-readonly

> 草稿知识项 — conan AutotoolsToolchain.defines 只读 property 陷阱
> 来源：postgresql 18.3 评审轮 R8 宏改写复验（fix/pg-7992-review，2026-09-04）
> 同 stem 配对：`knowledge/drafts/DRAFT-postgresql-18.3-autotoolstoolchain-defines-readonly.kv`

## 问题（现象 / error_signature）

- 配方 generate() 里 `tc.defines.extend(["HAVE_BROKEN_SHMGET", ...])` 无报错，
  但构建产物中所有守卫代码被编译剔除；
- 典型症状：W3 L2 冒烟 34/35 全绿，唯 `pg_upgrade --version` 失败：
  `could not look up effective user ID 20020085: user does not exist`
  （pg_upgrade 在选项解析早期即调 getpwuid；其余命令的 --version 路径
  不触达平台守卫代码）。

## 根因（root_cause）

1. `AutotoolsToolchain.defines` 是 **@property**，每次调用返回
   `[ndebug, gcc_cxx11_abi] + extra_defines + conf_flags` 拼接出的**新列表**；
   `tc.defines.extend([...])` 改的是临时列表，静默 no-op。
2. 真正进入 CPPFLAGS 的公共可变属性是 `tc.extra_defines`
   （`__init__` 中初始化的普通 list，见 autotoolstoolchain.py L39/L256/L305）。
3. 叠加陷阱：OHOS PC 系统 clang **原生预定义 `__OHOS__`**
   （`clang -dM -E -x c /dev/null` → `#define __OHOS__ 1`），历史
   `__OHOS__` 守卫补丁从未依赖显式注入即可工作——守卫宏一旦改名，
   注入链路断裂才暴露。

## 可复用方案（rec_approach: use-extra-defines-verify-injection）

1. 配方内注入宏一律 `tc.extra_defines.extend([...])`。
2. 守卫宏改名/重写后必须全量重建，并验证注入链路三处落点：
   - `build树/conan/conanautotoolstoolchain.sh` 的 `CPPFLAGS` 含 `-D<宏>`
   - `build树/build-release/src/Makefile.global` 的 `CPPFLAGS =` 行
   - configure 日志 `configure: using CPPFLAGS=...`
3. 冒烟全绿 ≠ 宏生效：挑一个**已知依赖守卫代码的运行期行为**做正测
   （本例：pg_upgrade --version 的 getpwuid 回退）。

## 适用条件

- conan 2.29.x（OHOS 适配版与上游同构）的 AutotoolsToolchain；
- 任何需要把 -D 宏注入 autotools 构建的配方；
- 把补丁守卫从编译器预定义宏（__OHOS__）改为自定义宏的 R8 合规改写。

## 反例（不适用场景）

- CMakeToolchain（preprocessor_definitions 是可直接赋值的普通属性）；
- 经 profile `[conf] tools.build:defines` 注入的场景（conf_flags 路径本身有效）。

## 验证证据（真实命令 + 结果）

- `grep -n defines .../conan/tools/gnu/autotoolstoolchain.py`
  → L39 `self.extra_defines = []`；L256 `def defines(self):`（property）；
  L305 `env.append("CPPFLAGS", ["-D{}".format(d) for d in self.defines])`
- 修复前：`conanautotoolstoolchain.sh` CPPFLAGS 仅 `-DNDEBUG`，
  Makefile.global `CPPFLAGS = -I... -DNDEBUG -D_GNU_SOURCE`（零 -D 宏）；
  `pg_upgrade --version` → user does not exist，L2 34/35。
- 修复后（extra_defines）：configure 日志
  `using CPPFLAGS=... -DHAVE_BROKEN_SHMGET -DHAVE_BROKEN_SHM_OPEN
  -DHAVE_BROKEN_GETPWUID -DHAVE_BROKEN_UMASK -DHAVE_NO_UNIX_SOCKETS ...`，
  L2 恢复 35/35。
- clang 预定义证据：`/data/service/hnp/bin/clang -dM -E -x c /dev/null`
  → `#define __OHOS__ 1` / `#define __OHOS_FAMILY__ 1`。

## 限制与恢复条件

- 基于本仓 conan 2.29.1（OHOS 适配版）源码实证；上游 conan 大版本若把
  defines 改为可写属性则本条失效（升级 conan 后复核 autotoolstoolchain.py）；
- MESON/CMAKE 构建体系不经此路径。
