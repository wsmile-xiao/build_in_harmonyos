# mysql-connector-c 26.7.0 OpenHarmony 适配知识库

> 来源：知识库扩展 Issue #2559
> 适配 PR：#7804

---

## 一、问题背景

在将已有 Linux 三方库迁移到 OpenHarmony PC 时，仅完成主库交叉编译并不能充分说明适配质量。实践中常见两个问题：

1. **glibc/musl 差异**：上游源码依赖 glibc 特有 API，而 OpenHarmony 使用 musl，导致源码无法直接编译。
2. **测试框架迁移困难**：主库能够成功编译，但上游测试框架无法直接迁移到 Conan 2.x + OpenHarmony 交叉编译环境，导致测试覆盖无法复用。

本 Issue 以 `mysql-connector-c 26.7.0`（实际上游为 MySQL Connector/C++）为验证对象，总结一套可复用的：

- glibc / musl 兼容处理方法；
- Conan 2.x + CMake GTest imported target 迁移方法；
- 上游测试发现、编译、链接、运行状态分层统计方法；
- 无目标设备时的交叉编译测试验证方法。

---

## 二、两个核心问题

### 问题一：glibc resolver API 在 OpenHarmony/musl 下不可用

上游 `cdk/foundation/socket_detail.cc` 的 POSIX 实现使用：

- `res_ninit`
- `res_nsearch`
- `res_nclose`

这些接口属于 glibc resolver API，在 OpenHarmony/musl 环境下不可直接使用。

#### 处理原则

- 不要通过伪造 glibc 符号的方式强行通过编译。
- 对于不影响核心连接能力的可选功能，应明确划分功能边界，在 OHOS 平台进行条件裁剪，并记录功能限制。

#### 本次处理方式

- 保留非 OHOS 平台原始 resolver 行为；
- OHOS 下禁用 SRV resolver 查询路径；
- SRV lookup 返回空结果；
- 普通 MySQL X Protocol 连接逻辑保持不变。

对应 patch：`patches/0001-ohos-disable-glibc-resolver-api.patch`

#### 已知限制

- OpenHarmony 下暂不支持 DNS SRV 服务发现。
- 普通 MySQL X Protocol 连接不受该 resolver patch 影响。

#### 适用场景

> "上游依赖 glibc 非标准扩展，但该功能不是核心功能，且 musl 无等价 API"的三方库迁移场景。

---

### 问题二：Conan 2.x GTest imported target 与旧 CMake 集成方式不兼容

部分旧项目的 GTest CMake 集成逻辑仍假设：

```
GTEST_LIBRARIES
```

返回实际库文件路径，例如：

```
/xxx/lib/libgtest.a
```

但在现代 CMake + Conan 2.x 环境中，`find_package(GTest)` 可能返回：

```
GTest::gtest
```

即 CMake imported target。

如果旧项目继续执行：

```
list(GET GTEST_LIBRARIES 0 gtest_location)
```

然后：

```
IMPORTED_LOCATION "${gtest_location}"
```

最终会错误地把 `GTest::gtest` 当作文件路径使用，导致 legacy gtest imported target 无法正确定位实际静态库，并且 `INTERFACE_INCLUDE_DIRECTORIES` 不会自动传递，从而引发 `gtest/gtest.h: No such file or directory`。

---

## 三、通用迁移方案

本次没有修改任何单个 upstream test，而是在上游 GTest 集成层增加 bridge，对应 patch：

```
patches/0002-ohos-support-conan-gtest-imported-targets.patch
```

只修改：`cdk/cmake/gtest.cmake`。

### Step 1：区分文件路径和 imported target

检测 `GTEST_LIBRARIES` 中获得的是：

- 实际 library path；
- 还是 `GTest::gtest` target。

对于传统路径继续使用原有逻辑；对于 imported target 模式，获取 Conan GTest package 的安装前缀，并定位：

- `libgtest.a`
- `libgtest_main.a`

避免将 target name 直接设置为 `IMPORTED_LOCATION`。

### Step 2：传递 interface include directories

现代 `GTest::gtest` 已经携带 `INTERFACE_INCLUDE_DIRECTORIES`，旧项目自行创建的 legacy `gtest` target 并不会自动继承这些属性。

因此需要将 `GTest::gtest` 和 `GTest::gtest_main` 的 include interface 传递给 legacy imported target。

这样可以解决：

```
gtest/gtest.h: No such file or directory
```

等问题。

### Step 3：尽量不修改具体测试用例

测试迁移应优先修改：

- test framework integration；
- build-system bridge；
- imported target compatibility；

而不是逐个修改 `TEST` / `TEST_F` 源码。

这样做的好处：

1. 最大程度保留上游测试真实性；
2. 降低后续升级上游版本的维护成本；
3. 使方案能够复用于其他旧 CMake + Conan 2.x 项目。

---

## 四、测试分层统计方法

迁移上游测试时，不应只写"有多少测试通过"。至少要区分四种数字：

1. **source declarations**：源码中 `TEST` / `TEST_F` 声明数量；
2. **CMake registered sources**：CMake 实际注册进入构建的测试源文件数量；
3. **successfully compiled / linked targets**：成功编译/链接的测试目标数量；
4. **runtime executed tests**：实际运行通过的测试用例数量。

否则容易把"交叉编译成功"错误描述成"测试运行通过"。

### mysql-connector-c 26.7.0 实例

源码 `TEST` / `TEST_F` 声明：

| 类型 | 数量 |
| --- | ---: |
| Unit | 75 |
| Integration | 204 |
| Integration 拆分 | devapi 127 + xapi 77 |
| Other | 0 |
| **Total** | **279** |

> 279 只是源码测试声明数量。上游 `cdk/CMakeLists.txt` 中存在 `IF(0)`，因此部分 cdk 单元测试目录默认不会加入实际构建。

实际进入 OHOS 交叉编译：

| 来源 | 测试 source 数量 |
| --- | ---: |
| common | 3 |
| devapi | 8 |
| xapi | 3 |
| **Total** | **14** |

最终统一链接为：`run_unit_tests`。

### 交叉编译结果

| 项 | 结果 |
| --- | --- |
| configure | PASS |
| compile | PASS |
| link | PASS |
| failed | 0 |

### OHOS-specific smoke test

| 项 | 结果 |
| --- | --- |
| 类型 | Conan `test_package` |
| 数量 | 1 |
| 结果 | `1/1 PASS` |

---

## 五、Runtime NOT RUN 说明

本次 `run_unit_tests runtime = NOT RUN`，**不能写成 PASS**。

### 原因

- 当前没有 OpenHarmony/aarch64 runtime runner；
- `hdc` 无连接设备；
- 无 `qemu-aarch64`；
- integration tests 还需要 MySQL 8.0+ X Protocol Server。

### 约定

> "cross compile PASS" 与 "runtime PASS" 必须明确区分。

对于没有运行环境的交叉编译项目，建议报告格式：

| 阶段 | 取值 |
| --- | --- |
| configure | PASS / FAIL |
| compile | PASS / FAIL |
| link | PASS / FAIL |
| runtime | PASS / FAIL / **NOT RUN** |
| NOT RUN reason | 明确填写 |

### Conan test_package

```
1/1 PASS
100% tests passed, 0 tests failed out of 1
```

该 smoke test 已正常执行并通过，覆盖：

- `find_package(mysql-connector-c CONFIG REQUIRED)`
- `mysql-connector-c::mysql-connector-c`
- `<mysqlx/xapi.h>`
- 静态库 `libmysqlcppconnx-static.a`
- 静态 consumer 所需 `STATIC_CONCPP`
- C/C++ 混合链接链路
- CTest 注册和运行

---

## 六、约束与限制

- OpenHarmony 下暂不支持基于 DNS SRV 的服务发现，普通 MySQL X Protocol 连接不受影响。
- 上游 `cdk/CMakeLists.txt` 中存在 `IF(0)`，部分 cdk 单元测试目录默认不加入构建。
- 上游 `run_unit_tests` 在当前环境无法 runtime 执行，结果为 NOT RUN。
- 上游 CMake `bootstrap()` 会启动子 CMake 并通过 `load_cache()` 覆盖 Conan toolchain 设置的 `BUILD_STATIC` / `WITH_SSL` / OpenSSL 路径，因此 recipe 中按照 Conan recipe 方式禁用了 upstream `bootstrap()`，并使用 Conan dependency graph 中的 OpenSSL 路径。
- 279 是源码 `TEST` / `TEST_F` 声明数量，不等同于实际生成的测试可执行文件数量。
- 未为了通过测试而修改任何单个测试用例；所有测试源码保持上游原样。

---

## 七、通用迁移最佳实践

对于 OpenHarmony 三方库测试迁移，可采用以下流程：

1. 先统计上游 `TEST` / `TEST_F` 等测试声明；
2. 再分析 CMake 实际注册了哪些测试源码和 target；
3. 优先解决测试框架本身的 CMake / Conan compatibility；
4. 不为了通过编译而批量修改单个 upstream test；
5. 分别记录 configure / compile / link / runtime；
6. 无设备时将 runtime 明确标记为 NOT RUN 并填写原因；
7. 使用 `test_package` 对安装后的 package 进行 downstream smoke validation；
8. 对 glibc/musl 差异采用平台条件处理，并明确功能限制。

该方法不仅适用于 `mysql-connector-c`，也适用于大量：

- 旧 CMake 工程；
- 自建 legacy GTest target；
- Conan 2.x imported target；
- Linux/glibc → OpenHarmony/musl；

的三方库迁移场景。

---

## 八、本次验证结果

| 项 | 结果 |
| --- | --- |
| OpenHarmony aarch64 主库构建 | PASS |
| Conan package | PASS |
| Conan test_package | 1/1 PASS |
| 上游 GTest configure | PASS |
| 上游测试 source compile | PASS |
| `run_unit_tests` link | PASS |
| upstream runtime | **NOT RUN** |
| PR CI | PASS |

### 适配补丁列表

| Patch | 目标文件 | 解决问题 |
| --- | --- | --- |
| `0001-ohos-disable-glibc-resolver-api.patch` | `cdk/foundation/socket_detail.cc` | glibc resolver API 在 musl 不可用 |
| `0002-ohos-support-conan-gtest-imported-targets.patch` | `cdk/cmake/gtest.cmake` | Conan 2.x GTest imported target 与旧 CMake 不兼容 |
