# pam-wrapper 1.1.8 高难度挑战候选举证

## 1. 申报范围

本文为 Issue `#1763`、PR `#4234` 的 Path C（高难度挑战）候选材料。它只覆盖
`pam-wrapper 1.1.8` 的 HarmonyOS PC 适配，不把前置依赖 `linux-pam/1.7.2` 的
工作量重复计入本 PR，也不预先声明最终等级或分值；最终分类以评审结果为准。

- 上游项目：`https://cwrap.org/pam_wrapper.html`
- 官方源码：`https://ftp.samba.org/pub/cwrap/pam_wrapper-1.1.8.tar.gz`
- SHA-256：`6549c0b3e41d1ebe0c94a1be63c25eec918191462b602ab6f47d4a5fa709c3e4`
- 构建系统：CMake
- 目标环境：HarmonyOS 6.0 / aarch64
- 直接依赖：`linux-pam/1.7.2`
- 测试依赖：`cmocka/2.0.2`，仅作为 Conan `test_requires`

## 2. 为什么不是普通编译适配

`pam-wrapper` 不是普通单共享库。一个有效交付同时包含并联动：

- `libpam_wrapper.so`：通过 `LD_PRELOAD` 拦截 PAM API；
- `libpamtest.so`：供测试程序调用的公开 C API；
- `pam_matrix.so` 等多个 PAM MODULE 目标；
- PAM service 文件、passdb 和私有 runtime 目录；
- 上游 CTest/CMocka 测试可执行文件及其 build-tree 动态模块。

因此，“编译出 `.so`”不能证明功能成立。验证必须让动态加载器、PAM 模块加载、
预加载初始化、服务配置、认证会话和目标端安全策略在同一个真实流程中闭环。

## 3. Path C 候选依据

### 3.1 多动态目标与 PAM 依赖契约

上游 CMake 原本直接使用 `pam`、`pam_misc` 和系统头搜索。HarmonyOS Conan
环境中，这会绕过锁定依赖或找不到目标包。适配需要同时修正 configure checks、
`pam_wrapper`、`pamtest`、四个 PAM modules 和上游 test target，使它们都使用
`linux-pam/1.7.2` 的精确 include/library 路径。

该问题复用 E223 draft 的“Conan 路径桥接到上游 CMake legacy 变量”模式，但
本 PR 还要保证同一组路径在库、MODULE 和测试目标之间一致，不能只让 configure
阶段通过。

### 3.2 LD_PRELOAD 的进程启动生命周期

`pam_wrapper` 在主程序进入 `main()` 前初始化，并复制
`PAM_WRAPPER_SERVICE_DIR`。所以测试程序内再创建 service/passdb 或修改环境已经
太晚。Conan `test()` 必须在 `exec` 前完成夹具创建，并把以下状态同时交给子进程：

- `LD_PRELOAD`
- `LD_LIBRARY_PATH`
- `PAM_WRAPPER_SERVICE_DIR`
- `PAM_WRAPPER_RUNTIME_DIR`
- `TMPDIR`

本次将该通用生命周期问题沉淀为
`DRAFT-pam-wrapper-preload-startup-context`（KV/MD 配套草稿）。消费者不仅检查
`dlopen`，还经 `libpamtest` 调用 `pam_matrix` 完成真实认证。

### 3.3 build-tree ELF 签名后执行上游测试

仅签名 package 目录中的最终 `.so` 不足以运行上游测试。CTest 实际加载的是
build tree 中的测试可执行文件、`pam_wrapper`/`pamtest` 和 PAM modules。配方在
CTest 前枚举真实 ELF，排除普通文件以外的候选，移除旧 `.codesign` 后重新签名；
工具缺失或任一签名失败立即终止，而不是静默跳过。

该步骤复用正式知识 E077，但把签名边界从“安装产物”扩展到“上游测试运行图”。
这也是最初可打包、但无法证明上游真实运行的关键差异。

### 3.4 默认执行完整上游目标

上游测试不再作为默认关闭的可选装饰：

- `with_upstream_tests=True` 为默认值；
- CMake `UNIT_TESTING=ON`；
- `cmocka/2.0.2` 作为不可见测试依赖，不污染运行时包依赖；
- CTest 先打印 inventory，再以 `--verbose -j1` 执行；
- 使用私有可写 `TMPDIR`，不依赖系统临时目录行为。

目标端实际完成 1/1 CTest target、23/23 CMocka cases，之后继续完成安装包消费者
认证流程。23 个 case 只按上游 case 计一次，shared 构建、内部断言和重复执行不扩充
数量。

## 4. 失败演进与修复边界

| 阶段 | 问题 | 根因 | 处理 |
|---|---|---|---|
| W0 | 仓库初始无可用 PAM 实现 | `pam-wrapper` 需要 PAM headers 和 `libpam` | 前置 `linux-pam/1.7.2` 独立适配，本 PR 只消费已发布依赖 |
| CMake configure/link | 系统 `pam`/`pam_misc` 搜索不可靠 | 上游 legacy 查找未绑定 Conan package | 四份逐文件 portability patch 注入精确 include/library 路径 |
| 消费者运行 | 进程内配置看似存在但 wrapper 使用旧状态 | 预加载库在 `main()` 前复制环境 | launcher 先创建 service/passdb，再带完整环境 exec |
| 上游 CTest | package 可签名，但 build-tree 测试图仍不可执行 | CTest 使用未处理的 build-tree ELF | 测试前枚举并签名 executable、shared libraries 和 modules |
| 测试门禁 | 上游套件默认关闭 | opt-in 测试不能证明默认交付 | 默认开启并使用 `test_requires`，失败直接阻断 build |

四份补丁只调整构建路径和目标连接，不修改上游
`tests/test_pam_wrapper.c` 的 case、输入或期望值，也没有跳过失败 case。

## 5. 测试统计与结果

| 范围 | 唯一入口/case | 结果 | 说明 |
|---|---:|---:|---|
| 上游 CTest target | 1 | 1/1 PASS | `test_pam_wrapper` |
| 上游 CMocka cases | 23 | 23/23 PASS | 不按内部断言重复计数 |
| 新增安装包 consumer | 1 | 1/1 PASS | `dlopen` + `run_pamtest` + `pam_matrix` 认证 |
| 仓库 CI | L0/L1/L4/L5 | PASS | L2 因 library package 无 `bin/` 正常跳过 |

证据：

- 真机运行目录：`/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-upstream-20260807-144624`
- CTest 日志 SHA-256：`9660199e69663db0bcced0d4bf802d3d6e318219030ecad4e731bd7806c9ed87`
- 仓库 CI 日志 SHA-256：`a181e7753188788ad47bd24a4196d2d68e47208a377d4949a9ba3370283d59c7`
- Conan verify 报告 SHA-256：`8c5d26bc22cc70ec7371e01ebd55639cb59a7ebc879a87aaf1731294e4b7a50e`

## 6. 知识库贡献

- 复用 E077：ELF 修改后移除旧签名并重新签名。
- 复用 E200：先确认 HarmonyOS/musl 的 `LD_PRELOAD` 能力。
- 复用 E223 draft：将 Conan 精确依赖路径桥接给上游 CMake legacy 查找。
- 新增 `DRAFT-pam-wrapper-ctest-elf-runtime-closure`：CTest 前必须签名构建树的
  完整 ELF 加载闭包，不能依赖稍后的 package-time 签名。
- 新增 `DRAFT-pam-wrapper-preload-startup-context`：预加载库在 `main()` 前捕获
  配置时，必须由 launcher 预创建夹具并在 `exec` 环境中一次性注入变量。

新知识以 `draft:true` 的 KV/MD 配套文件随软件 PR 提交，不修改正式
`knowledge/graph/index.tsv`，由知识库主编后续审核、合并或提升。

## 7. 申报边界

- 申请 Path C 高难度挑战候选，最终分类和分值由评审确认。
- 不把 `linux-pam/1.7.2` 的独立适配工作量重复计算。
- 不声明 Python binding 已验证；配方显式关闭其自动发现。
- 不声明 static 模式；`pam-wrapper` 的核心语义要求共享 interposition library。
- 不把 5 条 consumer 断言拆成 5 个新增测试流程。
- 不申报独立服务搭建；service 文件只是进程内 PAM 测试夹具。

## 8. 评审请求

请评审确认：多目标 PAM 动态加载图、`LD_PRELOAD` 的 pre-main 生命周期、
build-tree 全 ELF 签名、已发布 PAM 依赖桥接，以及 23/23 上游 case 加真实认证
consumer 的目标端闭环，是否满足 Path C 高难度挑战库候选要求。
