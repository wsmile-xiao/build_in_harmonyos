# DRAFT-ohos-conan-make-executable-conf：OHOS 适配版 Conan 未注册
# tools.build:make_executable conf（self.conf.get() 抛 ConanException）

> Contributor: nymphcast-0.2 适配 | Status: Draft | Updated: 2026-08-27
> Source: archives/n/nymphcast/0.2-alpha0（round-8 attempt-1 设备 CI 实测）

## 现象

nymphcast 0.2-alpha0 是纯 GNU Make 型 recipe（上游无 CMakeLists.txt）。
conanfile.py `build()` 首版在 `_resolve_make()` 中按官方常见写法读取：

```python
make = self.conf.get("tools.build:make_executable", check_type=str)
```

在 OHOS 适配版 Conan 2.29.1（设备 `conan --version` 实测）下，该调用直接抛
`ConanException`：

```text
ConanException: [conf] tools.build:make_executable does not exist in
configuration list. Run conan config list to see all the available confs.
```

（设备日志：`<run>/ci-round-8/ci-attempt-1-fail.log`，`Error in build()
method, line 215` → `while calling _resolve_make, line 49`。）

`conan create` 在 build() 入口即崩溃，L1 失败。

## 根因分析

- OHOS 适配版 Conan 2.29.1 的 conf 注册表 **不含** `tools.build:make_executable`：
  `conan config list | grep -c make_executable` = **0**。
- 官方 Conan 2.31.1 文档（global.conf 内置 conf 列表）同样**无**该 key：
  存在的是 `tools.build:compiler_executables`（dict，见 E307）、
  `tools.cmake:cmake_program`、`tools.gnu:make_program` 等。
- 设备 `conan config list | grep make_program` 显示 `tools.gnu:make_program`
  存在（官方 2.x 长期 key），但与 E307 的 `compiler_executables` 是**不同 key、
  不同语义**；本 run 与"conf 是 dict"主题无关，是"conf 未注册"这一全新类别。
- make 的实际解析在 OHOS CI 由 profile buildenv 把 `/data/service/hnp/bin`
  注入 PATH 后经 `shutil.which("make")` 得到（round-9 ci.log RUN 行）。

## 解决方案

1. **PATH 探测优先 + 已知工具链目录兜底**（nymphcast 采用，round-9 PASS）：

```python
import shutil, os
_HNP_BIN = "/data/service/hnp/bin"
found = shutil.which("make")
make = found if found else os.path.join(_HNP_BIN, "make")
```

2. 若确需 conf，必须先 `conan config list` 验证 key 存在（如
   `tools.gnu:make_program`），不能假设注册。

## 验证证据

- 修正后 round-9 权威 CI PASS：L0/L1/L4/L5 pass、L2 skip 非阻塞、
  Build Summary 1/1、`nymphcast_server` 打包成功，test_package
  `--version` 在 conanrun env 下真实运行 PASS。
- `conan config list | grep -c make_executable` = 0（未注册，独立复核）。

## 查重（B1 去重证据摘要）

- 检索词：`tools.build:make_executable` / `tools.gnu:make` / `tools.build:make` /
  `make_executable` / `ConanException` / `self.conf`（knowledge/ 全目录 grep）。
- 结果：`make_executable` 全 knowledge **0 命中**（rc=1）。
- 最相近条目：E307（`tools.build:compiler_executables`，**不同 conf key**）与
  经验仓 nymphrpc-0.1.1 build-system 条目（同为 compiler_executables dict 读取）。
- 差异：本条目主题是"conf 未注册导致 self.conf.get() 抛 ConanException"，
  E307/经验仓主题是"conf 是 dict 需整体读取"——机制、错误签名、修复路径均不同。
- 新增价值：为 Makefile 型 recipe 确立"先 PATH 探测、不盲用未验证 conf"的解析模式；
  与 E307 互补构成 Conan conf 图谱的独立节点。

## 禁止做法

- 不要 `self.conf.get("tools.build:make_executable", ...)`——在 OHOS 适配版
  Conan 2.29.1 下必然抛 ConanException。
- 不要假设 OHOS 适配版 Conan 的 conf 注册表与官方一致；新 key 使用前
  必须先 `conan config list` 验证。
