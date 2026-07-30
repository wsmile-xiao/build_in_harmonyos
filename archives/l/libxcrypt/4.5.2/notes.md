# libxcrypt 4.5.2 适配笔记

## 编译环境

- 目标平台: HarmonyOS 6.0 / aarch64
- 构建系统: Autotools + Libtool
- 编译器: Clang 15
- Conan: 2.29.1 OHOS 适配版
- 编译日期: 2026-07-19
- 状态: built（真机 Conan shared/static 均验证通过，未上传）

## 源码与依赖

- 官方源码: `https://github.com/besser82/libxcrypt/releases/download/v4.5.2/libxcrypt-4.5.2.tar.xz`
- SHA-256: `71513a31c01a428bccd5367a32fd95f115d6dac50fb5b60c779d5c7942aec071`
- 上游 tag commit: `db70b42bd7b2a5b00a8580c8dec0aa66791c950a`
- 第三方依赖: 无，仅运行时依赖系统 `libc.so`

W0 使用精确版本做只读下载/安装检查，远端不存在 `libxcrypt/4.5.2` 配方或二进制；本包又没有 Conan 依赖，因此可作为叶子包继续适配。

## 配方构建步骤

1. Conan 下载并校验官方 release tarball。
2. `apply_conandata_patches()` 按顺序应用七个自动生成补丁。
3. `AutotoolsToolchain` 生成编译器、shared/static、fPIC 和安装目录参数，并仅添加 `-Wno-error=language-extension-token`。
4. 通过显式 shell 调用生成的 `configure` 参数，避免直接执行 HMDFS 上的脚本。
5. `make -j1` 后运行完整 `make check`；`LOG_COMPILER` 在检测到同名 `.libs` ELF 时用 `/system/bin/sh` 运行 Libtool wrapper，其余测试直接执行。
6. `make install DESTDIR=<Conan package>`，删除不应发布的 `.la`，不对已签名 ELF 做 post-link 改写。

## 问题与根因

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | `config.guess` 无法识别平台 | 上游脚本没有 HarmonyOS 分支 | 补充 `__OHOS__` libc 检测和 `aarch64-unknown-linux-ohos` 输出 |
| 2 | `config.sub` 拒绝 shorthand | 上游已接受 `ohos*` 和 `linux-ohos*`，但没有 `ohos-linux` 规范化 | 仅增加缺失的 canonicalization 分支 |
| 3 | `config.status` 创建 `subs1.awk` 报 `Permission denied` | `umask 077` 与 HMDFS setgid/group 权限组合导致当前构建进程无法继续写入 | 只修改创建 `confXXXXXX` 临时目录的两处为 `umask 022` |
| 4 | 生成头文件/映射时 helper 报权限错误 | HMDFS 上不能依赖脚本文件自身的执行位 | `Makefile.am` 与发布包 `Makefile.in` 的 8 个调用均改为 `$(SHELL) move-if-change` |
| 5 | `asm volatile` 被 `-Werror` 提升为错误 | Clang 将 GNU asm token 报为 `-Wlanguage-extension-token` | 精确添加 `-Wno-error=language-extension-token`，保留其他 `-Werror` |
| 6 | `crypt-nested-call` 链接缺少 `explicit_bzero` | OHOS libc 不提供该符号，libxcrypt fallback 在共享 ELF 中是 hidden，而该测试遗漏 fallback 对象 | 给测试目标增加 `lib/libcrypt_la-util-xbzero.lo`，并同步生成文件依赖 |
| 7 | 初次 `make check` 大量 `Permission denied` | 失败来自 Libtool HMDFS wrapper 启动，不是密码算法失败 | 使用基于同名 `.libs` ELF 探测的 `LOG_COMPILER` launcher |
| 8 | `explicit-bzero` 在目标端返回 77 | 目标头文件存在 `ucontext.h`，但没有上游测试需要的上下文函数，因此 `USE_SWAPCONTEXT` 未定义 | 只在 OHOS 测试翻译单元中增加 pthread 独立栈后端，保留原三项死栈扫描及其判定 |
| 9 | `getrandom-fallbacks` 在目标端返回 77 | 目标 libc 提供 `arc4random_buf`，上游预处理分支跳过整个 fallback 测试 | 只在 OHOS 测试翻译单元中取消该特性宏并复用上游同一 fallback 实现，完整执行原失败链与断言 |

## 补丁说明

- `0001-Makefile.am.patch`: 源层修复 helper 启动，并补齐 `crypt-nested-call` fallback 对象。
- `0002-Makefile.in.patch`: release tarball 的生成文件对应修改；CI 不依赖 `autoreconf`。
- `0003-build-aux-m4-autogen-config.guess.patch`: HarmonyOS 平台和 libc 识别。
- `0004-build-aux-m4-autogen-config.sub.patch`: `ohos-linux` 到 `linux-ohos` 的最小规范化补丁。
- `0005-configure.patch`: 仅修改已由真机日志证明失败的两处临时目录 umask。
- `0006-test-explicit-bzero.c.patch`: 在缺少可用 ucontext 函数的 OHOS 目标上，为原上游死栈扫描补充 test-only pthread 独立栈后端；生产库代码不变。
- `0007-test-getrandom-fallbacks.c.patch`: 在 OHOS test-only 翻译单元中复用上游 fallback 实现，使已有 fallback 失败链在目标 libc 提供 `arc4random_buf` 时仍被执行；生产库代码不变。

补丁正文由 `refresh-patch --auto` 基于官方 tarball 的 pristine/work 双轨生成。Windows 原生生成器的路径分隔符与 hardlink 问题使用隔离副本排查，未修改仓库框架文件。

## 验证结果

2026-07-23 在 HarmonyOS 6.0/aarch64 真机上，以 fresh 且彼此隔离的 Conan home、源码树、构建树和临时目录执行完整上游测试。静态配置汇总为：

```text
TOTAL: 54
PASS:  54
SKIP:  0
FAIL:  0
```

原先两个条件性入口 `test/explicit-bzero` 与 `test/getrandom-fallbacks` 已通过仅限测试翻译单元的目标适配真实执行并得到 PASS。OHOS 的 `compute-symver-floor` 选择 `XCRYPT_2.0`，因此 obsolete API 测试不会进入该平台的 54 项唯一测试集合。

正式 Conan 双配置结果：

| 配置 | 上游 TOTAL | PASS | SKIP | FAIL | test_package |
|------|-----------:|-----:|-----:|-----:|--------------|
| `shared=False` | 54 | 54 | 0 | 0 | 同一消费者入口通过 |
| `shared=True` | 52 | 52 | 0 | 0 | 同一消费者入口通过 |

共享配置不选择仅用于静态符号校验的 `symbols-renames` 与 `symbols-static`；54 是两个配置的唯一上游测试集合，不把 shared/static 重复执行计为新增用例。

static 包只含 `libcrypt.a`，static 消费者 NEEDED 仅为 `libc.so`。shared 包只含三个 regular-file alias `libcrypt.so`、`libcrypt.so.2`、`libcrypt.so.2.0.0`，三者 SHA-256 相同；shared 消费者 NEEDED 为 `libcrypt.so.2` 与 `libc.so`，没有 RUNPATH。

本轮证据由目标端 runner 逐项读取 Automake `.trs` 的唯一 `test-result` 与 `global-test-result`，并要求同名原始 `.log`、`test-suite.log` 汇总和集合边界完全一致。回传后再次验证 238 个原始证据文件与 10 个汇总文件的 SHA-256，均无失败；独立校验器输出：

```text
VALIDATION_PASS: unique=54/54 static=54/54 shared=52/52 unexpected=0
```

完整回传包 SHA-256 为 `14580505eee37637d503537be1820c41d6c33707986a3091ccf5c09e041954dc`，结构化校验结果 SHA-256 为 `a683f6bf0e88af4fc30cff27c3dd774a4a8ae4624a3894e2406bb66f8e06e069`。详细方法、入口映射、补丁语义和计分材料见 `reports/high-difficulty-and-test-evidence.md`。

直接安装产物的 `libcrypt.so` SONAME 为 `libcrypt.so.2`，NEEDED 仅有 `libc.so`，没有 RUNPATH；ELF 包含 `.note.ohos.ident` 与 `.codesign`，真实共享库测试已成功加载。导出接口包括 `crypt*`、`crypt_gensalt*`、`crypt_checksalt` 与 `crypt_preferred_method`。

PR #3018 的后续消费者测试审计补充了关键前置条件保护：当
`crypt_preferred_method()`、`crypt_gensalt_rn()` 或 `crypt_r()` 失败时，测试在记录
原有失败判定后立即返回，不再把空指针或未初始化 setting 传给后续 API。修改后的同一
消费者用例在 HarmonyOS 6.0/aarch64 真机以 Clang 15 的
`-Wall -Wextra -Werror` 分别链接既有 static/shared 产物并通过；注入
`crypt_preferred_method() == NULL` 后进程按预期以 1 正常失败，没有崩溃。该保护不
拆分新用例，也不增加原有 12 个断言计数。

远端历史 HEAD `1b18820e` 的 Build #9159 在 `conan-setup` 阶段安装 Conan 2.29.1
时失败：社区 PyPI 能提供 Conan wheel，但缺少其 `requests>=2.25,<3` 传递依赖。
流水线尚未进入 libxcrypt 配方或测试，因此该结果属于 CI 环境安装失败，不能记为本包
构建或测试失败，也不能通过修改配方伪装成已修复。

## 技术债务与配套知识草稿

- 精确 warning demotion 属于工具链兼容参数；若上游将 `asm volatile` 改成标准 `__asm__ __volatile__`，可移除该参数。
- E232 知识草稿记录 HMDFS 上无扩展名 Libtool test wrapper 的条件启动：仅当同路径 `.libs/<basename>` ELF 存在时通过 `/system/bin/sh` 启动 wrapper，其余真实 ELF 直接执行，禁止把所有测试统一交给 shell。
- E233 知识草稿记录目标 libc 缺少 API 时的测试链接规则：库内 hidden fallback 不能自动满足独立测试目标，必须把准确的 fallback 对象加入该测试的 `LDADD`，不能跳过测试或改写预期。
- 两个新增测试补丁只改变目标端测试可执行路径，不进入安装产物；后续若上游直接提供等价的 pthread 栈后端或允许强制选择 fallback 测试，应优先收敛到上游实现。
- 两条草稿均以配套 `.kv`/`.md` 文件随本软件 PR 提交，由主编审核后提升；协作者不修改正式索引。
- 关联已有知识: `E007`、`E063`、`E087`、`E129`、`E232`、`E233`、`openharmony-pc-autotools-patchng-hmdfs`、`openharmony-pc-conan-library-shared-options`、`openharmony-pc-conan-test-virtual-run-env`。
