# libinklevel 0.9.7 适配笔记

## 编译环境

- 构建系统: autotools（configure + libtool，上游 tar 内含 2009 年的 config.guess/config.sub）
- 编译日期: 2026-09-13
- 编译器: clang 15.0.4（OHOS SDK aarch64，OHOS libc）
- 依赖: `libusb/1.0.27`（shared）、`libxml2/2.15.3`（shared），制品仓已发布，按 R36 直接依赖，未做捎带适配
- 状态: published

## 编译与验证步骤（W3 等价命令）

```bash
cd archives/l/libinklevel/0.9.7
conan create . \
  -pr:h=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="libinklevel/*"
```

- 4 个补丁在 `build()` 中经 `apply_conandata_patches()` 应用，configure 打印
  `host system type... aarch64-unknown-linux-ohos`
- `checking for libusb-1.0... yes` / `checking for libxml-2.0... yes`（PkgConfigDeps 注入的 .pc）
- 产物: `lib/libinklevel.so.5.0.0`（SONAME `libinklevel.so.5`，含 `.so` 软链）、`include/inklevel.h`、
  `share/doc/`；构建期 `.la`（记录绝对路径）在 package() 中删除
- test_package 消费者测试 4 例全通过（见 reports/test-report.md）

## 上游测试枚举台账（全量，2026-09-13）

**结论: source_declared_total = 0（上游无独立测试用例）**

tarball `libinklevel-0.9.7.tar.gz` 共 23 个文件，无 tests/ 目录、无测试框架注册、无
`TESTS` / `check_PROGRAMS` 目标（`Makefile.am` 中只有 `lib_LTLIBRARIES = libinklevel.la`），
`make check` 无对应规则。上游无测试用例，由 `test_package/` 消费者测试覆盖；本 PR 不修改 `ci/config/`。

| 项 | 文件 | 分类 | 是否独立上游用例 | 是否实际运行 | 结果/原因 |
|----|------|------|-----------------|-------------|----------|
| 库源码 | libinklevel.c devices.c canon.c epson.c bjnp.c bjnp-io.c bjnp-debug.c hp.c util.c | 库实现 | 否（非测试） | 编译 | make 通过，产出共享库 + 静态库 |
| 公共头 | inklevel.h | API 声明 | 否 | 编译 | 消费者测试 include 使用 |
| 测试框架 | 无 | - | - | - | 上游无测试框架（无 CUnit/check/ctest/pytest 注册） |
| fixture/样例/基准 | 无 | - | - | - | 上游无 |
| 测试脚本 | 无 | - | - | - | 无 .sh/.py 测试脚本 |
| 构建目标 | lib_LTLIBRARIES = libinklevel.la | 库 | 否 | 构建 | make exit 0 |
| 手册 | doc/ 下的 man 页 | 文档 | 否 | - | 非用例 |

> 上游 README 说明该库的验证方式为“接上真实打印机后运行示例程序”，属手工验证，
> 无自动化测试用例可执行，因此按规则走“补全测试”路径。

## 补全测试（消费者视角，4 例）

`test_package/test.c` 通过公共头 `inklevel.h` 真实调用 API，不使用桩函数：

| 用例 | 断言 | 实测结果 |
|------|------|---------|
| TC1 公共 API 可用性 | `get_version_string()` 非空且含 `0.9.7` | PASS（`libinklevel 0.9.7`） |
| TC2 参数校验错误路径 | 未知端口返回 `UNKNOWN_PORT_SPECIFIED(-6)` | PASS（rc=-6） |
| TC3 设备名解析错误路径 | 非法 BJNP URI 返回 `BJNP_URI_INVALID(-17)` | PASS（rc=-17） |
| TC4 无设备环境探测 | USB 端口无打印机时返回负值且不崩溃 | PASS（rc=-4） |

## 鸿蒙 PC 平台特有测试（`test_package/test_ohos.c`，4 例 / 11 条断言）

上游无测试套件的前提下，除通用消费者契约外补充的平台特有断言（第二个测试可执行文件，
`test()` 内与前一个程序依次 `self.run()`，均须 RC=0）：

| 用例 | 断言 | 实测结果 |
|------|------|---------|
| TC-OHOS1 运行时按 SONAME 解析 | `/proc/self/maps` 可读、含 `libinklevel.so.5`；库目录落在运行时搜索路径；`libusb-1.0.so.0`、`libxml2.so.16` 已映射（5 条） | PASS |
| TC-OHOS2 探测时延契约 | 连续 3 轮 `get_ink_level(USB)` 均返回负值且单轮 < 5s（2 条） | PASS（rc=-4；0.003/0.009/0.015s） |
| TC-OHOS3 UTF-8 设备名健壮性 | 中文设备名与 900 字节 UTF-8 设备名均返回负值、不越界（2 条） | PASS（rc=-17 / -17） |
| TC-OHOS4 目标架构契约 | 从只读映射起始处读 ELF 头：64 位小端 + `EM_AARCH64`（2 条） | PASS（class=2 data=1 machine=183） |

**平台事实（本次实测发现，可用于后续同类适配）**：

1. 鸿蒙上 `/proc/self/maps` 记录的是 **HMDFS 挂载底层路径**
   `/data/service/el2/<uid>/hmdfs/account/files/Docs/...`，该路径在进程内 **不可访问**
   （`realpath`/`open` 报 No such file or directory），而进程可见路径以 `$HOME`
   （`/storage/Users/currentUser`）为前缀；两者指向同一目录（同 inode）。
   → 断言“库目录来自运行时搜索路径”时必须按“`$HOME` 前缀 ↔ HMDFS 底层前缀等价”比对剩余
   相对路径，不能直接 `strcmp`/`realpath` 比较全路径。
2. 不可 `open()` 底层路径时，可用**只读映射起始地址直接读文件头**（映射 offset=0、权限
   `r--p`），无需重复 `open()`——TC-OHOS4 即以此读取 ELF 头验证交叉构建目标。
3. conan 缓存中 `p/<包名+id>` 是访问符号链接、`p/b/<id>` 才是真实目录，脚本比对路径时需
   先 `realpath` 归一（与上面第 1 点叠加，双向前缀差异）。

## 适配踩坑与修复

1. **三元组不识别（E007）**：上游 config.guess 不认识 OHOS，config.sub 又直接拒绝
   `linux-ohos`。修法分两处：config.guess 增加按 uname（HarmonyOS）匹配的 case 分支，
   直接产出 `aarch64-unknown-linux-ohos`（**不引入 `__OHOS__` 宏探针**，保持补丁无平台宏）；
   config.sub 把 `linux-ohos` 补进 kernel/os 校验白名单，否则 configure 报
   `Invalid configuration ... machine 'aarch64' not recognized`。
2. **HMDFS 上的 mktemp（E490）**：configure 的 `mktemp -d ./confXXXXXX` 分支在 HMDFS 上
   无法创建临时目录，导致 configure 中途失败；改为固定目录名后通过。
3. **NDEBUG 缺符号（本次新增知识）**：`bjnp-debug.c` 用 `#ifndef NDEBUG` 包住
   `bjnp_hexdump()` / `level2str()` / `str2level()` 的定义，而 `bjnp-io.c` 在守卫之外
   无条件调用它们。Conan Release 构建带 `-DNDEBUG` → 定义被剔除、引用仍在 →
   `libinklevel.so.5` 带未解析符号，消费者进程 `dlopen` 即失败
   （`undefined symbol: bjnp_hexdump`）。修法是去掉该守卫常编译（0001 补丁）。
   注意：上游默认 `./configure && make` 不带 `-DNDEBUG`，所以该缺陷只在 Release 构建暴露。
4. **依赖注入（R49）**：configure 用 `PKG_CHECK_MODULES` 探测 `libusb-1.0` / `libxml-2.0`，
   配方用 `PkgConfigDeps` 生成 .pc 交给 `AutotoolsToolchain` 自动挂 PKG_CONFIG_PATH，
   依赖路径全部落在 Conan 构建目录内，未写入共享 `/usr/local`。

## 归档

- 补丁: 4 个（1 个 bugfix + 3 个 portability），由 `refresh-patch --auto` 固化
- 测试: 消费者测试 8 例 / 16 条断言（上游 0 例；`test.c` 4 例 5 条 + `test_ohos.c` 4 例 11 条），MANIFEST.yml 已声明

---

## 对话记录

### 对话 #1 — 初始适配（2026-09-13）

- 上游无测试套件（`make check` 无规则），按“补全测试”路径新增 `test_package/test.c`（4 例 5 条断言）。
- 定位并修复 `bjnp-debug.c` 的 `NDEBUG` 守卫不一致导致的未解析符号，固化为 `0001-bjnp-debug.c.patch`。
- W3 本地 CI 通过，创建 PR #9851，CI 首次全绿。

### 对话 #2 — 补充鸿蒙 PC 平台特有测试（2026-09-14）

- 新增 `test_package/test_ohos.c`（4 例 11 条断言），覆盖运行时 SONAME 解析、探测时延契约、
  UTF-8 设备名边界、交叉构建目标架构契约，并在 `test_package/CMakeLists.txt` 注册第二个可执行文件。
- 实测踩坑：`/proc/self/maps` 记录 HMDFS 底层路径，进程内不可 `open()` → 断言改用 realpath 归一化 +
  `$HOME`/HMDFS 前缀等价比对；ELF 头改为直接从只读映射起始地址读取。
- 本地 `conan create` 迭代 3 轮后 PASS=16 FAIL=0。

### 对话 #3 — 处理人工检视意见（2026-09-14）

- 检视意见 1（rule5）：PR 只能包含 `archives/` + `knowledge/` 改动 → 将 `ci/config/no_official_test.txt`
  的登记改动从本 PR 移除（该文件回到与 `main` 一致），上游无测试的事实改由 PR 说明与 `MANIFEST.yml` 声明；
  CI 的 L1 检查改按“`test_package` 实际执行”路径通过，不再依赖白名单跳过。
- 检视意见 2（test_package 复核）：发现两处断言受环境分支影响会让断言数浮动（10~11 条）→
  TC-OHOS1 搜索路径归属、TC-OHOS4 ELF 头校验改为无条件断言（环境缺失时判负并打印原因），
  通过路径恒为 11 条断言。
- 复验：`conan create` RC=0、PASS=16（`test_package` 5 + `test_ohos` 11）、FAIL=0；`finish` W3 重跑通过，
  `.ci-result.json` 已刷新（exit_code=0）。
---

**编译结束**: 2026-09-14 10:38
**最终状态**: published
