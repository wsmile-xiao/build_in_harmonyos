# kea-ctrl-agent

ISC Kea 的 **Control Agent**（REST 控制通道前端），适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`kea-ctrl-agent` 是 Kea 自带的控制通道前端：对外暴露一个 HTTP/HTTPS 端点
（默认 `http-host`/`http-port` 可配，支持 TLS 与 basic auth），把远端管理命令
（JSON body）转发给 `kea-dhcp4` / `kea-dhcp6` / `kea-d2` 中配置的控制通道，
并把应答原样返回；同时**自行处理** Control Agent 原生命令——`config-get` /
`config-set` / `status-get` / `shutdown` / `version-get` 等不会转发给服务器。
典型用法是把它放在只能访问管理网络的接口上，DHCP 服务器本体则不开控制通道。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/bin/agent/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：上游 `SBINDIR`（本包按 Conan 约定安装到 `bin/kea-ctrl-agent`）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（HTTP/HTTPS 与摘要） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带 Kea 运行时库全集 20 个共享库（40 文件：soname 名 + 全版本名
物化两份）。真机上 `readelf` 逐级解析代理二进制的 NEEDED 闭包为 16 库——
Kea 各库以「全部已构建库」累积链接（`LIBS_BUILT_SO_FAR`），闭包深于直接
NEEDED（代理直接 9 库）；经 `libkea-hooks` 加载的插件还会用到更多运行时库，
故按家族 kea-hook-bootp/kea-hook-ha 同口径分发全集，安装后无需额外的 Kea
运行库即可直接执行。

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（全树构建时 `src/lib/dhcp/iface_mgr_linux.cc` 同样编译到）。
3. **脚本 execve 限制**：OHOS 内核拒绝 shebang 脚本直接执行 → conan 的 meson
   包装脚本经 `sh` 调用；configure 期的 `env.sh` / `grabber.py` /
   `config-report.sh` / `mk_cfgrpt.sh` 经解释器前缀调用（补丁 0003/0004）；
   脚本型测试 `ca_process_tests.sh` 经 `meson --wrapper sh` 执行。
4. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
5. **符号链接沙箱**：`/storage` 拒绝 `ln -s` → meson 的 soname 符号链接在
   build() 内以复制方式物化（`_materialize_sonames`），并保留 package() 的
   0 字节落盘自愈复核。
6. **并发进程配额**：`meson compile -j 8` 限并发（ninja 默认并行度触发
   posix_spawn EAGAIN）。
7. **测试沙箱临时目录**：共享测试辅助 `isc::test::Sandbox` 以 `P_tmpdir` 拼
   `mkdtemp()` 模板，/tmp 只读时返回 NULL、`std::string` 空指针赋值即崩 →
   模板优先 `TMPDIR`（补丁 0005；与 kea-dhcp6 配方对**同一共享文件**的移植
   逐字节一致）。
8. **AF_UNIX 路径名 socket**：鸿蒙 hmdfs 用户存储拒绝路径名 `bind()`
   （EPERM，真机全盘探针：仅抽象命名空间可用）→ ca_command_mgr 的 9 个
   命令转发用例以「与测试服务器同路径、同原语」的 bind 探针判定后
   `GTEST_SKIP`（补丁 0006；常规 Linux 探针恒真、跳过路径永不触发）。
9. **测试 socket 路径长度**：深 out-of-tree 构建目录（如共享包缓存）令
   `TEST_DATA_BUILDDIR` 拼接 `/test-socket` 超过 `sockaddr_un::sun_path`
   108 字节上限，`connect()` 一律抛 `ENAMETOOLONG`（真机 verify2 单例失败
   复现）→ 夹具在拼接超限时回退 `TMPDIR`（短且可写；未设 TMPDIR 时行为
   不变；补丁 0007）。
10. **文件 logger 白名单**：Kea 对配置文件 logger 的输出路径做白名单校验
    （白名单目录取环境变量 `KEA_LOG_FILE_DIR`，默认 `/var/log/kea`；OHOS 上
    不存在该目录）→ 给 Kea 进程配绝对日志文件路径时须导出 `KEA_LOG_FILE_DIR`
    指向可写目录（上游各进程测试 `.sh.in` 标准做法；test_package e2e 用例
    同款处置并校验日志落盘）。

## 上游测试

`src/bin/agent/tests/meson.build` 注册 2 个测试，均在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `kea-agent-tests`（gtest） | 98（执行 96） | ca_cfg_mgr 20、ca_command_mgr 15、ca_controller 22、ca_process 2、ca_response_creator_factory 1、ca_response_creator 14、get_config 1、parser 23；其中 2 例为上游自带 `DISABLED_` 前缀（不执行），ca_command_mgr 另有 9 例命令转发用例按平台探针跳过（见适配要点第 8 条） |
| `ca_process_tests.sh`（shell） | 7 | pid 文件二次启动拒绝、SIGTERM/SIGINT 优雅退出、`-t` 配置检查成功/语法错误/取值错误三态、日志口令脱敏 |

本版本实测：96 + 7 = 103 例执行——**94 例通过（87 gtest + 7 shell），0 失败**；
9 例命令转发用例因 hmdfs 拒绝 AF_UNIX 路径名 bind()（EPERM）按同型探针判定后
跳过（校验点、逻辑与注册数零改动）。

## test_package（消费者视角 + 鸿蒙特有用例）

`conan create` 的 test 阶段真实编译并执行 3 个测试（CMake +
`find_package(kea-ctrl-agent)`）：

| 测试 | 内容 |
|------|------|
| `test_kea_ctrl_agent.py` | 版本输出（`-v`/`-V`）、`-W` 配置报告、无参数 usage 错误路径、`-t` 对合法配置的接受与对语法错误/越界端口的拒绝、一次真实控制通道端到端（回环端口启动真实进程，POST `config-get` 校验 HTTP 200 + result 0 + 返回端口，POST 不支持命令校验非零 result——应答为单元素 JSON 数组形制，解包后判定——并以 `KEA_LOG_FILE_DIR` 导出验证配置日志落盘，SIGTERM 优雅停止），共 7 项用例 |
| `test_ohos_platform`（**鸿蒙特有**） | 包内 `bin/kea-ctrl-agent` 的 OHOS 平台 ABI 特征：ELFCLASS64 / `EM_AARCH64` / `ET_DYN`(PIE)、`DT_NEEDED` 链接 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`，共 8 项检查 |
| `test_ohos_runtime`（**鸿蒙特有**） | OHOS 加载器下的运行时闭包：`DT_NEEDED` 的 Kea 库全部随包分发、全部 40 个 `libkea-*.so*`（运行时全集 20 库 × soname 名 + 全版本名）`dlopen(RTLD_NOW)` 成功、真实执行 `kea-ctrl-agent -v` 输出 `3.0.3`，共 6 项检查（另有逐库 dlopen 结果行） |

鸿蒙特有测试用例 **2 个**，实测 **2/2 通过**。

## 使用

```bash
conan install --requires=kea-ctrl-agent/3.0.3 -pr:h=<ohos-aarch64 profile>

# 版本
kea-ctrl-agent -v

# 以配置文件启动（示例配置见上游 doc/examples/agent.json）
kea-ctrl-agent -c /path/to/agent.json

# 经控制通道查询配置
curl -X POST -H 'Content-Type: application/json' \
     -d '{"command": "config-get"}' http://127.0.0.1:8000/
```
