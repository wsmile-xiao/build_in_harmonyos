# qt5-qtscxml 5.15.2 Build Notes

## Source
- Upstream tarball: qtscxml-everywhere-src-5.15.2.tar.xz (download.qt.io 官方源)
- sha256: 60b9590b9a41c60cee7b8a8c8410ee4625f0389c1ff8d79883ec5a985638a7dc（download.qt.io 与腾讯镜像双源实测一致）

## Build System
- qmake (Qt5 addon module)
- Products: libQt5Scxml.so (src/scxml), qscxmlc host tool (tools/qscxmlc),
  QtScxml QML plugin (src/imports/scxmlstatemachine)

## Dependency Resolution
- qt5-qtbase/5.15.2.2: qmake/moc/rcc + Qt5Core/Qt5Test (testlib)
- qt5-qtdeclarative/5.15.2: Qt5Qml + qml/ import path (src/imports 与上游测试的 qml 依赖)
- .pri 合并: qtdeclarative 的 mkspecs/modules/*.pri 需并入可写 Qt prefix，
  否则 qtHaveModule(qml) 为假，src/imports 与 tests 会被静默跳过

## Build Steps
1. 建可写 Qt prefix（qt-prefix 模式，同 qtmultimedia 先例）
2. qmake -spec linux-clang qtscxml.pro "CONFIG -= tests_need_tools examples_need_tools"
3. make -j4 QMAKE_STRIP=""
4. qscxmlc 工具 ELF 签名（binary-sign-tool -selfSign 1）
5. tests/auto 各套件独立目录 qmake+make+run（QT_QPA_PLATFORM=offscreen）
6. make install INSTALL_ROOT=<staging> 后搬入包目录

## Upstream Tests (real run, rule4)
- tests/auto 五套件真跑（配方 build() 内 qmake+make+run，QT_QPA_PLATFORM=offscreen）：
  - parser: Totals 42 passed, 0 failed
  - statemachine: Totals 20 passed, 0 failed
  - statemachineinfo: Totals 3 passed, 0 failed
  - dynamicmetaobject: Totals 4 passed, 0 failed
  - compiled: Totals 11 passed, 0 failed（STATECHARTS 由签名后的 qscxmlc 编译）
  - 五套件合计 80 passed / 0 failed
- scion 套件（W3C SCXML 一致性集，编译生成 273 个测试类）本地实测：
  47 项 PASS 后在首个依赖 ECMAScript 数据模型的用例处被 OHOS 沙箱 JIT 限制杀死
  （mprotect failed in ExecutableAllocator::makeExecutable: Permission denied，
  SIGSEGV rc=139）——环境限制非库缺陷，与仓内 qt5-qtdeclarative/5.15.2 先例
  的 JIT 限制同根因；上游 scion.pro 自带 BLACKLIST 与该限制无关

## Issues Encountered
- qscxmlc 为 host_build 工具，未签名时 OHOS 加载器拒绝执行（Operation not
  permitted）→ binary-sign-tool -selfSign 1 后可运行；package() 阶段对包内
  bin/ 全部 ELF 做自签
- tst_compiled 通过 QMAKE_EXTRA_COMPILERS 调用 qscxmlc 编译 STATECHARTS，
  故 qscxmlc 必须先签名再跑 compiled 套件
- 构建宿主环境注入的 LD_LIBRARY_PATH 携带不兼容 libc++_shared.so 副本时会
  遮蔽系统版本导致 qmake/cmake 报 "Error relocating ... symbol not found"——
  测试子进程环境必须确定性构造（源树 lib + 依赖包 lib + toolchain lib），
  不继承父级 LD_LIBRARY_PATH

---

**编译结束**: 2026-10-06
**最终状态**: built
