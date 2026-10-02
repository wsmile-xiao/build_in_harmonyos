# DRAFT-conan-buildenv-user-conf-ohos：OHOS Conan 2.29.1 buildenv 不进 recipe 进程 + user conf 命名契约

> Contributor: input-utils-1.3 适配 | Status: Draft | Updated: 2026-09-26
> Source: archives/i/input-utils/1.3

## 现象

input-utils 1.3 在 OHOS 设备 CI（Conan 2.29.1）适配中观察到三个环境契约问题：

1. profile `[buildenv]` 声明的变量（sysroot、工具路径）不进入 recipe 进程的
   `os.environ`；recipe 顶层直接读取得到空值。
2. profile `[conf]` 段中单段 `user:<name>:<key>` 形式的 conf 键被**静默丢弃**
   （无任何告警），`self.conf.get` 返回 None。
3. 上游 GNUmakefile 的 install 目标依赖 `install(1)`，OHOS toybox 无此命令；
   上游 shell 脚本按 `/usr/include` 假设查找 `input-event-codes.h`，设备无此目录。
4. 官方 buildbot（conan-pr-check）环境不导出任何专用 env——
   `OHOS_SDK_SYSROOT` / `OHOS_SDK_NATIVE` 在官方仓 ci/conan/ 全目录
   grep 零命中（官方入口模拟 Run A 复现 name.sh /usr/include 报错）。
   依赖手工 env 注入的方案在官方 CI 上不可交付。

## 根因分析

- (a) Conan 2 的 `[buildenv]` 仅在 build 阶段 `conanbuild` 环境脚本及其子进程
  中生效，recipe 进程自身不消费它；bare `subprocess.run()` 与 `shutil.which`
  读到的是 recipe 原始 PATH。
- (b) user conf 必须两段式命名 `user.<org>:<key>`；单段形式不匹配内部解析
  规则即被丢弃，且无诊断输出。
- (c) 设备无 `install(1)`、无 `/usr/include`，任何宿主 Linux 假设都会在
  build/package 阶段显式失败。
- (d) 官方 CI 不注入 sysroot env，且 recipe 无法从 profile [buildenv] 顶层
  读到环境值 → sysroot 必须可在 recipe 内部自主获取（降级链），否则只在
  开发者手工 env 下"看起来能过"。

## 解决方案（input-utils 1.3 实证契约，round-19 三级 sysroot 契约，CI round-21 双口径 PASS）

1. sysroot 获取采用**三级降级契约**（能力探测，不写平台名硬编码）：
   - 第 1 级：专用 env `OHOS_SDK_SYSROOT`（若已设直接采纳）；
   - 第 2 级：`OHOS_SDK_NATIVE` 布局探测——`<sdk>/native` 下存在
     `sysroot/usr/include/` 目录时取 `<sdk>/native/sysroot`；
   - 第 3 级：build() 内 cc 自探测——cc 取 profile conf 整键
     `tools.build:compiler_executables`（`isinstance(dict)` 守卫），
     否则 `which(clang)` / `which(cc)` 兜底；优先 `<cc> -print-sysroot`
     （rc=0 且输出为真实目录才采纳）；clang < 16 无该 flag 时回退
     `<cc> -print-file-name=include` 得到资源 include 目录，从其父目录
     逐级上溯（≤8 级）寻找兄弟 `sysroot/`，且仅当
     `<sysroot>/usr/include/linux/input-event-codes.h` 实际存在才采纳；
   - 探测失败（无 cc / 探测不到 sysroot / 头文件缺失）：仅输出 info 日志，
     安全回退上游默认查找路径，不报错、不伪造、不改上游行为；env 优先级
     设计不变（env 命中即跳过探测）。
2. user conf 写 `user.<org>:<key>` 于 profile `[conf]` 段。
3. 上游脚本头文件路径假设用 env-var hook patch（`OHOS_INPUT_CODES` /
   `OHOS_INPUT_BUS_CODES`），未设 env 回退上游原逻辑。
4. `install(1)` 缺失 → recipe `package()` 用 `conan.tools.files.copy` 复现
   同一文件集（bin/share/man/licenses），遵循
   DRAFT-conan-copy-keep-path-nesting 的 pattern/keep_path 语义约束。

## 与既有条目的差异（去重声明）

- **E2150**（pkgconf 3.0.5，drafts/E2150-draft-2301.md）：E2150 描述 buildenv
  仅作用于 `self.run()` build scope、bare subprocess/shutil.which 读不到的
  **run() 作用域机制**，并给出机器可读 build-tool 查询的 run() 写法。本条是
  OHOS 设备 Conan 2.29.1 变体的具体表现 + **契约写法增量**：(b) user conf
  命名契约全库 0 命中为全新内容；(c) install(1)/sysroot env 契约为 E2150
  未涉及的打包与头文件层。E2150 只回答"buildenv 到不了哪里"，不回答
  "专用 env 缺失时 sysroot 如何经 cc 自探测降级获取"——三级契约为本条
  主体增量，非 E2150 的 run() 作用域主题。
- **E330**（PCRE2 10.47，drafts/E330-draft-2301.md）：仅含一句禁令 "Do not
  rely only on os.environ for profile buildenv values inside a Conan
  recipe"，主题是 noexec 树上 shell 能力探测与 Automake 分发。本条给出该
  禁令的完整机制解释 + user conf 命名契约 + 逐项修复契约，属不同问题类别。
- **E098**（鸿蒙缺 install 命令，cp+chmod 替代）：E098 是 make install 阶段
  的 shell 层替代；本条是 **Conan recipe 层** `copy()` 替代 `install(1)` 的
  配方模式与动机，且 env 契约/sysroot 部分不在 E098 范围内。
- **DRAFT-conan-copy-keep-path-nesting**：覆盖 copy 的 pattern/keep_path
  语义坑；本条只引用其语义约束，本身解决的是 install(1) 缺失的打包策略。
- **E238**（嵌入式 clang 头路径发现）：主题是 include 顺序保留（须保留目标
  sysroot 的探测顺序），非 sysroot 自动发现降级链；本条三级契约以 cc
  自探测（-print-sysroot / -print-file-name=include 上溯）为主题，与
  E238 互补不重叠。
- **E328**（CMake toolchain）：主题是 toolchain 文件不可被 env 部分替代；
  本条不是 toolchain 配置问题，且 E328 的 OHOS_NDK_HOME 邻接布局为静态
  约定，非 cc 探测。
- **E296**（Meson cross file）：sysroot 由 cross file 静态从路径推导注入，
  非 cc 自探测降级链；Meson 机制不同。

## 禁止做法

- 不要在 recipe 进程顶层用 `os.environ["OHOS_*"]` 或 `shutil.which` 作为
  buildenv 值来源（另见 E330 禁令）。
- 不要在 profile `[conf]` 段写单段 `user:<name>:<key>`（静默丢弃）。
- 不要在 recipe 中硬编码设备绝对路径（如 `/data/service/hnp/...`）；
  一律经 env/conf 注入并做存在性探测。

## 验证证据

- 双口径验证（round-21 权威 CI，两条均 rc=0）：
  - Run A（官方入口原样模拟，不导出任何专用 env）：rc=0，日志含
    "OHOS sysroot auto-detected via clang" 证据行——第 3 级 cc 自探测
    在官方 CI 真实触发并成功；
  - Run B（env 优先口径，export OHOS_SDK_SYSROOT）：rc=0 且日志零
    auto-detected 行——env 优先级未被第 3 级破坏。
- `conan create --build`（强制真实 build）："Apply patch (portability)"、
  Packaged 7 files + 3 .man、test_package 4/4 RUN（round-11-ci.log，281 行）。
- OHOS_SDK_SYSROOT / OHOS_INPUT_CODES / `user.<org>:` 全库（graph/drafts/doc/
  经验仓）0 命中，本条为主体增量；三级契约与"官方 buildbot 不导出 env"
  事实句经 Curator r7 / Auditor r7 双轮换词查重均 0 命中。

## 关联

E098、E219、E2150、E238、E296、E328、E330、DRAFT-conan-copy-keep-path-nesting。
最终编号 Exxx 由知识库主编确认。
