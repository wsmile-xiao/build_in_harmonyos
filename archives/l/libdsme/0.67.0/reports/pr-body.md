- **三方库名称**：libdsme（DSME "Device State Management Entity" 的 dsmesock 客户端协议库，附带 DSME 与 Thermal Manager 的 D-Bus 接口定义模块；提供 `dsmesock_*` 连接/收发/广播与 `dsmemsg_*` 消息工具）
- **上游版本**：0.67.0（上游 tag `0.67.0`，commit `67e57c5`，发布于 2024-10-02）
- **上游仓库地址**：https://github.com/sailfishos/libdsme （源码取官方 tag 归档 `https://github.com/sailfishos/libdsme/archive/refs/tags/0.67.0.tar.gz`，官方 HTTPS 源；sha256 `58908591d652f6505cebeb126664950cf9337d70a963b2f03cd6e80e91578e46`）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E002（`/tmp` 只读）、E046（HMDFS 权限/`chmod` 语义）为平台差异依据；本次新沉淀 3 条草稿（见"补充说明"）：抽象 AF_UNIX 套接字、libcheck 的 `TEMP` 探测顺序、toybox 缺 GNU `install(1)`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | `tests/ut_libdsme.c`（Check 框架，`tests/tests.xml` 注册）：`test_message`（消息分配/访问器契约）与 `test_send_receive`（对 mock daemon 的 connect/broadcast/receive/extra 往返） |
| 集成测试 | 0 | 上游 tarball 无集成测试目录 |
| 其他测试 | 0 | 无 CMake/Meson/pytest 等注册项；`make` 无 `check` 目标（测试二进制只被默认目标构建） |
| **合计** | **2** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | recipe 在 `make` 之后真实执行 `tests/ut_libdsme` 并解析 XML，强制 2/2 successful |
| 集成测试 | 1 | **+1（新增）** | 消费者测试 `test_package/test.c`（35 个执行断言 + 9 个产物契约检查）：抽象套接字双向往返 + extra 载荷 + 消息 API + 负向控制 |
| 鸿蒙特有测试 | 1 | 新增 | OHOS 产物契约（`test_package/conanfile.py` 的 readelf 检查）：ELF64/AArch64/DYN、上游 SONAME、纯 soname DT_NEEDED（含 musl `libc.so` 与 GLib）、无 RPATH/RUNPATH、12 个导出符号 |
| **合计** | **4** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 1. **修改的测试文件**：`tests/ut_libdsme.c`（对应 `patches/0002-tests-ut_libdsme.c.patch`，+24/−7）
>    - **修改原因**：OHOS 上不存在可用的"文件系统 AF_UNIX 套接字"目录——`/tmp` 是只读 erofs（E002），HMDFS 全域 `bind()` 返回 EPERM，`/dev/shm` 返回 EACCES（设备实测）；上游 mock daemon 硬编码 `/tmp/ut_libdsme.sock` 必然失败。另 Check 的临时通讯文件需要可写目录，而 musl 定义了 `P_tmpdir=/tmp`。
>    - **修改内容**：① mock daemon 绑定抽象套接字 `@ut_libdsme`（`sun_path[0]='\0'` + 按抽象命名空间长度 bind），抽象名下跳过 `unlink()`/`chmod()` 文件操作；② 结果 XML 默认路径支持 `TMPDIR` 环境变量。**用例数量（2）、断言与测试逻辑均未改动**，通过率 2/2 为真实执行结果。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（上游 2 个 Check 用例全部运行）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 说明：上游已有测试，但只覆盖"库内部 API + mock daemon"一个视角；本适配另行补充了两个**新增维度**（已计入上表，非"上游无测试"情形）：
>
> - **补全的测试范围**：
>   1. 消费者视角安装包测试（`test_package/test.c`，1 用例 / 35 个执行断言）：仅用已安装包的头文件与库，验证 alarm-limit 常量、消息 API（已知/未知 id、NULL 消息、extra 尺寸/指针）、`dsmesock_connect` 对不存在端点的负向控制（返回 NULL），以及抽象套接字上的双向收发与 `dsmesock_getucred`。另有 `test_package/conanfile.py` 内 9 个产物契约检查调用点（在 3 个库与 12 个符号的循环中反复执行），不与消费者断言混算。
>   2. 鸿蒙产物契约（`test_package/conanfile.py` 的 `test()`，1 用例）：三库 ELF64/AArch64/DYN、SONAME 精确匹配、DT_NEEDED 纯 soname、无 RPATH/RUNPATH、导出符号齐全、`libdsme.so.0` 依赖 musl libc 与 GLib。
> - **补全原因**：本适配修改了协议库核心路径（`dsmesock_connect` 新增抽象套接字支持），需要消费者侧独立验证该路径真实可用（上游测试的 mock daemon 与客户端同进程内，且直接绑定测试用套接字）；同时"编译通过"不构成 OHOS 产物契约证据（R40）。
> - **新增测试文件清单**：
>   1. `archives/l/libdsme/0.67.0/test_package/test.c` — 消费者测试主体（35 个 CHECK 执行断言；`#define CHECK` 宏自身不计，Release 下不会被 NDEBUG 裁掉）
>   2. `archives/l/libdsme/0.67.0/test_package/conanfile.py` — 消费者构建 + 运行 + OHOS 产物契约检查
>   3. `archives/l/libdsme/0.67.0/test_package/CMakeLists.txt` — CMakeDeps/CMakeToolchain 消费者工程
>   4. `archives/l/libdsme/0.67.0/test_package/MANIFEST.yml` — 上游 2 用例、新增 2 用例与断言计数声明

## 验证结果

- 编译状态：**通过**。`conan-verify`（profile `ohos-aarch64-device`）G0/G1/G2/G3/G4 全 PASS；`finish` step [5/10] 的 W3 本地 CI 阻塞门禁通过（门禁关键结果行见 `reports/w3-local-ci.log`；`.ci-result.json` 是工具写入的运行时标记文件、不入 PR 内容）；与平台同源的 `ci/conan/build_and_test.sh` 结果行：

  ```text
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: test_package executed
  L2_RESULT=skip: no bin/ dir
  L4_RESULT=warn: dangerous functions in patches
  L5_RESULT=pass: lib/ has content
  ```

  同日志中的其他关键行（逐字）：`libdsme consumer test: OK`、
  `[ok] L1e: Negative test confirmed — test genuinely depends on libdsme`、
  `100%: Checks: 2, Failures: 0, Errors: 0`。L4 告警针对补丁新增行中的
  `strcpy`：该调用是上游既有实现，补丁只是在其前增加 `sun_path` 长度检查，
  属门禁分级表中的非阻断告警。

- 上游测试用例通过率：**2/2（100%）**，真实运行输出 `100%: Checks: 2, Failures: 0, Errors: 0`，并按 XML 结果由 recipe 强制校验。
- 新增测试用例通过率：**2/2（100%）**（消费者测试 1/1、鸿蒙产物契约 1/1），分别在 `conan create` 的 test_package、W3 本地 CI 门禁、conan-verify 三轮独立执行中全部通过。

## 补充说明

### 适配要点

1. **抽象 AF_UNIX 套接字（平台必要适配，非 stub）**：`protocol.c` 的 `dsmesock_connect()` 支持 `@name` 前缀的抽象命名空间套接字（`sun_path[0]='\0'`，connect 长度按 `offsetof + 1 + len` 计算），同时对超长名称增加长度检查（原实现直接 `strcpy` 到 108 字节 `sun_path`）。普通路径行为完全不变；无任何平台宏，Linux 上同样成立。该方案源自设备实测：文件系统 unix socket 在 OHOS 全域不可用（`/tmp` EROFS、HMDFS EPERM、`/dev/shm` EACCES），抽象套接字 bind/connect 正常。
2. **上游测试真实执行**：上游 Makefile 只有默认目标构建测试二进制（无 `check` 目标），recipe 在 `make -j1` 后执行 `tests/ut_libdsme -o <build>/ut_libdsme.xml` 并解析 XML（Check 的 XML 带默认命名空间，按 local tag 匹配），非 2/2 成功即构建失败。
3. **libcheck 临时文件**：Check 0.15.2 探测顺序为 `TEMP` → `P_tmpdir` → `TMPDIR`，musl 定义 `P_tmpdir=/tmp`（只读），仅设 `TMPDIR` 无效；recipe 在 OHOS 上同时设置 `TEMP`/`TMP`/`TMPDIR` 指向构建目录（fork 模式默认即可通过，无需 `CK_FORK=no`）。
4. **不跑上游 `make install`**：上游 install 规则依赖 GNU `install(1)`，OHOS toybox 无此命令（实测 `Error 127`）；`package()` 显式安装三个共享库（含 SONAME 与开发用软链）、8 个头文件、3 个 pkg-config 文件与 COPYING；`.pc` 的 `prefix` 改写为 `${pcfiledir}/../..` 使其可重定位。
5. **构建环境可复现（R33/R49）**：`CC` 取自 profile 的 `tools.build:compiler_executables`；依赖头文件/库通过 `PkgConfigDeps` 生成的包内 `.pc` 暴露（glib 自带 `.pc` 的 `prefix=/` 不可用），`PKG_CONFIG_PATH` 指向 generators 目录，不注入共享系统前缀。
6. **CLI 声明（R38）**：本包为纯库（`cpp_info` 仅 libs/include），无 `bin/` 产物，因此按规范**不创建** `commands.json`。

7. **构建日志中的镜像前缀说明**：本地 `reports/conan-create.log` 中出现的
   `ghfast.top` 前缀是构建工具（E017 预防）在设备侧临时注入的下载镜像回退，
   构建后已还原（归档日志中如出现其他镜像域名，同属该临时注入机制）；归档内 `conandata.yml` 始终只声明官方 GitHub
   URL（R39），CI 会自行注入镜像 fallback。

### 已知限制

| 项 | 技术原因 |
|----|----------|
| 真机无 DSME 守护进程 | 上游测试与消费者测试均使用 mock daemon（与上游测试设计一致）；被测对象是客户端库，抽象套接字路径由消费者测试覆盖 |
| CI L2 冒烟 skip | 库包无 CLI（无 `bin/`），按 CI 逻辑跳过；已由 test_package 消费者真实执行替代 |
| L4 告警（非阻断） | 补丁新增行含 `strcpy`（上游既有的受控路径拷贝；补丁在调用前增加了 `sun_path` 长度检查，未引入新的危险函数），按门禁分级表属非阻断告警 |
| 上游 `tests.xml` 安装路径 | 其 `/opt/tests/libdsme/` 面向 Maemo 打包，本 Conan 包不安装测试二进制（仅库/头文件/.pc） |

### 平台贡献任务

- 任务 **#8164**，分支 **`feat/libdsme-0.67.0`**（与平台提供名称逐字一致）；标题前缀 `【积分赛】`。
- 本 PR 只包含 `archives/l/libdsme/` 单一软件目录（W2 原子性），未触碰框架文件与他人归档目录。
- 新增知识草稿（知识库扩展，随 PR 提交）：
  1. `DRAFT-libdsme-0.67.0-ohos-abstract-af-unix-socket` — OHOS 上文件系统 AF_UNIX 全域不可用，`@` 抽象命名空间为唯一可行方案；
  2. `DRAFT-libdsme-0.67.0-libcheck-temp-env-on-ohos` — libcheck 在 musl 上被 `P_tmpdir=/tmp` 抢先，必须设 `TEMP`；
  3. `DRAFT-libdsme-0.67.0-toybox-missing-install` — toybox 缺 GNU `install(1)`，Conan `package()` 需显式安装。

### 验证证据

| 证据 | 位置 |
|------|------|
| 上游测试真实输出（`100%: Checks: 2, Failures: 0, Errors: 0`） | `0.67.0/reports/conan-create.log`（干净重建）与 `0.67.0/reports/w3-local-ci.log`（第 222 行，W3 门禁同源输出） |
| conan-verify G0–G4 汇总 | `0.67.0/reports/conan-verify-report.md` |
| 测试说明与复现命令 | `0.67.0/reports/test-report.md` |
| W3 本地 CI 门禁日志 | `0.67.0/reports/w3-local-ci.log` |
| 适配笔记（含 7 条对话记录与问题表） | `0.67.0/notes.md` |
| W4 独立审计结论 | `0.67.0/reports/audit-result.json` |
