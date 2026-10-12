# qt5-qtwebsockets 5.15.2 适配笔记

## 编译环境
- 构建系统: qmake
- 编译日期: 2026-10-06
- 编译器: clang/clang++ (OHOS llvm 15)
- 状态: built

## 编译步骤

1. `init-archive` 生成归档骨架（archives/q/qt5-qtwebsockets/5.15.2/）
2. 源码：官方单条 URL（download.qt.io qtwebsockets-everywhere-src-5.15.2.tar.xz，R39），sha256=a0b42d85...（清华 tuna / 中科大 ustc / download.qt.io 三源实测一致）
3. qmake 构建沿用 qt5-qtcharts/qtmultimedia 模式：私有可写 Qt prefix 镜像 qtbase（symlink + 重写 mkspecs 中 .pri 的 build-dir 引用）+ `qmake -spec linux-clang`
4. `make install STRIP=true`（qmake strip --strip-unneeded 会破坏动态符号表导致 dlopen 失败）
5. 打包后重写 .prl/.la/.pc 中残留的 build-dir/source-dir 路径为 package_folder
6. 上游测试（详见下节）在 conanfile.py build() 内执行：私有 mkspecs 开启 private_tests + reduce_exports 挪 disabled → 9 个 QTest 套件全部构建；tst_* 先经 binary-sign-tool 签名再 `make check -k` 回环执行；日志解析强制校验（套件数=9、失败必须全部在环境限制白名单内，否则构建失败）
7. 打包 .so 经 binary-sign-tool -selfSign 1 签名（qrencode 先例）
8. test_package：find_package(Qt5WebSockets) + 127.0.0.1 回环 RFC 6455 echo 往返冒烟测试

## 上游测试实测（rule4：真实数字）

tests/auto/websockets 共 9 个 QTest 套件、67 个测试函数、7322 个数据用例，
全部在 conan create 的 build() 阶段构建并执行（LD_LIBRARY_PATH 指向构建产物
lib + qtbase lib，127.0.0.1 回环，无需外网）：

| 套件 | 数据用例数 | 通过 | 失败 |
|------|-----------|------|------|
| tst_QWebSocketCorsAuthenticator | 3 | 3 | 0 |
| tst_WebSocketProtocol | 5042 | 5042 | 0 |
| tst_DataProcessor | 2135 | 2135 | 0 |
| tst_WebSocketFrame | 54 | 54 | 0 |
| tst_HandshakeRequest | 47 | 47 | 0 |
| tst_HandshakeResponse | 3 | 3 | 0 |
| tst_QDefaultMaskGenerator | 4 | 4 | 0 |
| tst_QWebSocket | 21 | 20 | 1 |
| tst_QWebSocketServer | 13 | 13 | 0 |
| **合计** | **7322** | **7321** | **1** |

唯一失败：`tst_QWebSocket::tst_errorString`（tst_qwebsocket.cpp:630）——测试向
`ws://someserver.on.mars:9999` 发起连接并预期 HostNotFoundError，但构建环境的
DNS 对任意域名返回 fake-IP（实测 `ping someserver.on.mars` 解析为 198.18.0.101
并可连通），实际得到 RemoteHostClosedError。属环境限制（DNS 劫持/fake-IP 网关），
非库缺陷：同一套件内其余 20 个用例（含真实回环连接、握手、帧收发）全部通过。
该用例已列入 conanfile.py 的 `_ALLOWED_FAILURES` 白名单并在日志中输出警告；
白名单之外的任何失败都会使构建失败（防虚报）。

另：tests/auto/cmake（test_module_includes）与 tests/auto/qml（依赖 QtQuick，
本包不引入 qml 模块）不在执行范围；tests/auto/bic 仅数据文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 私有测试目录不进 SUBDIRS | qtbase mkspecs 的 private_tests 特性默认 disabled | 私有 prefix 的 qmodule.pri 中把 private_tests 从 disabled 挪到 enabled |
| 2 | 私有测试链接失败（QWebSocketFrame 等未定义） | reduce_exports 特性使私有类符号默认隐藏 | qmodule.pri 中把 reduce_exports 挪到 disabled_features（Qt developer-build 等效）；**特性只能挪不能删**，删除会使 qtConfig() 报 "Could not find feature" |
| 3 | 构建拉入 qtdeclarative 等未声明依赖 | 缓存中 qtbase 包 mkspecs 被同仓其他 Qt5 模块构建污染（86 个 pri 中 34 个外来） | 配方剪枝：pri 中含非 qtbase 的 conan2 绝对路径即删除；原始 CI 下载的 qtbase 包此步为空操作 |
| 4 | tst_* 可执行文件运行前需签名 | OHOS ELF 签名机制 | llvm-objcopy --remove-section .codesign + binary-sign-tool sign -selfSign 1（coinutils 先例） |
| 5 | tst_errorString 失败 | 环境 DNS 对任意域名返回 fake-IP | 环境限制白名单 + 文档化；白名单外失败即构建失败 |
| 6 | OHOS conan 工具链把 CMAKE_SYSTEM_NAME 映射为 HarmonyOS，Qt5 Config 不识别 | qmake 生成的 Qt5WebSocketsConfig.cmake 按 Linux Qt5 布局 | test_package 的 generate() 双覆盖 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=arch（adamstark-audiofile/adios2 先例） |

## 源码修改

- 无补丁（patches_applied 为空），全部为构建系统层适配（私有 prefix 的 mkspecs 特性调整，不触碰上游源码）

## 依赖版本

- qt5-qtbase/5.15.2.2（已发布）

## 验证结果

```bash
conan create: G0-G4 门禁通过，package 成功
上游测试: 9 套件 / 7322 用例 → 7321 通过 / 1 失败（环境限制白名单，见上）
test_package: ./test_qt5_qtwebsockets → exit 0（回环 echo 往返 PASS）
签名: 打包 libQt5WebSockets.so.5.15.2 binary-sign-tool 签名成功
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | qmake 配方（私有 prefix 镜像 + 特性翻转 + 外来 pri 剪枝 + 上游测试实测与白名单校验 + STRIP=true + .prl/.pc 重写 + .so 签名） |
| conandata.yml | 官方单条 URL（R39）+ sha256 |
| test_package/ | 消费者冒烟测试（CORS API + Version13 + 127.0.0.1 echo 往返） |
| manifest.yaml / notes.md | 归档元数据与适配笔记 |

## 注意事项

- RUNPATH 为 $ORIGIN（相对寻址），与 qtbase 自身库一致，无绝对路径泄漏
- 打包产物含 include/QtWebSockets/{public,5.15.2/private}、lib/cmake/Qt5WebSockets、lib/pkgconfig、mkspecs/modules{,-inst}/qt_lib_websockets*.pri——后续 Qt5 模块（如 qt5-qtwebchannel 等）可用同一模式链接
