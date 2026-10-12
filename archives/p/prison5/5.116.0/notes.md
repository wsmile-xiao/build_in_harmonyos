# prison5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (Ninja)
- 编译日期: 2026-10-06
- 编译器: clang / clang++（HarmonyOS PC 工具链，aarch64，libc++）
- 状态: built（conan create 通过，本地预验证通过，未 upload）

## 上游结构（v5.116.0 tarball，sha256 双源核验一致）

Tier 1 KF5 条码抽象库：
| 目标 | 内容 |
|------|------|
| KF5Prison | 核心库：Prison::createBarcode 工厂 + QRCode(qrencode)/Code39/Code93/Code128/Aztec 生成器 |
| prison-datamatrix | CLI demo 工具（装到 bin/；DataMatrix 需 Dmtx，本包 Dmtx 关闭后运行即报错退出，随上游原样出货） |
| quick/scanner 子目录 | OPTIONAL TARGET 门控（Qt5Quick / Qt5Multimedia+ZXing），本包自然跳过 |

顶层 REQUIRED：ECM 5.116（tool_requires ecm/6.26.0）+ Qt5 5.15.2 CONFIG REQUIRED Core Gui（BUILD_TESTING 再加 Test Widgets）。
QRencode REQUIRED（`cmake/FindQRencode.cmake` 手写 module-mode 查找）；Dmtx/ZXing RECOMMENDED（可选）。

## 适配要点（KF5 链约定）

1. **QT_MAJOR_VERSION=5**：上游 `find_package(Qt${QT_MAJOR_VERSION}...)` 全链走 Qt5。
2. **Qt5 供给**：qt5-qtbase/5.15.2.2（force=True 归一图，DBus 能力超集二进制），原生 lib/cmake/Qt5* config 消费（cmake_find_mode=none + CMAKE_PREFIX_PATH 接线）。
3. **qrencode 接线**：上游是手写 FindQRencode.cmake（module mode），toolchain 预置 `QRencode_INCLUDE_DIRS`/`QRencode_LIBRARIES` 缓存变量短路 find_library/find_path（prison/6.18.0 先例），另把包前缀挂 CMAKE_PREFIX_PATH/CMAKE_LIBRARY_PATH 作兜底。
4. **可选后端裁剪**：`CMAKE_DISABLE_FIND_PACKAGE_Dmtx=ON` + `CMAKE_DISABLE_FIND_PACKAGE_ZXing=ON`（任务卡指定 qrencode 线，上游默认无此二依赖时的形态）；顺带自然关掉 quick/（Qt5Quick 门控）与 scanner/（Qt5Multimedia+ZXing 门控）子目录。
5. **CMAKE_SYSTEM_NAME=Linux 双覆盖**：toolchain 变量 + cache_variables 双写（OHOS→HarmonyOS 映射旁路，ECM 走 POSIX 分支；pan/0.165 + kpeople5 先例）。
6. **KF_SKIP_PO_PROCESSING=ON**（链约定：Qt5LinguistTools 未发布）；**KF_IGNORE_PLATFORM_CHECK=TRUE**。
7. **AUTOMOC/AUTORCC/AUTOUIC EXECUTABLE** 指向 qt5-qtbase bin 工具；`../b/mkspecs` 树从包内 mkspecs/ 重建（Qt5CoreConfigExtrasMkspecDir 硬编码路径，kpeople5 先例）。
8. **ELF 契约**：`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `-Wl,-soname,`（无版本号 DT_SONAME，W3 L5 闸）；`CMAKE_BUILD_WITH_INSTALL_RPATH=ON`（E537：链接后不再改写 ELF）。
9. **签名**：package 后 bin/* + lib/*.so 用 binary-sign-tool 重签（llvm-objcopy 先去 .codesign 节，p11-kit/0.26.2 配方内先例）。
10. **运行环境**：/system/lib64 前置 LD_LIBRARY_PATH（宿主工具与测试加载兼容 libc++）；ctest 运行链接兼容目录（build/bin 的 lib*.so 符号链接到上级 bin，kcoreaddons5/kpeople5 先例）。

## 上游测试（BUILD_TESTING=ON，ctest 真实执行）

6 个 autotest 全部 QTEST_APPLESS_MAIN（无 GUI 事件循环，.qrc 内嵌参考图，无 D-Bus、无 QStandardPaths 依赖）。Dmtx/ZXing 关闭后实际注册 4 个目标：

| 测试目标 | 槽数 | QTest 执行数（直跑实测） | 内容 |
|----------|------|------|------|
| prison-aztecbarcodetest | 18 | 53 | Aztec 编码全流程（网格/模式消息/数据/尺寸） |
| prison-code128barcodetest | 6 | 22 | Code128 编码 + 渲染 |
| prison-qrtest | 4 | 5 | QR 文本/二进制渲染 vs .qrc 参考图逐像素比对 |
| prison-reedsolomontest | 2 | 4 | Reed-Solomon 纠错核心 |
| **合计** | **30** | **84** | 4/4 目标通过（ctest 目标级 + 二进制直跑 Totals 双实证） |

prison-datamatrixtest / prison-zxingutiltest 由上游自身 `if(TARGET Dmtx::Dmtx)` / `if(TARGET ZXing::ZXing)` 守卫编译出局（非本配方跳过）。

## 验证记录

OHOS conan create（profile: ohos-aarch64，两遍全绿 RC=0，含 echo yes|conan remove 后干净重跑）：
- 上游 CTest：4/4 目标通过（18 测试函数、84 条 QTest 执行全过；目标级 ctest 输出 + build/bin 二进制直跑 Totals 双实证）
- test_package：1/1 通过（test_prison5，21 条断言全过；驱动真实公共 API + ELF 契约断言）

## 已知限制
- DataMatrix/PDF417/EAN13 条码与视频扫描器不在本包（可选后端裁剪，上游默认形态）。
- prison-datamatrix CLI 工具随上游原样出货：无 Dmtx 时运行报 "unsupported barcode type" 退出（exit 0 的 error 路径，上游行为）。
