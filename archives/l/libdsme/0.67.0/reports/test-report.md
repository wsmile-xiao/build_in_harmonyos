# libdsme 0.67.0 测试报告

## 测试环境

| 项目 | 值 |
|------|-----|
| 设备 | HarmonyOS PC（HAD-W24，aarch64），Kernel 1.12.0，HDC 报告 API 23 |
| 工具链 | OHOS SDK 26.0.0.18 native clang 15.0.4（aarch64-linux-ohos） |
| Conan | 2.29.1（OHOS 适配版），profile `ohos-aarch64-device` |
| 宿主依赖 | glib/2.84.0.1（ohos 制品仓已发布） |
| 测试依赖 | check/0.15.2（test_requires，仅上游测试） |
| 验证命令 | `python3 scripts/ohc-run.py conan-verify libdsme 0.67.0 --profile ohos-aarch64-device` |

## 结论摘要

| 类别 | 结果 | 说明 |
|------|------|------|
| 编译（conan create） | PASS | G0–G4 全通过（含 `--build=missing` 干净构建） |
| 上游测试 | **2/2（100%）** | `tests/ut_libdsme` 的 2 个 Check 用例，XML 校验强制 |
| 消费者测试 | 1/1 | `test_package/test.c`，35 个 CHECK 断言（另含 9 个产物契约检查调用点） |
| 鸿蒙特有测试 | 1/1 | OHOS 产物契约（readelf 检查） |
| 适配后合计 | **4 cases** | 上游 2 + 新增 2（其中鸿蒙特性 2） |

证据文件：

- `reports/conan-verify-report.md` — G0–G4/L2/L4/L5 汇总
- `reports/conan-create.log` — 干净重建（`conan remove` 后全量重新编译）与上游测试输出
- `reports/w3-local-ci.log` — W3 门禁中的上游测试输出（`100%: Checks: 2, Failures: 0, Errors: 0`，第 222 行）
- `reports/conan-verify-run.log` — conan-verify 运行日志

## 1. 上游测试（真实运行，非跳过）

上游 `tests/ut_libdsme.c` 使用 Check 框架，包含 2 个用例：

1. `test_message` — `dsmemsg_new`/`dsmemsg_id`/`dsmemsg_size`/
   `dsmemsg_extra_size`/`dsmemsg_line_size` 契约；
2. `test_send_receive` — 对 mock daemon 完成
   `dsmesock_connect` → `dsmesock_broadcast` → `dsmesock_receive` →
   `dsmesock_send_with_extra`（含 `STATE_REQ_DENIED_IND` + "a-reason"
   extra 载荷）的往返。

上游 Makefile 只把测试二进制编进默认目标、没有 `check` 目标，recipe 在
`make` 之后真实执行它并解析 XML：

```
libdsme/0.67.0@ohpcd/stable: RUN: ".../tests/ut_libdsme" -o ".../ut_libdsme.xml"
Running suite(s): libdsme
100%: Checks: 2, Failures: 0, Errors: 0
```

**对上游测试的修改**（见 `patches/0002-tests-ut_libdsme.c.patch`）：

- mock daemon 由 `/tmp/ut_libdsme.sock` 改为抽象套接字 `@ut_libdsme`
  （OHOS 禁止文件系统 unix socket：HMDFS `bind()` EPERM、`/tmp` 只读）；
- 抽象名下跳过 `unlink()`/`chmod()`；
- 结果 XML 默认路径支持 `TMPDIR`（musl `/tmp` 只读）。

用例数量、断言与测试逻辑未改动；通过率 2/2 = 100%。

## 2. 消费者测试（test_package/test.c）

`test_package/conanfile.py` 用 CMakeDeps/CMakeToolchain 对着**已安装包**
构建并运行 `libdsme_consumer`（35 个 CHECK 断言，Release 下不会被
`NDEBUG` 裁掉）：

- alarm-limit 常量（`dsme_snooze_timeout_in_seconds() == 120`）；
- 消息 API：已知 id 名称（`GET_VERSION`）、未知 id
  （`UNKNOWN_0000002a`）、NULL 消息（`NULL_MESSAGE`）、extra 尺寸/指针；
- **负向控制**：`DSME_SOCKFILE=@libdsme-no-such-endpoint` 时
  `dsmesock_connect()` 返回 NULL；
- **平台特性主路径**：绑定抽象套接字 `@libdsme-consumer-test`，
  `dsmesock_connect()` 真实连接，双向收发 +
  `dsmesock_send_with_extra` 载荷校验 + `dsmesock_getucred()`。

输出：

```
libdsme consumer test: OK
```

## 3. 鸿蒙特有产物契约（test_package `test()`）

对已安装的三个共享库逐一执行（llvm-readelf）：

- `ELF64` / `AArch64` / `Type: DYN`；
- `SONAME` 精确等于 `libdsme.so.0`、`libdsme_dbus_if.so.0`、
  `libthermalmanager_dbus_if.so.0`；
- `DT_NEEDED` 为纯 soname（无路径），libdsme.so.0 依赖 musl `libc.so`
  与 `libglib-2.0.so.0`；
- 无 `DT_RPATH`/`DT_RUNPATH`；
- libdsme.so.0 导出 `dsmesock_*`、`dsmemsg_*`、
  `dsme_snooze_timeout_in_seconds` 共 12 个入口符号。

## 4. 复现步骤

```bash
# 依赖已发布核验（W0）
conan download glib/2.84.0.1 -r=ohpcd
conan download check/0.15.2 -r=ohpcd

# 配方验证（干净构建 + 上游测试 + 消费者测试 + 契约检查）
python3 scripts/ohc-run.py conan-verify libdsme 0.67.0 --profile ohos-aarch64-device

# 本地 CI 模拟 + finish
CONAN_PROFILE=ohos-aarch64-device CI_PACKAGES=archives/l/libdsme/0.67.0 \
  CI_REPO_ROOT=$PWD zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```

## 5. 已知限制

- 真机没有 DSME 守护进程；上游测试本来就用 mock daemon，消费者测试同理
  （抽象套接字往返），符合被测库的客户端定位。
- 上游 `make install` 依赖 GNU `install(1)`（OHOS/toybox 没有），因此
  `package()` 显式安装产物；安装结果已通过 staging 拷贝与产物契约检查。
- `/tmp` 只读与 HMDFS 禁止 unix socket 是平台差异，已通过抽象套接字与
  `TEMP`/`TMPDIR` 重定向解决，不引入平台宏。

---

**测试结论**: 上游 2/2、消费者 1/1、鸿蒙产物契约 1/1，全部通过。
