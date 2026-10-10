# rgf 3.12.0 适配笔记

## 编译环境
- 构建系统: cmake（上游构建入口在 `RGF/CMakeLists.txt`，单可执行目标）
- 编译日期: 2026-09-28
- 编译器: clang/clang++（OHOS SDK，profile `ohos-aarch64`，host == build）
- 依赖: 无（RGF 核心仅链接 C++ 标准库）
- 状态: built（首轮未提交工作树；真机 rule4 门禁通过前不标 published）

## 软件说明
rgf（Regularized Greedy Forest，正则贪心森林）是树集成机器学习方法
（Rie Johnson / Tong Zhang，IEEE TPAMI 2014）的 C++ 实现，用于回归与
二分类的训练/预测/联合训练预测（`rgf train|predict|train_predict`）。
本次路径 A 只打包原始 RGF 实现（与 Homebrew 公式 `cd RGF` 范围一致）：
单二进制 `bin/rgf` + 示例数据（`share/rgf/examples/sample`）+ 许可证。
FastRGF（OpenMP 多核变体）与 python-package / R 包装器不在本次范围内。

## 版本坐标
上游 tag `3.12.0`，取 GitHub tag 归档
`https://github.com/RGF-team/rgf/archive/refs/tags/3.12.0.tar.gz`
（sha256 `c197977b…57dc86`，与 Homebrew `rgf.rb` 同值，可互证）。

## 编译步骤
```bash
cmake <source>/RGF -DCMAKE_BUILD_TYPE=Release   # 经 CMakeToolchain（ohos-aarch64）
cmake --build .                                 # HMBS 注入 jobs=1，单作业
cmake --install . --prefix <package_folder>    # 落盘 bin/rgf
```
配方在 `build()` 内不调用 `cmake.test()`：上游 RGF 核心零 ctest 注册，
空跑 `ctest` 会伪造覆盖，审计结论见 `test_package/MANIFEST.yml`。

## 上游测试审计（R51 第一步）
- `RGF/CMakeLists.txt`：唯一构建目标 `add_executable(rgf ...)` +
  `install(TARGETS rgf DESTINATION bin)`；全文无 `enable_testing`、
  无 `add_test`、无 gtest 宏。
- `RGF/` 下无 `tests/`、`test/` 目录；`RGF/examples/sample/` 共 14 个
  文件，全为 `.x/.y` 数据与 `.inp` 参数文件（演示输入，无断言框架）。
- `python-package/tests/` 存在，但只覆盖 Python 包装器
  （需 Python + scikit-learn/scipy/numpy），不测试被打包的 C++ 二进制，
  不计入本包口径（`upstream_test_total: 0`，`manual_audit`）。
- 防假绿：消费者测试断言产物**非空**（`test -s`）、预测行数用
  `grep -c -E` 与测试行数硬比对、错误路径断言**非零退出码**
  （缺失输入、未知动作），避免空文件比空文件报通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 根目录无 CMakeLists，直接 configure 会报缺构建入口 | 上游把 RGF/FastRGF/python-package 并排放在仓库根，CMake 入口在 `RGF/` 子目录 | `cmake.configure(build_script_folder=<source>/RGF)` 定点，与 Homebrew `cd RGF` 同范围；不为根目录补傀儡 CMakeLists |
| 2 | 是否需要打包 FastRGF？ | FastRGF 需 OpenMP（`find_package(OpenMP REQUIRED)`），增加工具链不确定性；Homebrew 公式亦只交付 `bin/rgf` | 路径 A 只交付 RGF 原始实现，FastRGF 明确列为未覆盖面，不静默丢弃 |
| 3 | 真机预检 configure 失败：`-- The C/CXX compiler identification is unknown` + `The CMAKE_C_COMPILER: /data/service/hnp/bin/clang ...`，`-- Configuring incomplete`（第 1 轮曾误判为平台名问题，加 `CMAKE_SYSTEM_NAME=Linux` 后告警消失但失败原样复现） | 非平台名问题，而是 E557 宿主 lld 运行时故障：OHOS clang 驱动在链接步 spawn 动态链接的宿主 `lld`，其 NEEDED `libxml2.so.16` 在 worker 上无法解析，lld 启动即死，CMake 报编译器探测失败（与已合入 ls-hpack/2.3.5 CI PR #7487 同一指纹） | 移植 ls-hpack 的链接器宿主运行时门禁：`build()` 在 `cmake.configure()` 前用配置 clang 做真实 compile+link 探针；ambient 失败则从活动工具链派生含 `libxml2.so.16` 的目录，以 build-scoped `Environment` prepend 到 `LD_LIBRARY_PATH`；全失败则 fail closed 抛完整诊断。不绕过 CMake 编译器检查、不硬编码路径、不污染全局环境 |
| 4 | 上游 `RGF/CMakeLists.txt` 无任何 `cmake_minimum_required`，CMake 4.x 在 `project(rgf)` 处拒配（E103/E187 类） | 上游 CMakeLists 只有 `if(MSVC)` 分支内才声明 3.1，Linux/OHOS 路径无版本声明 | `generate()` 与 `cmake.configure(variables=...)` 双通道传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（照搬 oatpp/1.3.1：toolchain 值读取时机过晚，必须同时走 configure 命令行） |
| 5 | 上游 `set(CMAKE_INSTALL_PREFIX ${CMAKE_CURRENT_SOURCE_DIR})` 硬编码安装前缀，会覆盖工具链注入的包前缀，`cmake --install` 落盘到源码缓存而非包目录 | plain `set()` 在 toolchain 之后执行，无条件覆盖 | 新增 `patches/0001-remove-hardcoded-install-prefix.patch` 删除该行（保留 `EXECUTABLE_OUTPUT_PATH` 与 Homebrew 行为一致）；`build()` 首行 `apply_conandata_patches(self)` |
| 6 | 真机第 3 轮仍 `System is unknown to cmake, create: Platform/HarmonyOS` + `CMAKE_C/CXX_COMPILER ... /data/service/hnp/bin/clang` 自检失败（E092 指纹；cmake 4.4.3 无 Platform/HarmonyOS.cmake） | 第 1 轮 Linux 别名单独试过仍失败（当时 E557 lld 宿主运行时故障仍在，被误判为别名无效）；第 2 轮只加 lld 门禁仍失败（未知平台名下编译器 sanity 必挂）。双根因需叠加 | `generate()` + `cmake.configure(variables=)` 双通道设 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（先例 lzo/2.10、zxc/0.9.1、ayatana-ido/0.10.4-v2；上游 RGF 无 Linux-only 分支，仅 MINGW/MSVC 特例，tag 3.12.0 实证），保留 E557 lld 门禁；不绕过 CMake 编译器检查 |
| 7 | 真机第 4 轮同一指纹复现（C/CXX identification unknown，`cmake.configure` 行号 349→354 证明 Linux 别名已生效运行但失败不变） | 平台别名假设被证伪：别名只消警告，编译器探针仍挂。裸探针（无 target/sysroot 旗）与 CMake 探针（带工具链旗）用不同编译器路径/旗集时会分叉：profile 固定绝对路径 `/data/service/hnp/bin/clang{,++}`，该文件在 worker 上缺失或不可执行时工具链仍嵌入悬空路径，而配方探针回退到 PATH clang 仍可通过，掩盖分叉 | 改换路线：`generate()` 加编译器可用性门禁（isfile+X_OK 双检，不可用则 `tc.variables` 覆盖为 PATH 解析值并 warning，沿用 naga/ayatana-ido 先例；可用时零改动）；`_get_cc` 同步加 X_OK；`build()` 包裹 `cmake.configure`，失败时打印 `CMakeError.log`/`CMakeOutput.log` 尾部（`CMAKE_DIAG`）再抛，下一轮凭真实编译器报错而非猜测定因 |

## 测试情况

### 上游官方测试
无（0/0，审计见 `test_package/MANIFEST.yml`）。

### 鸿蒙特有（消费者）测试
`test_package/test_rgf.sh`（12 条断言，设计值；实测数以真机
`rgf-consumer: P/A assertions passed` 汇总行为准）：
- 包内 `rgf` 在 PATH 可解析且可执行；
- 现场合成 8 行 3 特征回归集（离线、确定性），`train_predict`
 （`reg_L2=1,loss=LS,test_interval=5,max_leaf_forest=20`，小规模保证
  真机单作业秒级完成）退出码 0；
- `out/m-01`、`.pred`、`.info` 三产物非空；`.pred` 恰 2 行数值预测
  （与 2 行测试输入对应）；`.info` 含 `leaf` 结构字样；
- 缺失训练文件与未知动作分别非零退出（ harness 存活性证据）。

## 验证结果
待 HMBS 真机预检回填（本轮不猜数字；`conan create` 日志中的
`HMBS_TEST_PACKAGE_RESULT` / `HMBS_UPSTREAM_TEST_RESULT` 为准）。

## 未覆盖面
- FastRGF 多核变体（含 OpenMP 路径）未构建验证。
- 大规模示例（`regress.train.x`  full 500 叶训练）未在消费者测试中
  全量复跑（耗时）；功能等价性由小规模端到端覆盖。
- 模型跨端序迁移（上游文档 `_AZ_BIG_ENDIAN_` 章节）未验证
  （同端序真机无此需求）。

## 注意事项
- `rgf` 为纯 CLI（`package_type = "application"`），软件级
  `commands.json` 已声明（R38）。
- `/tmp` 在目标机可能只读：测试工作目录建在包测试当前目录
  （`rgf-test-workdir`），不依赖 `/tmp`。
