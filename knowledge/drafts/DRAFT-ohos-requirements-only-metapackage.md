# DRAFT-ohos-requirements-only-metapackage：requirements-only 聚合元包的 Conan 配方模式与 CI 门禁语义（OHOS）

> Status: Draft | Updated: 2026-08-27 | Source: archives/a/astromatic/1.3（HarmonyOS PC 适配）
> 最终编号（Exxx）由知识库主编确认；字段遵循 knowledge/ 现有 schema（参照 E241/E255）与 ARCHIVE-SPEC。

## 问题

上游为发行版/套件的**聚合元包（metapackage）**（如 Debian 原生元包 astromatic 1.3）时：

- 上游 tarball **不含程序源码、构建系统或测试**，仅含打包元数据（debian/ 目录：
  changelog/control/copyright/lintian-overrides/rules/source/format）。
- 直接套用编译型配方模板（source() 下载 + build() 编译 + package() 装产物 + test_package
  链接/数据校验）会得到空 build()、伪造包数据，或把"上游零测试"错误声明为跳过/全通过。
- Conan 2.29 无 meta-package 枚举，`package_type` 只能取 `unknown`。
- CI 门禁对无产物元包表现为特殊语义：L1 NO_TESTS 白名单、L1e/L2 skip、L5 warn——若不在
  notes/manifest 显式声明，易被后续审核误判为"跳过既有测试"。

## 根因分析

元包的本质是**依赖聚合声明**而非软件制品：自身不产出 bin/ 或 lib/，其"适配"等于把上游依赖
清单（Debian control Recommends/Depends）映射为 Conan `requirements()`。OHOS 平台本身无新增
约束（无编译环节、无平台名硬编码分支），难点全在配方形态与 CI 语义声明。

## 配方模式（推荐方案）

1. **conanfile.py — requirements-only 配方**：
   - `package_type = "unknown"`（Conan 2.29 无 meta-package 枚举）；
   - `settings = "os", "compiler", "build_type", "arch"`（满足 L0p 四项门禁）；
   - 仅 `def requirements()`：逐项对齐上游依赖清单（astromatic 1.3 的 debian/control
     Recommends 7 项：missfits/psfex/scamp/source-extractor/stiff/swarp/weightwatcher）；
   - **无** `source()/build()/package()/generate()`；`package_info()` 声明空 bindirs
     （`self.cpp_info.bindirs = []`）；
   - 传递依赖版本冲突用 `override=True` 统一（astromatic 用 `fftw3f/3.3.9.1` override 统一
     psfex 钉的 3.3.9 与 scamp/source-extractor 钉的 3.3.9.1——同源同内容，后者仅版本递增标签，
     不改动已发布工具配方）。
2. **conandata.yml — 记录官方源但不下载**：仍声明官方源 URL + SHA256（CI source_trace/审计用），
   配方不调用 `get()`。astromatic 官方 tarball（salsa debian/1.3）
   sha256=056c0ff71adebc07d1fa48e871f044a8cf312fe6c75a32c4648c89f68823b4b7。
3. **无 commands.json**（元包无自身二进制，L0k 判库型不要求）。

## CI 门禁语义

- **L1 NO_TESTS 白名单的双语义**（`ci/config/no_official_test.txt`）：
  ①"上游测试与 OHOS 构建环境不兼容"（如需完整 Linux 桌面/网络/GUI，头部注释原义）；
  ②"上游官方零测试"（astromatic 属此类）。同一机制两种语义，白名单文件头部注释必须区分，
  否则后续库会误读（round-5 Web Review B-9 反向印证）。
  "上游官方零测试"须三源核验：官方 tarball 文件树（无测试文件/无 autopkgtest/debian/tests）
  + `debian/rules`（`%: dh $@` 仅打包）+ `debian/control`（Architecture: all / Multi-Arch: foreign）。
- **L1e skip**：`No standard artifact dirs found to sabotage`——元包无自身产物，R34 破坏性反向
  验证不适用；由依赖闭包冒烟承担验证职责。
- **L2 skip**：`no bin/ dir`——元包无自身二进制。
- **L5 warn**：`no artifacts found`——元包空产物预期（非失败，Build Summary Success 仍计 1）。
- **依赖闭包冒烟替代验证**：test_package 用 `VirtualRunEnv` + `env="conanrun"` 对依赖闭包全部
  二进制真实执行（--version/-v/--help）。关键反证：7 个二进制系统 PATH 上全部
  `NOT_ON_SYSTEM_PATH`（`command -v` 实测），证明冒烟验证的是元包 requires 闭包而非系统偶然命中。

## 4 个真实近邻草稿的机制差异（Curation Auditor 补证项，查重边界）

| 近邻草稿 | 主题 | 与 requirements-only 元包模式的机制差异 |
|---|---|---|
| DRAFT-conan-staticlib-transitive-headers.kv（sha256=60ca6eaa…，proposed E321） | static-library 包 traits 传播（headers=False）致消费者 CMakeDeps INCLUDE_DIRS 空 | **机制不同**：针对 `package_type=static-library` 的实际库产物与 traits 传播；本模式是 `package_type=unknown`、零产物，无 traits 可传播 |
| DRAFT-npm-ohos-nodejs-toolchain.kv/.md（sha256=737dbd0c…/5169b1c1…） | CI L1e/L2 产物探测 `find -name bin` 对 node_modules 嵌套 bin 误判 | **机制相反**：npm 包"有产物但探测错位"；元包"无产物致 L1e/L2 skip=预期"，两者不重叠 |
| E257-draft-2282.md（sha256=2bd3686e…） | L1e 破坏性反向验证（移走 lib/ 后消费者测试失败→证明测试依赖打包产物） | **机制相反**：有产物包上 L1e 正常工作；元包无产物致 L1e skip |
| E257-draft-4151.kv/.md（sha256=a374e3e7…/36be4987…） | Python 包 L1e 反向负验证 + VirtualRunEnv + 显式消费者执行 | **机制不同**：针对 Python 运行时模块（site-packages/PYTHONPATH）与 L1e 反向负验证；元包为无产物聚合配方、闭包冒烟为正向验证 |

## 适用对象

- Debian/发行版元包、套件聚合包、聚合库组（tarball 仅含打包元数据、无程序源码）。
- 与 E241（数据/规则清单型库，settings=None + 有制品）、E255（纯资源型数据包，有 build/package
  复制 share/）、E305（字体资源包，package_type=application + 有制品）的边界：这些"无编译但
  有制品"的模式均不覆盖"requirements-only 无产物聚合"。

## 验证证据（round-5 权威 CI，固定 delivery base 9a77f7cd7130ded03ffe3d7bf6a436d0b5ef0426）

- 候选：commit 1b7f28e506b1180a4eef4cbf2e39d8d7a8d1638c，tree ece756857e06ec3ba0114a253912b7791a0b6caa。
- conan create PASS：Build Summary Total=1 Success=1；元包 "No files in this package!" WARN 预期；
  依赖 10/10 Already installed（7 工具 + 传递依赖）。
- test_package 冒烟 7/7：OK missfits --help / psfex --help / scamp --version / sex --version /
  stiff -v / swarp --help / ww --help（CI 日志 sha256=1c981882a70c9f98b4ccb6c558d9a4be776ef1826964fab02f04f2942e4828d6；
  conan build 日志 sha256=51a11225b298bbff14b4bd8544c3adcaa2867584b657e8690779768a9aa892a5）。
- L1 skip=whitelisted / L1e skip=No standard artifact dirs / L2 skip=no bin/ / L5 warn=no artifacts found。
- 配方证据 sha256：conanfile.py=feb955fa0aa8bf137774983f0f6680d86f3d267d76a0114bf9177baa0c50eaf3、
  conandata.yml=1173ea76479baf3d0eef84e6745e475ab1e3295dd457759fa1bd47a676a76133、
  no_official_test.txt=6fb7c8f25e6be5bd301f56a920c0a23041feef7051d68227d4c600050d19da24、
  test_astromatic.py=5aeb98dda3978102b082d6c5a41aaf5c13656b70203559502aa5c29ce9161b9c。

## 禁止做法

- 不要为元包伪造 build()/package() 或空壳二进制/commands.json（假制品，违反 PR 原子性）。
- 不要把"上游零测试"写成"上游测试全通过"或"测试不适用"（须官方 tarball/rules/control 三源核验，
  写 FULL_PASS 属虚假口径）。
- 不要对元包的 L1e/L2 skip、L5 warn 不做说明（须在 notes/manifest 声明为元包预期）。

## 参考

- 配方：archives/a/astromatic/1.3（conanfile.py / conandata.yml / test_package / notes.md / README.md）。
- 上游官方：salsa.debian.org/debian-astro-team/astromatic，tag debian/1.3。
- 关联知识：E241 / E255 / E305（无编译但有制品）；4 个机制不同的 draft 近邻见上文表格。
