# socket-wrapper 1.4.1 HarmonyOS PC 移植设计

## 目标与范围

将官方 socket_wrapper 1.4.1 移植到 HarmonyOS PC（aarch64、musl、Clang），在
`archives/s/socket-wrapper/1.4.1/` 中交付可复现的 Conan 2 配方、必要的版本专用补丁、
上游测试记录和端到端消费者测试。交付物只覆盖 socket-wrapper；当前工作区中 snow、
libucontext、kcolorscheme、libXext 等本地改动不得被暂存、提交或覆盖。

本阶段不创建或推送 PR。完成本地验证后，仅在用户明确授权时才使用
`templates/积分赛事PR模板.md` 准备并提交 PR。

## 基线与参考

- 目标源码：`https://ftp.samba.org/pub/cwrap/socket_wrapper-1.4.1.tar.gz`
- SHA256：`390cc82a1b2103555cfd803bc1acbfeeed2b68cde081005b92cac78ec76554aa`
- 上游构建系统：CMake，`project(socket_wrapper VERSION 1.4.1 LANGUAGES C)`
- 直接参考：`upstream/feat/socket-wrapper-1.5.2` 中已经过 HarmonyOS PC 验证的
  socket-wrapper 1.5.2 配方、补丁、上游测试结果和消费者测试。
- 同族参考：仓库中的 pam-wrapper 与 nss-wrapper 配方，用于确认 cwrap 家族的 ELF
  签名和运行环境处理方式。

1.5.2 的八个补丁均不能直接应用于 1.4.1，且两个版本在 23 个源码文件上存在变化。
因此复用的是已经验证的平台结论和测试方法，而不是文件内容或补丁行号。

## 方案选择

采用“验证结论回迁”方案：先在未修改的 1.4.1 上得到编译或测试失败证据，再把 1.5.2
中对应的兼容性结论按 1.4.1 源码结构重新实现。相比从零摸索，该方案复用已知的 OHOS
平台事实；相比机械复制 1.5.2，它能避免版本差异造成的错误补丁和虚假测试结果。

## 依赖与打包模型

- `libsocket_wrapper.so` 和 `libsocket_wrapper_noop.so` 仅依赖 libc、线程库和动态加载器，
  不增加第三方运行时依赖。
- 上游 CTest 套件需要 `cmocka >= 1.1.0`。默认使用已在 1.5.2 案例中验证过的
  `cmocka/2.0.2` 作为 Conan `test_requires`，但实现前必须按 W0 使用
  `conan download --only-recipe` 和 OHOS profile 的 `conan install` 重新核验配方与二进制。
- socket_wrapper 必须以共享库形式工作，因为核心功能依赖 `LD_PRELOAD`；配方拒绝
  `shared=False`。
- `package_info()` 将 `socket_wrapper_noop` 暴露为链接库，并通过 runenv/buildenv 暴露
  `SOCKET_WRAPPER_LIB` 与库搜索路径。该软件不安装用户命令，因此不创建 `commands.json`。

## 适配边界

HarmonyOS 专用配置优先放入 Conan 的 OHOS 分支和 CMake 能力探测结果中。源码补丁只解决
不能由配方表达的真实源代码兼容问题，且使用能力宏而非在补丁新增行中注入 `__OHOS__`。

预期逐项验证以下 1.5.2 经验是否也适用于 1.4.1：

1. musl 在 `_GNU_SOURCE` 下将 `fopen64`、`open64`、`openat64` 定义为宏别名，拦截函数
   定义前需要安全地取消宏定义。
2. OHOS/musl 的 `recvmmsg`、`sendmmsg` 原型可能使用 `unsigned int flags`，需要能力探测
   和匹配的 typedef、包装函数及导出函数签名。
3. `/tmp` 不可写时，上游测试必须尊重 `TMPDIR`；socket 文件目录还必须足够短并位于允许
   AF_UNIX bind 的原生文件系统。
4. CMake 交叉编译的 try-compile 与 libc 探测结果需在 OHOS 配方中稳定化，避免把链接器
   或运行探针失败误判为 API 缺失。
5. HarmonyOS 执行或加载 ELF 前需要签名；上游测试二进制、测试辅助共享库和打包后的
   共享库都由配方统一签名。
6. cmocka 2.x 与旧版测试代码的符号/版本检测差异仅在 1.4.1 实际失败时修复。

每一项都以 1.4.1 的原始失败、编译器声明或设备探针为依据。未在 1.4.1 复现的问题不进入
补丁集。

## 文件职责

- `conanfile.py`：下载源码、应用补丁、生成 CMake 工具链、执行上游测试、安装和签名，
  并声明消费者可见的包信息。
- `conandata.yml`：记录官方源码 URL、真实 SHA256、cmocka 测试依赖及全部补丁元数据。
- `patches/*.patch`：仅存放在 1.4.1 上经失败驱动验证的源码兼容补丁。
- `test_package/conanfile.py`：消费刚生成的包，设置 `LD_PRELOAD`、运行目录和接口号后执行
  测试程序。
- `test_package/test_socket_wrapper.c`：完成 TCP bind/listen/connect/accept/send/recv，检查
  payload、对端 AF_INET 视图以及 `SOCKET_WRAPPER_DIR` 中生成的 AF_UNIX socket 文件。
- `test_package/CMakeLists.txt`：只负责构建消费者程序和传入被测共享库路径。
- `test_package/MANIFEST.yml`：如实申报 1.4.1 上游测试清点、运行命令、实测数量与结果。
- `manifest.yaml`、`notes.md`：记录版本元数据、构建选项、补丁理由、测试证据和平台限制。
- `reports/W0-report.md`、测试/CI 报告：保存依赖核验及验证结果。
- 软件级 `README.md`、`manifest.yaml`：仅在当前 `upstream/main` 尚不存在时创建，并登记
  1.4.1；不得照抄 1.5.2 的 `published` 状态。

## 测试策略

实施遵循失败先行：先建立能真实消费包的 `test_package`，确认配方缺失时验证失败；再写最小
配方。每个源码兼容改动都由原始编译错误、设备探针或上游测试失败触发，补丁完成后重跑同一
检查。

验证分为四层：

1. **静态与结构门禁**：Python 编译检查、YAML 解析、补丁 dry-run、`test_package` 完整性、
   分支/路径/源 URL/settings/测试实质性检查。
2. **上游测试**：先用 `ctest -N` 记录 1.4.1 实际注册数量，再在 HarmonyOS 6.0 虚拟机
   单线程运行全部 CTest。任何排除项必须附未拦截的独立系统探针或明确平台缺失证据；不得
   直接沿用 1.5.2 的三个排除项。
3. **Conan 消费者测试**：`conan create` 必须构建、打包并运行 LD_PRELOAD 回环重定向测试，
   不能用只打印字符串的空壳测试。
4. **本地 CI 同源验证**：在 HarmonyOS 6.0 虚拟机执行
   `CI_PACKAGES="archives/s/socket-wrapper/1.4.1" zsh ci/conan/build_and_test.sh`，随后通过
   `ohc-run.py finish socket-wrapper 1.4.1 built` 的 W2/W3 门禁。`.ci-result.json` 只能由
   finish 生成，不手工创建或修改。

成功标准是：依赖预检通过、配方从官方源码可重复构建、上游测试结果有完整清点与解释、
test_package 端到端通过、本地 CI 脚本退出码为 0、无 P0/P1 本地审计问题，并且 Git diff
只包含 socket-wrapper 1.4.1 的允许归档文件。

## 错误处理与止损

- 编译或测试失败先查询历史归档与知识图谱，再按错误证据修复。
- 同类配方调参连续五次仍失败时停止盲试并整理失败证据。
- 制品仓或官方源连续三次不可达且跨度超过 30 分钟时按外部依赖阻塞处理，不伪造结果。
- 虚拟机连接信息在进入设备验证前向用户索取；没有设备实测不得宣称 HarmonyOS 验证通过。
- 不删除、不覆盖、不提交当前工作区其他软件的本地改动；需要消除 W2 多包干扰时只做可恢复
  的路径限定暂存，并在验证后恢复。
