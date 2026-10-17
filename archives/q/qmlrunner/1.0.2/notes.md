# qmlrunner 1.0.2 适配笔记

## 编译环境
- 构建系统: cmake（上游为 qmake，适配新增 CMakeLists.txt）
- 编译日期: 2026-10-01
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，--target=aarch64-linux-ohos）
- 目标平台: HarmonyOS PC / OpenHarmony aarch64（os=OHOS, arch=armv8, libc++, cppstd 17）
- 状态: built（W3 本地验证通过，未 upload）

## W0 依赖检查（适配前第一件事）
- 直接依赖: `qt5-qtbase/5.15.2.2`（Core/Gui/Widgets）、`qt5-qtdeclarative/5.15.2`（Qml/Quick）
- 传递依赖: zlib/1.3.1、dbus/1.14.10、expat/2.8.2
- 验证方式: `conan download <ref> -r=ohpcd`（R35，禁用 conan list 判定）——全部可下载且含二进制包，
  无需自行补依赖。

## 上游测试清点（R51 第一步）
```bash
$ tar tzf qmlrunner-1.0.2.tar.gz | sed 's|^[^/]*/||'
.gitignore
LICENSE
README.md
qmlrunner.pro
src/main.cpp
$ grep -nE "check|test" qmlrunner.pro
（无输出——qmake 工程无 check/test target）
```
- 上游测试套件: **无**（无 tests/ 目录、无 CTest/pytest 注册、无测试框架依赖）
- 上游测试运行: 无可用测试（N=0），不计入通过率分母
- 适配后补全: test_package 消费者测试 13 条断言（见 reports/test-report.md）

## 编译步骤
```bash
# 1. 初始化（源码走官方 codeload 端点；设备侧直连正常）
python3 scripts/ohc-run.py init-build qmlrunner 1.0.2 \
  --url=https://codeload.github.com/rinigus/qmlrunner/tar.gz/refs/tags/1.0.2
source .build-context-qmlrunner-1.0.2

# 2. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight qmlrunner 1.0.2 --src "$BUILD_SRC_DIR"
# → task=cpp, detected=cpp（源文件 1 个，cpp 主体占比 100%）

# 3. 补丁生成（新增 CMakeLists.txt 经编辑追踪固化）
python3 scripts/ohc-run.py track-edit add qmlrunner 1.0.2 CMakeLists.txt
python3 scripts/ohc-run.py refresh-patch --auto qmlrunner 1.0.2

# 4. 配方验证（G0/G1/G2/G3 PASS；G4/L2/L4/L5 工具跳过，非失败）
python3 scripts/ohc-run.py conan-verify qmlrunner 1.0.2 --profile ohos-aarch64-device
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 安装后的 `bin/qmlrunner` 执行报 `Operation not permitted`（EPERM），而构建目录中的同名二进制可运行 | CMake install 阶段默认重写 ELF 的 RPATH（build rpath 与 install rpath 不一致时原地改写动态段），使 OHOS 链接器写入的 `.codesign` 段失效；鸿蒙内核拒绝执行签名不匹配的 ELF（E077 同族）。实测：构建产物与安装产物仅动态段区域不同（cmp 第 6037 字节起），构建产物带完整签名可执行 | CMakeLists 中 `set(CMAKE_SKIP_RPATH ON)` + `SKIP_BUILD_RPATH`/`SKIP_INSTALL_RPATH`，安装产物与链接产物逐字节一致（md5 相同）；运行期库解析交给 conanrun 的 `LD_LIBRARY_PATH`（diffpdf 配方同款运行时模型）。设备侧无 `/data/service/hnp` 签名工具（`binary-sign-tool` 不存在），四步重签路径不可用，避免修改是首选 |
| 2 | `conan-verify` G2 失败：ghfast.top 镜像注入后超时 | 工具为 GitHub URL 临时注入 ghfast.top 镜像（E017 预防），该镜像在当前网络不可达 | conandata.yml 改用 GitHub 官方 codeload 端点（与 archive/refs/tags 端点 302 同实体、字节级 SHA256 一致；仓库内 204 个配方同款端点），工具注入对 codeload 为空操作，设备直连实测 OK（14883 字节，sha256 与申报一致） |
| 3 | G2 二次失败：`BadZipFile: File is not a zip file` | codeload URL 末段是 tag 名（无扩展名），Conan `get()` 按末段推断为 zip（E483） | `get(..., filename="qmlrunner-1.0.2.tar.gz")` 显式指定文件名与格式（E483 推荐方案） |
| 4 | 测试环境无显示 | OHOS PC 当前无 X11/Wayland 平台插件运行时保证；qt5-qtbase 提供 offscreen/minimal/vnc 插件 | test_package 用 `QT_QPA_PLATFORM=offscreen` + `QT_QUICK_BACKEND=software`（软件场景图，无 GPU），`QT_PLUGIN_PATH`/`QML2_IMPORT_PATH` 显式指向依赖包内插件与 QML 模块 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：新增 `CMakeLists.txt`（唯一源码级变更）。
  - 上游 qmake(.pro) 在 OHOS 无可用 mkspec/交叉工具链路径，改为 CMake：
    手动接线 qt5-qtbase/5.15.2.2 与 qt5-qtdeclarative/5.15.2 的 include/lib 目录
    （该 Qt 打包未接 CMakeDeps config，diffpdf/disomaster 同模式）。
  - `src/main.cpp` 无 Q_OBJECT/qrc，不需要 moc/rcc。
  - `CMAKE_SKIP_RPATH` 等三项见问题 1。
  - 补丁为新增文件（`--- /dev/null`），无平台宏、无绝对路径、无凭据。

## 依赖版本
- qt5-qtbase/5.15.2.2（Core/Gui/Widgets，传递 zlib/1.3.1、dbus/1.14.10→expat/2.8.2）
- qt5-qtdeclarative/5.15.2（Qml/Quick）

## 验证结果

```bash
$ conan create archives/q/qmlrunner/1.0.2 --user=ohpcd --channel=stable \
    -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device --build=missing
...
        [step] positive 1: qmlrunner -P <root> myapp
        [ok] QML window loaded, event loop quit cleanly
        [step] positive 2: -noscale + extra -path (extra import path)
        [ok] -noscale / -path combination accepted
        [step] negative 1: no application name (usage)
        [ok] usage + rc=255
        [step] negative 2: unknown option
        [ok] unknown option + rc=253
        [step] negative 3: duplicate application name
        [ok] duplicate app name + rc=254
        [step] negative 4: QML application not found
        [ok] missing app + rc=254
        [ok] ALL PASS (2 positive + 4 negative cases)
```

```bash
$ python3 scripts/ohc-run.py conan-verify qmlrunner 1.0.2 --profile ohos-aarch64-device
✅ 配方验证通过: qmlrunner 1.0.2（G0/G1/G2/G3 PASS；G4/L2/L4/L5 因工具未解析到包 ID 跳过，非失败）
```

- 安装产物与构建产物逐字节一致：`md5sum` 均为 `9f1f7ed09c002eac1d1644ddf5f8a698`（签名保留）。
- 消费者测试：2 正例（真实 QML 窗口加载 + 事件循环退出 rc=0；含 `-noscale`/`-path` 组合）
  + 4 负例（CLI 契约与退出码 255/253/254/254），共 13 条断言，全部通过。

## 交付物
| 文件 | 说明 |
|------|------|
| bin/qmlrunner | QML 应用启动器（aarch64 OHOS，动态链接 Qt5） |
| licenses/LICENSE | GPL-3.0 许可证原文 |

## 注意事项
- 运行时需 `QT_PLUGIN_PATH`（qt5-qtbase/plugins）与 `QML2_IMPORT_PATH`（qt5-qtdeclarative/qml）；
  无显示环境加 `QT_QPA_PLATFORM=offscreen`，无 GPU 加 `QT_QUICK_BACKEND=software`。
- 不要对安装后的二进制做任何后处理（strip/patchelf/objcopy），否则 `.codesign` 失效不可执行（E077）。
- 下游集成（如桌面启动器）通过 conanrun 环境获得 PATH 与 LD_LIBRARY_PATH。

## 适配路径
- **路径 A（基础适配）**。本次适配未发现未被知识库覆盖的类级新问题：
  CMake install 重写 RPATH 导致 `.codesign` 失效属 E077 同族（本包以
  `CMAKE_SKIP_RPATH` 避免修改，设备侧无签名工具时的首选路径）；codeload URL
  的 `get()` 文件名推断属 E483；CMake/OHOS 平台映射属 E092。经验已在
  manifest `knowledge_gained` 中沉淀，不单独走路径 B。

**编译结束**: 2026-10-01 19:00
**最终状态**: built
