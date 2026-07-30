# SDL2_net 2.2.0 高难适配说明与复现证据

## 1. 文档用途

本文是 DOSBox Staging 0.82.2-r1 前置依赖 SDL2_net 2.2.0 的 Path C
举证文档。它绑定当前配方、补丁、测试清单和本地验证证据，供依赖 Issue
`#1349` 与依赖 PR `#3164` 引用。本文不替代原始日志，也不把交叉编译或
链接结果写成目标端运行通过。

## 2. 上游身份与适配范围

- 上游仓库：`https://github.com/libsdl-org/SDL_net`
- 正式源码包：`SDL2_net-2.2.0.tar.gz`
- 源码 SHA-256：
  `4e4a891988316271974ff4e9585ed1ef729a123d22c08bd473129179dc857feb`
- 上游核心实现：`SDLnet.c`、`SDLnetTCP.c`、`SDLnetUDP.c`、
  `SDLnetselect.c`，SDK 12 shared/static 均完成 `4/4` 编译。
- 唯一上游自动消费入口：`cmake/test/main.c`。shared/static 目标使用相同
  源码和输入，因此只计 `1` 个独立入口。
- `showinterfaces`、`chat`、`chatd` 是示例程序，不计入自动测试。
- 下游关系：DOSBox Staging 需要 SDL2_net；本配方又精确依赖
  `sdl2/2.30.10`，并要求两个包的 `shared` 选项一致。

## 3. Path C 逐项举证

### 3.1 多层构建与包元数据耦合

该库不是只把四个 C 文件编译为一个库。交付同时要求以下契约成立：

1. 上游 CMake 在 OHOS/HarmonyOS 上能生成正确的共享库规则。
2. shared 模式生成一个真实 `libSDL2_net.so`，SONAME 也是无路径的
   `libSDL2_net.so`，不能依赖版本别名链。
3. static 模式只生成 `libSDL2_net.a`，不能混入共享产物。
4. Conan 的 `SDL2_net::SDL2_net` 与 `SDL2_net::SDL2_net-static` 目标必须
   分别绑定 `SDL2::SDL2` 与 `SDL2::SDL2-static`。
5. `cpp_info.requires = ["sdl2::sdl2"]`、头文件目录和传递链接信息必须让
   下游在不手工添加系统路径的情况下完成查找、编译和链接。

这些条件跨越上游 CMake、Conan 组件模型、依赖选项传播和最终 ELF 元数据，
任何一层错误都可能只在下游消费时暴露。

### 3.2 文件系统上的共享库形态修正

上游 `CMakeLists.txt` 在 UNIX shared 模式同时设置版本化输出名并创建额外的
无版本别名。SDK 12 的未修改构建在安装阶段复现了重复无版本目标问题，日志：

```text
cmake-sdk12-unpatched-install-r1.log
SHA256 49903a3dd6f57c5145b3af6e0b790653552ca9698e1962052c973fb4ccc632d3
```

补丁 `patches/0001-CMakeLists.txt.patch` 仅在
`CMAKE_SYSTEM_NAME` 为 `OHOS` 或 `HarmonyOS` 时关闭 `VERSION`、
`SOVERSION`、版本化 `OUTPUT_NAME` 以及额外别名安装。其他平台保留原上游
行为。补丁后 shared 与 static 安装日志分别为：

```text
cmake-sdk12-patched-install-r1.log
SHA256 c0a3d6b5126b64915c2cd706a8f6254ea8ab18daa95341a0e531da69a53e2015

cmake-sdk12-patched-static-install-r4.log
SHA256 6e195c6f2450bee310b54eec5592163f706d478ce348debd99e14d6dd3f80b42
```

这是平台限定的产物语义修复，不是空实现，也没有改变网络 API。

### 3.3 目标工具与最终 ELF 处理

native OHOS 包装路径需要在 CMake 安装完成后处理最终共享库；测试路径则在
每个 consumer 完成链接后处理最终可执行文件。配方具备以下失败关闭条件：

- 从 Conan 编译器配置、编译器相邻目录、HNP 目录和 PATH 中解析版本匹配的
  `llvm-readelf`、`llvm-objcopy` 与 `binary-sign-tool`。
- 输入缺失、工具失败、多于一个目标节、空目标节或临时路径冲突均立即失败。
- 已有且非空的单一目标节保留；否则生成独立输出，回读验证后原子替换。
- 成功与失败路径都清理临时文件，失败时不覆盖原始 ELF。

本地模拟工具正向/负向夹具和 6 个候选变异均通过预期判定。它们只验证流程
契约，不冒充真实目标工具运行。

### 3.4 独立网络消费者矩阵

适配后的 7 个可执行入口一一对应 7 个源文件、7 个 CMake target、7 个
Conan 执行名和 MANIFEST 条目：

1. `test_upstream_cmake_consumer`：上游 installed-package consumer 的
   字节一致副本。
2. `test_init_version_byteorder`：初始化、版本和 16/32 位网络字节序。
3. `test_packet_boundaries`：最小分配、扩容和 packet vector 生命周期。
4. `test_resolve_errors`：过长主机名失败、loopback 与 wildcard 地址转换。
5. `test_udp_loopback`：本机 UDP 发送、接收和载荷验证。
6. `test_tcp_loopback`：本机 TCP 监听、连接、接受和双向载荷验证。
7. `test_socket_set`：socket set 添加、就绪、接收、删除和清理。

TCP/UDP 只使用 `127.0.0.1`。内部断言、同一输入的 shared/static 重复构建
和重复执行均不增加用例数。

## 4. 失败演进、根因与实现取舍

| 阶段 | 现象 | 根因 | 处理与取舍 |
|---|---|---|---|
| 历史归档审计 | 旧记录含 Autotools 平台补丁 | 当前正式配方使用上游 CMake | 删除无关旧补丁，不沿用不可证明的历史结果 |
| SDK 12 未修改 shared 安装 | 无版本目标重复 | UNIX 版本化输出和额外别名安装同时生效 | 只为 OHOS/HarmonyOS 关闭版本链 |
| 元数据消费 | SDL2_net 导出目标依赖 SDL2 目标 | 上游配置文件不主动加载 SDL2 依赖 | test_package 显式查找两包并验证目标来自预期包根 |
| shared/static 依赖图 | 两层包模式可能不一致 | SDL2_net 与 SDL2 的 ABI 模式必须成对 | recipe 传播选项，test recipe 再次硬校验 |
| 历史交叉运行 | 目标程序不可直接在宿主执行 | r35/r36 仅为交叉构建 | 保留 `NOT_RUN` 历史边界，不计运行通过 |
| r27 目标运行 | fresh Conan home 无法解析冻结 SDL2 包 | r30 仅保留已验证包树，未保留完整 Conan 索引 | 以 `harness/conanfile.py` 导入精确包树，再构建并执行 SDL2_net |

## 5. 完整测试入口与真实结果

| 范围 | 独立入口 | 宿主 fresh | OHOS 交叉编译/链接 | 目标端运行 |
|---|---:|---:|---:|---:|
| 上游 installed consumer | 1 | `1/1 PASS` | shared/static 均 `1/1` link | `1/1 PASS` |
| 适配新增 consumers | 6 | `6/6 PASS` | shared/static 均 `6/6` link | `6/6 PASS` |

宿主 r15 从不存在的输出根启动一次，校验官方 SDL2 与 SDL2_net 源码包后
重新解压、构建并执行 7 个精确入口。关键闭包：

```text
complete SHA256 3669198e06cc2e6694c718baba2bb7e98eed7abe140797646c28dc350141b82f
terminal SHA256 c3cd666e6cf23c7242e716546c9acb1befc8621536fbc439a85bb4058ac728d1
evidence manifest SHA256 d930e35f8abd16ac4f3a099e890c15f6936ce58790866a7c928d85148b35d2d2
```

OHOS shared r35 与 static r36 均从源码创建 SDL2、SDL2_net 包并链接同一组
7 个 AArch64 consumer。它们绑定冻结的本地 SDL2 候选，而不是已发布制品：

```text
SDL2 HEAD d7db0575394853b3726eda4b8e1fbbebdfc05f5b
SDL2 tree 21a62e26f745ebdb94bde567be94b6484d8523bb
shared r35 log SHA256 607812e781ff0677d1db810ed0d2956680d4545baf2b455bfda17c00902a0b56
shared r35 binding SHA256 7cc485ab80e7025b21a4ed1d2e5b63651b78c492f8697e2331e31b504189c903
shared r35 complete SHA256 ff414b2e13b03dbd4fe353f8bba65f38aafcd42d2dfcb6573ebc59f56add8df9
static r36 log SHA256 81a87c9390b843bb2051e7af52f771a618f2d525fe65cf6fb7390d2d4aaa01cd
static r36 binding SHA256 37cf1cb21577494dc152ba5ea291e81b6d36f408794c976492b8a97a44648d1f
static r36 complete SHA256 5fad7aaa8b066c7f98702f52bfd76dd2fe6aa4f0fdb6c86401d888f83fbf6b6a
target r27 shared execution 7/7 PASS
target r27 static execution 7/7 PASS
logical upstream 1/1 PASS
logical adapted 6/6 PASS
evidence manifest SHA256 7c00d97af51a2c56e1fe8b10d9bf78391eac8c684843855b358e9610a08d3122
release-chain W3 BLOCKED_UNTIL_SDL2_2_30_10_PUBLISHED
```

只读联合验证器已校验 r35/r36 的 recipe、binding、log、exit、complete 和
consumer 哈希闭包，SHA256 为
`db8fdc5a44973595db1881167213d14e3381102c54b35d90955c0bb5db90a291`。
旧 W4 绑定的是更早的候选，已过期。本文和证据更新提交后必须由独立 W4
重新绑定最终 HEAD；在此之前不声明当前候选已通过 W4。

## 6. 复现步骤

1. 校验 `conandata.yml` 中正式源码 SHA-256。
2. 使用 OHOS arm64 profile 分别创建 shared 与 static 包，并确保
   `sdl2/2.30.10` 的 `shared` 选项与本包一致。
3. 对 shared 包检查仅有一个真实 `libSDL2_net.so`，SONAME 不含路径。
4. 对 static 包检查只有 `libSDL2_net.a`，不含共享产物。
5. 运行 test_package 配置和构建，确认 7 个目标均从两个 Conan 包根解析。
6. 若 `can_run()` 为 false，终态必须为 `NOT_RUN`；不得写入 PASS。
7. 在目标端 fresh Conan home 中逐模式执行 7 个入口，要求唯一终态为
   `1/1` 上游加 `6/6` 新增，shared/static 重复执行不扩充逻辑计数。
8. 对候选文件、runner、终态和原始日志建立 SHA-256 清单，再运行独立 W4。

## 7. 目标验证边界

- 已证明：官方源码身份、补丁限定范围、冻结 SDL2 r30 包树下的 shared/static
  包创建、AArch64 编译链接、目标端上游 `1/1`、新增 `6/6`、两模式各
  `7/7` 执行，以及 171 文件证据闭包。
- 未证明：从发布制品仓 fresh 消费 `sdl2/2.30.10` 的 release-chain W3。
- 待完成：最终 HEAD 的独立 W4，要求 P0/P1 均为零。
- 不需要外部网络服务；运行测试仅使用本机 loopback。

## 8. 积分项说明

| 项目 | 本库事实 | 当前申报边界 |
|---|---|---|
| 测试框架/工具链（证明材料需 Wiki） | 建立 7 入口清单、fresh runner、唯一终态与哈希闭包 | 在正式 Wiki 页面发布前不把本报告单独当作已取得证明；本文可作为 Wiki 原稿 |
| 搭建服务 | 未搭建独立服务 | 不申报 |
| 资源与环境依赖 | 绑定官方 SDL2_net 源码和精确 SDL2 前置，并完成 shared/static 验证 | 可按规则申报，最终以 Issue/PR 审核为准 |

## 9. Issue 与 PR 引用文本

Issue `#1349` 与 PR `#3164` 应同时引用：

```text
Path C 详细举证：archives/s/sdl2_net/2.2.0/reports/high-difficulty-evidence.md
```

本库按高难认领规则使用 `【高难度挑战】` Issue 标题前缀；作为主库的前置
依赖，PR 标题仍使用 `【依赖项】` 前缀。本文不改变一库一 Issue、一库一 PR
的一一对应边界。
