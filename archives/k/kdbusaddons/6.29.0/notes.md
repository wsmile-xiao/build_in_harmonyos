# kdbusaddons 6.29.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM/KDE Frameworks 6)
- 编译日期: 2026-08-31 (r04: qtbase 6.11.1.1 Qt6DBus 消费核验轮)
- 编译器: clang/clang++ 15 (ohos-aarch64 profile, os=OHOS)
- 状态: built

## 编译步骤

r04 本轮（r03 已证明 ECM 6.29.0 可消费；本门禁核心为 qtbase/6.11.1.1 Qt6DBus 消费核验）：

1. **qtbase/6.11.1.1 消费门禁**（r04 前置，详见最终报告）：
   - `conan install --requires=qtbase/6.11.1.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=never` → exit 0（未从源码构建）
   - 制品内确认 `libQt6DBus.so.6.11.1`（1243776 B）与 `lib/cmake/Qt6DBus/Qt6DBusConfig.cmake` 存在
   - 真实 CMake 消费者 `find_package(Qt6DBus 6.9.0 REQUIRED NO_MODULE)` + `target_link_libraries(qt6dbus_consumer Qt6::DBus)` → configure + build 成功，二进制 NEEDED 含 libQt6DBus.so.6

2. **conan create**（-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同 profile）：
   - CMake configure 通过（含 ECMPoQmTools 的 find_package(Qt6 LinguistTools)、WITH_X11=OFF 跳过 X11-only GuiPrivate）
   - libKF6DBusAddons.so 构建成功；kquitapp6 工具构建成功
   - 上游 ctest（autotests + tests 共 4 项，均需活动 session bus；OHOS 构建机无 dbus-daemon，按运行环境限制记录，不阻塞包创建）
   - test_package：ctest 2/2 通过（test_kdbusaddons + test_kdbusaddons_ohos），直接运行 ./test_kdbusaddons 与 ./test_kdbusaddons_ohos 均 OK
3. **conan-verify** 全部门禁 PASS（G1/G0/G2/G3/G4, L2/L4/L5），报告在 reports/conan-verify-report.md
4. **finish 至 Step 5/10（W3 本地 CI 模拟）**：setup.sh 通过；build_and_test.sh 的 JC 门禁被 main 上其他库既有跟踪垃圾文件阻塞：
   - archives/i/isa-l_crypto/2.26/conandata.yml.orig（跟踪，feat(isa-l_crypto)）
   - archives/m/middleclass/4.1.1/conandata.yml.ghfast-bak（跟踪）
   - archives/s/swift-corelibs-blocksruntime/6.3.3/.staging-verified（跟踪）
   均为 2026-08-27 早于本任务的仓库既有基线，非 kdbusaddons 范围；按 SKILL 隔离/恢复规则记录外部首错，不修改他库，不重跑掩盖。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(Qt6DBus) 在 CMakeDeps 下找不到 | qtbase 用 cmake_find_mode=none，CMakeDeps 不生成 Qt6DBus 配置 | generate() 手动写 conan_cmakedeps_paths.cmake，把 qtbase lib/cmake 加入 CMAKE_PREFIX_PATH（kdnssd/kcoreaddons 同法） |
| 2 | Qt6Gui/Qt6GuiPrivate 为 X11-only | kdbusaddons CMakeLists `if(HAVE_X11) target_link_libraries(... Qt6::GuiPrivate)` 需 qtx11extras_p.h | WITH_X11=OFF → HAVE_X11=FALSE，跳过 X11-only 私有 Gui 链接（OHOS 无 X11） |
| 3 | 上游 ctest 依赖活动 D-Bus session bus | OHOS 构建机无 dbus-daemon（仅 gdbus） | karchive 先例：ignore_errors=True 记录实际结果，环境限制不阻塞包创建 |
| 4 | 首次 OHOS 测试断言 serviceName() 非空 | 无 session bus 时 Registration 构造早退，generateServiceName() 不执行，serviceName() 为空 | 修正 OHOS 测试断言为真实平台行为：isRegistered()==false 且 serviceName() 为空 |
| 5 | W3 JC 杂物门禁失败 | main 上 isa-l_crypto/middleclass/swift-corelibs-blocksruntime 的既有跟踪垃圾文件（外部历史基线） | 按 SKILL 隔离/恢复规则记录外部首错，不修改他库，不重跑掩盖，回报 external_blocked |

## 源码修改

- 无 patch（ECM 6.29.0 已发布 ohpcd，无需降版本补丁）

## 依赖版本（r04 实测消费）

| 依赖 | 版本 | registry 状态 |
|------|------|---------------|
| qtbase | 6.11.1.1 | ohpcd 已发布（Qt6DBus 消费门禁通过） |
| extra-cmake-modules (tool) | 6.29.0 | ohpcd 已发布（r03 证明可消费） |
| qt6linguisttools (tool) | 6.11.1 | ohpcd 已发布（kdnssd r03 已消费） |
| dbus | 1.14.10 | ohpcd 已发布（qtbase 传递） |

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=kdbusaddons/6.29.0  # exit 0，test_package 2/2 Passed
ohc-run.py conan-verify kdbusaddons 6.29.0   # G1/G0/G2/G3/G4 PASS，可标记 published
ohc-run.py finish kdbusaddons 6.29.0 built   # W3 JC 被 he 库既有跟踪垃圾文件外部阻塞
./test_kdbusaddons                           # KDBusService serviceName/isRegistered OK
./test_kdbusaddons_ohos                      # OHOS 平台行为断言 PASS（无 X11 依赖、无 bus 优雅降级）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（qtbase/6.11.1.1 + ecm 6.29.0 + qt6linguisttools/6.11.1） |
| conandata.yml | 官方源 URL + SHA-256 |
| test_package/ | test_kdbusaddons + test_kdbusaddons_ohos + MANIFEST.yml |
| manifest.yaml | 版本级元数据（built） |
---

**编译结束**: 2026-08-31 14:06
**最终状态**: built
