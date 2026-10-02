# udfclient 0.8.21 测试报告

> **项目**: udfclient 0.8.21（UDFtoolkit，UDF 文件系统工具集）  
> **测试日期**: 2026-09-27  
> **测试环境**: HarmonyOS 6.1.0.117（HongMeng Kernel 1.12.0）aarch64；OHOS SDK clang 15.0.4；Conan 2.29.1（ohos-aarch64-device profile）  
> **测试类型**: 消费者端到端测试（上游无官方测试套件，R51 清点见下）+ conan create test_package

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游官方测试 | 0（无 tests/ 目录、无 check 目标） | — |
| 鸿蒙特有测试（test_package/test.sh 断言） | 13 | 100% |
| 通过 (PASS) | 13 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**（13/13 断言；另 conan-verify G0-G4 全部 PASS）

**上游测试清点（R51）**:
1. `tar tzf UDFclient.0.8.21.tgz` 无 `tests/` 或 `test/` 目录；
2. `Makefile.in` 无 `check`/`test` 目标（仅 all/install/depend/clean/cleandir 及库/程序链接规则）；
3. `configure.ac` 无 `AC_CONFIG_TESTDIR` 等测试注册；
→ 上游 N=0，按 R51 以消费者端到端测试（test_package）补偿。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。六个工具全部构建成功并可执行；`newfs_udf` 创建的 UDF 镜像可被
`udfdump`（描述符扫描 / 卷集挂载 / 目录树）与 `udfclient`（只读挂载 / 目录列表）
正确读取；`conan create` + `test_package` 全流程在本机与 conan-verify 中通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | — | — |

### 2.3 可用功能清单

```
✅ udfclient    : 交互式只读挂载、ls/cd/pwd/free/get 等命令（测试覆盖挂载与列表）
✅ udfdump      : -S 顺序描述符扫描、卷集挂载、-t 目录树导出（测试覆盖）
✅ newfs_udf    : 镜像文件上创建 UDF 文件系统（-L/-b/-s，测试覆盖）
✅ cd_sessions  : 构建/执行/用法正常（无光盘介质，未做介质级验证）
✅ cd_disect    : 构建/执行/用法正常（无光盘介质，未做介质级验证）
✅ mmc_format   : 构建/执行/用法正常（无光盘介质，未做介质级验证）
⚠️ 写路径       : 对文件型镜像 mkdir/put 返回上游限制错误（真实光盘介质不受影响）
```

### 2.4 已知限制

1. 文件型 UDF 镜像必须显式 `-b 2048`（工具默认按光盘介质推断扇区大小）。
2. 镜像文件上的写命令（mkdir/put）不可靠（上游 `Can't determine directory ...`），未纳入断言。
3. 真实光盘读写需要光盘驱动器，本次未覆盖。

---

## 三、测试详情

### 3.1 通过的测试（test_package/test.sh，13 项断言）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 六个工具 usage banner（udfclient/udfdump/newfs_udf/cd_sessions/cd_disect/mmc_format） | 可执行性 | ✅ PASS |
| `newfs_udf -L OHOSTESTVOL -b 2048 -s 8192 consumer.img` + 产物非空 | 创建 UDF 镜像 | ✅ PASS |
| `udfdump -S consumer.img \| grep OHOSTESTVOL` | 顺序描述符扫描（读路径） | ✅ PASS |
| `udfdump -b 2048 consumer.img \| grep "Volume set"` | 卷集挂载 | ✅ PASS |
| `udfdump -b 2048 -t consumer.img \| grep OHOSTESTVOL` | 目录树 + 卷标 | ✅ PASS |
| `udfdump -b 2048 -t consumer.img \| grep "Directory tree of mount point"` | 目录树导出 | ✅ PASS |
| `printf 'ls\nexit\n' \| udfclient -b 2048 consumer.img \| grep "Directory listing of /"` | 只读挂载/列表 | ✅ PASS |
| 负向控制：`udfdump /nonexistent-udf-image` 必须失败 | 错误处理 | ✅ PASS |

> `conan create` 日志（reports/conan-create.log）记录：
> `Launching test_package` → `RUN: .../bash test.sh` → `ALL UDFCLIENT CONSUMER TESTS PASSED`。

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 真实光盘介质读写（CD-RW/DVD+RW 等） | 设备/CI 无光盘驱动器 |

---

## 四、关键问题分析

### 问题1: out-of-source（Conan build folder）构建缺少 VPATH

- **现象**: `conan create` 中 `make -j1` 报 `No rule to make target 'udfdump.o'`。
- **根因**: 上游手写 Makefile.in 面向 in-source 构建，未定义 `VPATH`；Conan autotools
  工具链在独立 build 目录中调用 `configure`，make 无法在 srcdir 找到 `.c` 源文件。
- **解决**: 补丁 0001 在 Makefile.in 增加 `VPATH= @srcdir@`（同时完成 BSD `.TARGET`
  规则到 GNU make 静态模式规则的改写）。

### 问题2: HMDFS 上 autoconf 临时目录不可写

- **现象**: `config.status: ./confXXXXXX/subs1.awk: Permission denied`。
- **根因**: HMDFS 强制目录 setgid，`umask 077 && mktemp -d` 生成 `drwx--S---` 目录，
  即使属主也无法写入（知识图谱 E114）。
- **解决**: 补丁 0004 移除 configure 中 config.status 临时目录创建的 `umask 077`。

### 问题3: HarmonyOS 平台三元组识别

- **现象**: `configure: error: cannot guess build type`；conan 传入
  `--host=aarch64-linux-ohos` 时 `config.sub` 报 `system 'ohos' not recognized`。
- **根因**: 2018 版 config.guess/config.sub 无 HarmonyOS/linux-ohos 支持（E007/E205）。
- **解决**: 补丁 0002（config.guess 增加 HarmonyOS 分支，输出 `aarch64-unknown-linux-ohos`）
  与补丁 0003（config.sub 接受 `linux-ohos*`）。

---

## 五、验证命令

```bash
# conan-verify（G0-G4）
python3 scripts/ohc-run.py conan-verify udfclient 0.8.21 --profile ohos-aarch64-device
# → G0/G1/G2/G3/G4 PASS；test_package 13 项断言通过

# 本地 CI 门禁（与平台 CI 同一脚本）
export CONAN_PROFILE=ohos-aarch64-device
export CI_PACKAGES="archives/u/udfclient/0.8.21"
export CI_REPO_ROOT="$PWD"
zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
# → 见 .ci-result.json（finish [5/10] 写入）
```
