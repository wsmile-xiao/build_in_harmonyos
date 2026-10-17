# cpdb-libs 2.0-b5 测试报告

## 结论

HarmonyOS/AArch64 适配构建和全部规定测试通过。上游测试与新增
HarmonyOS 测试合计 2/2 通过，通过率 100%。

## 环境

- HarmonyOS SDK: 6.0.0.47（API 20）
- 目标架构: AArch64 / `armv8`
- 编译器: HarmonyOS Clang 15.0.4
- Conan: 2.29.1（OHOS 适配版）
- 运行环境: HarmonyOS/AArch64 目标运行环境

## 测试清点与结果

| 测试 | 类型 | 结果 |
|------|------|------|
| `tools/run-tests.sh` | 上游 D-Bus 集成测试 | 1/1 PASS |
| `test_package/test_cpdb_ohos.c` | HarmonyOS 消费端 API 测试（8 项显式校验） | 1/1 PASS |
| `cpdb-pickle-print` 支持的无参数用法 | 包内命令冒烟 | PASS |
| `cpdb-text-frontend` 的 `stop` 交互 | 包内命令与 D-Bus 冒烟 | PASS |

上游发布包仅注册一个 Automake 测试入口；未发现其他 CTest、pytest、
独立 `tests/` 目录或额外 Automake `TESTS` 条目。

## 门禁结果

- `conan create`: PASS（源码校验、六个补丁、编译、`make check`、安装、消费端测试）
- GLib `gio-unix-2.0` 元数据注入: PASS（`configure` 实际输出 `checking for gio-unix-2.0... yes`，编译和链接使用 Conan GLib 包路径）
- Worker Autotools 工具缺失场景: PASS（发布生成文件与源码修改同步并刷新时间戳，构建不调用 `autoreconf`、`autopoint`、`aclocal` 或 `automake`，完整编译及上游测试 1/1 通过）
- Worker 受限临时目录场景: PASS（显式 OHOS/AArch64 三元组绕过 `config.guess` 探测；OHOS 构建将 Autoconf 临时目录设为 `umask 022`，`config.status` 可在 HMDFS 中创建 `subs1.awk`，其他平台仍默认 `077`；完整构建及测试通过）
- Worker 固定 Python shebang 场景: PASS（构建日志确认 GDBus 两个接口均由当前 Conan Python 显式执行 GLib 包内 `gdbus-codegen`，未执行 PATH 中的 `/data/service/hnp/bin/gdbus-codegen`；上游测试通过显式 `LOG_COMPILER` 运行）
- Worker 无 D-Bus session runner 场景: PASS（不依赖宿主机 `dbus-run-session`；真实运行前端并验证 session bus 不可用时仍接受 `stop`、安全销毁对象且输出成功断言；有 runner 的环境继续覆盖原上游会话总线路径）
- 共享库与静态库配置: 均完成 `conan create`、上游测试和消费端测试，全部 PASS
- `conan-verify`: PASS（G0/G1/G2/G3/G4、L2/L4/L5）
- W3 `build_and_test.sh`: PASS，1/1 软件包，100%
- L0/KC/JC: PASS
- L1e 破坏性反向验证: PASS，确认测试实质依赖 cpdb-libs 产物
- ELF 检查: 4/4 为 AArch64 ELF64；共享库 SONAME、相对 NEEDED、NX、PIE/共享对象类型和 GNU_RELRO 均符合检查要求
- 最终 Conan 包未包含 libtool `.la` 元数据

## 产物覆盖

验证覆盖 `libcpdb`、`libcpdb-frontend`、公开头文件、pkg-config 元数据、
`cpdb-text-frontend` 与 `cpdb-pickle-print`。两项命令均按上游实际支持的
调用方式运行通过。
