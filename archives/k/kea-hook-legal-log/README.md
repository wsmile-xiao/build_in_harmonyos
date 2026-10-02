# kea-hook-legal-log

ISC Kea 的 **legal log**（司法日志，Kea 2.4 起更名 Forensic Log）hook 插件，
适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libdhcp_legal_log.so` 是 Kea DHCPv4/v6 服务器的司法日志钩子：按参数配置的
轮转策略（固定时长 / 每日 / 每月 / 每年轮转）把服务器的租赁/分配活动写入
日志文件，支持轮转前/后执行 `prerotate`/`postrotate` 命令，可选数据库后端
（MySQL/PostgreSQL）或文件后端。插件由 Kea 服务器在运行时 `dlopen()` 加载
（`hooks-libraries` 配置项），不是被链接的库。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/hooks/dhcp/forensic_log/`（Kea 2.4 起目录更名，产物仍为
  `libdhcp_legal_log.so`，与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：`lib/kea/hooks/libdhcp_legal_log.so`

## 家族复用

本包与已适配的 kea-hook-limits、kea-hook-ping-check、kea-hook-host-cmds 同属
Kea 3.0.3 单源码树（`src/hooks/dhcp/` 下平级目录），平台差异完全相同：
0001-0004 四补丁整组复用（md5 逐字节一致）。本配方新增 0005/0006：
- **0005（运行时脚本 spawn）**：本插件独有的**运行时**脚本执行点——RotatingFile
  轮转时经 `ProcessSpawn`（fork+execve，无 shell 回退）运行 prerotate/postrotate
  命令，OHOS 内核拒 shebang execve，补丁在 musl-Linux 上把命令经 `/bin/sh`
  路由（脚本路径作 `$1`，参数语义不变）。
- **0006（只读系统目录下日志文件打开回退）**：OHOS app 沙箱把 `/tmp` 等系统
  目录以只读挂载，`KEA_LEGAL_LOG_DIR` 指向这类目录时后端 `openInternal()`
  打开日志文件失败（EROFS）；补丁在打开失败且 `errno ∈ {EROFS, EACCES}` 时
  回退到 `$HOME/.kea-legal-log/`（路径 `/` 转 `_` 防碰撞，mkdir 幂等），
  配置字符串与 PathChecker 校验消息原样保留。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件（`interprocess`/`circular_buffer`），须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端 |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带插件运行时加载的 Kea 共享库（`readelf -d` NEEDED 闭包），
因此安装后无需额外的 Kea 运行库即可被服务器加载。

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`，使
   `iface_mgr_linux.cc` / `pkt_filter_lpf.cc` 等 Linux 后端源码被选中。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（`__linux__ && !__GLIBC__` 守卫，无需平台宏）。
3. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
4. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径
   （OHOS 的 Python subprocess 不解析 PATH）。
5. **脚本执行一律经解释器**：OHOS 内核拒绝 shebang 脚本的 execve（无论执行位），
   Kea 的 configure 期脚本（`scripts/env.sh`、`scripts/grabber.py`、
   `config-report.sh`、`mk_cfgrpt.sh`）由补丁 0003/0004 经解释器前缀调用；
   配方自身的 `build()` 也遵循同一纪律（conan 的 meson 包 `bin/meson` 是
   shell 包装脚本，改经 `sh "<meson 包>/bin/meson"` 调用）。
6. **运行时命令 spawn**（本插件独有）：RotatingFile 轮转时的 prerotate/
   postrotate 命令经 `ProcessSpawn` 直接 execve，无 shell 回退——OHOS 上
   脚本命令由补丁 0005 经 `/bin/sh` 路由，`$1` 语义不变。
7. **只读系统目录下的日志文件打开**（本插件独有）：OHOS app 沙箱把 `/tmp`
   等系统目录以只读挂载；`KEA_LEGAL_LOG_DIR` 指向这类目录时，补丁 0006 在
   open 失败（EROFS/EACCES）时回退到 `$HOME/.kea-legal-log/`，配置字符串
   原样保留（上游测试断言 BadValue 消息嵌入的路径文本不受影响）。
8. **soname 物化**：OHOS `/storage` 沙箱拒绝符号链接，meson 版本化共享库的
   soname 名只以符号链接发布 → build() 在 compile 后以复制方式物化 soname 名。

## 上游测试

两个 Meson 注册的 gtest 套件在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `dhcp-forensic-log-tests` | 85 | hook 单元测试（command_log 7+3 / legal_log4 17 / legal_log6 27+1 / legal_log_mgr 11 / rotating_file 19），全部走文件/内存后端，无 root 用例；其中 3 例真实执行 prerotate/postrotate 测试脚本（补丁 0005 覆盖的运行时 spawn 路径）、1 例以 `KEA_LEGAL_LOG_DIR=/tmp` 实测只读系统目录下的打开回退（补丁 0006） |
| `dhcp-forensic-log-libloadtests` | 6（源码 10） | 插件的加载/卸载契约与回调行为；PgSql/MySqlLegalLibLoadTest 各 2 例受 HAVE_PGSQL/HAVE_MYSQL 守卫，`-Dmysql/-Dpostgresql=disabled` 下上游构建即不编译（属上游按配置裁剪，非适配删除） |

与 ping-check 不同，本插件的上游测试面**没有 root 组**：所有用例走文件后端
（ForensicLog）/内存后端，无原始套接字、无数据库后端依赖。

本版本实测：见版本级 `notes.md`。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| `test_legal_log_hook` | 消费者契约 | `dlopen` 加载包内 hook，校验 `version`/`load`/`unload` 契约符号与 hook ABI 版本 30003 |
| `test_ohos_platform` | **鸿蒙特有 #1** | 校验产物平台 ABI 签名：ELFCLASS64 / `EM_AARCH64`（OHOS PC aarch64）、`DT_NEEDED` 为 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`，并验证 OHOS 加载器 `dlopen(RTLD_NOW)` 可解析插件 |
| `test_ohos_runtime` | **鸿蒙特有 #2** | 在 OHOS 加载器下逐个 `dlopen(RTLD_NOW)` 包内 Kea 运行时库，校验完整 NEEDED 闭包可解析、闭包驻留后 hook 仍可加载且契约符号可解析 |

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=kea-hook-legal-log/3.0.3 -pr:h=<ohos-aarch64 profile>
```

Kea 服务器加载（`kea-dhcp4.conf`）：

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      { "library": "<prefix>/lib/kea/hooks/libdhcp_legal_log.so" }
    ],
    "legal-log": {
      "name": "kea-legal",
      "path": "/var/lib/kea",
      "base-name": "kea-legal",
      "count": 2,
      "maximum-rotation-time": 3600
    }
  }
}
```
