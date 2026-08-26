# qt5-qtx11extras 5.15.2 适配笔记

## 编译环境
- 构建系统: qmake
- 编译日期: 2026-08-25
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
# 1. 修复 qt5-qtbase 包内 qt.conf 与 mkspecs/modules/*.pri 的构建目录引用
#    （同 qt5-qtsvg 先例，_fix_qtbase_paths）

# 2. 应用补丁（patches/）：
#    0001-bypass-xcb-gate.patch    src.pro: 绕过 qtConfig(xcb) 门控
#    0002-manual-xcb-link.patch    x11extras.pro: QMAKE_USE_PRIVATE xcb → 手动链接

# 3. qmake configure
qmake qtx11extras.pro -spec linux-clang \
  -after "XCB_INC=<libxcb>/include" "XCB_LIB=<libxcb>/lib"

# 4. 编译（防 strip，OHOS loader 拒绝 stripped ELF）
make -j2 QMAKE_STRIP=""
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 无产出（"Nothing to be done"） | 制品仓 qt5-qtbase/5.15.2 未启用 xcb 特性（QT_FEATURE_xcb=no），src.pro 中 `qtConfig(xcb) { SUBDIRS += x11extras }` 门控跳过子目录 | 补丁 0001：src.pro 直接 `SUBDIRS += x11extras` |
| 2 | `Project ERROR: Library 'xcb' is not defined` | qtbase 无 xcb qmake 模块定义，x11extras.pro 的 `QMAKE_USE_PRIVATE += xcb/nolink` 解析失败 | 补丁 0002：改为 `INCLUDEPATH += $$XCB_INC` + `LIBS += -L$$XCB_LIB -lxcb`，qmake 用 -after 传入路径 |
| 3 | python urllib SSL 证书验证失败 | 本机 CA 证书缺失 | `SSL_CERT_FILE=/data/service/hnp/python.org/python_3.12/lib/python3.12/site-packages/certifi/cacert.pem` |
| 4 | init-build 解压不完整（仅 13/105 文件） | init_build.py 解压逻辑在该 tarball 上异常 | 手动 `tar -xJf --strip-components=1` 重新完整解压 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| 0001-bypass-xcb-gate.patch | src.pro：`qtConfig(xcb) { SUBDIRS += x11extras }` → `SUBDIRS += x11extras` |
| 0002-manual-xcb-link.patch | x11extras.pro：`QMAKE_USE_PRIVATE += xcb/nolink` → `INCLUDEPATH += $$XCB_INC` + `LIBS += -L$$XCB_LIB -lxcb` |

## 依赖版本

- qt5-qtbase/5.15.2（制品仓）
- libxcb/1.16（制品仓；qx11info_x11.cpp 仅用 `<xcb/xcb.h>`，无需 libx11）

## 验证结果

```bash
# 本地编译验证
qmake qtx11extras.pro -spec linux-clang -after "XCB_INC=..." "XCB_LIB=..."
make -j2 QMAKE_STRIP=""
# 产物: lib/libQt5X11Extras.so.5.15.2 (+ .so/.so.5/.so.5.15 符号链接)
# 头文件: include/QtX11Extras/{QX11Info,QtX11Extras,qx11info_x11.h,...}
# mkspecs: mkspecs/modules-inst/qt_lib_x11extras*.pri
# cmake: lib/cmake/Qt5X11Extras/Qt5X11ExtrasConfig.cmake
# pkgconfig: lib/pkgconfig/Qt5X11Extras.pc
```

## 注意事项

- qt5-qtx11extras 在 OHOS 上编译成功（依赖 libxcb/libx11 已发布），但其 X11 语义在 OHOS 无 X11 显示服务器时运行时不可用（QX11Info 查询类仅编译期可用）；作为依赖包发布以支持 baka 等应用的编译链接闭合。
- 后续若 qt5-qtbase 以启用 xcb 特性重建，可移除 0001/0002 补丁并恢复官方 src.pro/x11extras.pro。
