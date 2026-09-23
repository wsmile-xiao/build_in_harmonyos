# check 0.11.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载官方源码 `https://github.com/libcheck/check/releases/download/0.11.0/check-0.11.0.tar.gz`（SHA-256: 24f7a48aae6b74755bcbe964ce8bc7240f6ced2141f8d9cf480bc3b3de0d5616）
2. CMake 配置：`cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（OHOS 交叉/本机构建同一参数）
3. `make -j4` 构建 libcheck.a（静态库）+ 测试程序
4. `ctest` 及 shell 脚本全量运行上游测试（全部通过）
5. `conan create`（test_package 消费者验证通过）→ conan-verify G0-G4/L2/L4/L5 全过 → finish W3 本地 CI 模拟通过

> 注意：本机无 root，github.com 直连超时；本地下载/构建时经 ghfast.top 镜像拉取 tarball，
> 但 conandata.yml 保留官方 URL（R39），镜像仅用于本地拉取动作。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure 报 "Compatibility with CMake < 3.5 has been removed" | 上游声明 `cmake_minimum_required(2.8)`，本机 CMake 4.1.2 已移除旧兼容 | conanfile generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | `cmake --install` 报 "file INSTALL cannot find build/Release/lib/libcompat.h" | 上游 lib/CMakeLists.txt 把源码头文件路径写成构建目录 | 补丁 0001 改为 `${CMAKE_CURRENT_SOURCE_DIR}/libcompat.h` |
| 3 | check_check 单测"挂起"（ctest 120s 超时） | 超时类测试含真实 sleep（CK_DEFAULT_TIMEOUT 0.5~6s 及 scaling 用例），整套需 ~9 分钟 | 以 560s 上限完整运行，EXIT=0；台账如实记录 |

## 源码修改

- `patches/0001-lib-CMakeLists.txt.patch`: lib/CMakeLists.txt 第 73 行 install 路径
  `${CMAKE_BINARY_DIR}/lib/libcompat.h` → `${CMAKE_CURRENT_SOURCE_DIR}/libcompat.h`

## 依赖版本

- 无外部依赖（仅 libm/librt/libpthread 系统库）
- CMake 4.1.2（本机），Conan 2.29.1（OHOS 适配版），clang 15.0.4

## 验证结果

```bash
# 上游测试：check_check EXIT=0（914 主套件 + 260 subordinate），check_check_export EXIT=0（809+260）
# shell 脚本测试 6/6 EXIT=0；源码声明 368 项中独立用户用例 358/358 (100%) 通过
# conan-verify 全门禁 PASS；finish W3 本地 CI exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 构建配方（含 CMAKE_POLICY_VERSION_MINIMUM 兼容注入） |
| conandata.yml | 官方源 + SHA-256 + 补丁声明 |
| test_package/ | 消费者用例（HarmonyOS 专项，公开 API 编译链接运行） |
| patches/0001-lib-CMakeLists.txt.patch | 上游 install 路径缺陷修复 |
| reports/upstream-test-ledger.md | 上游测试双口径台账 |
| reports/test-report.md | 测试报告 + W2/W3 基线隔离审计 |

## 注意事项

- 0.15.2 归档已存在（同软件），本次为独立版本目录 0.11.0，互不影响
- check 0.11.0 CMake 构建不产出 checkmk 工具（R38 判定为纯库，无需 commands.json 新增）
- OHOS /tmp 只读（E002）：所有测试/运行均设置 TMPDIR/TMP/TEMP 指向可写目录
