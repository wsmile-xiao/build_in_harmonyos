# qtspeech-5.15.2-qtbase-mkspecsdir-stale-path-symlink（拟 E752）

> Contributor: j669539 / Status: **DRAFT** / Updated: 2026-10-07 / Source: PR !14839
> 拟提升编号：E752（最终由主编确认；取号经过见 .kv number_note——E543/E544 已入 graph，E545-E550 被在途 issue 主张，E551-E751 六层复核全占）

## 症状

Qt5 addon 模块（qtspeech 5.15.2 实测）在 conan create build() 内驱动上游 cmake 测试套件
（tests/auto/cmake 的 module_includes ctest）时，cmake configure 阶段直接 FATAL_ERROR：

```
CMake Error at .../Qt5Core/Qt5CoreConfig.cmake:14 (message):
  The imported target "Qt5::Core" references the file
  ".../p/<pkg-id>/../b//mkspecs/linux-clang" but this file does not exist.
```

或（上游套件 make check 入口，另一形态）：

```
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed.
```

本地原型实测：缺修复时上游 cmake 套件必挂（find_package(Qt5Core) FATAL_ERROR）。

## 根因

三层叠加（都在「qtbase 制品包不可重定位 + 新版 CMake + OHOS 平台探测」上）：

1. **qt5-qtbase 制品包残留构建期路径**：包内 lib/cmake/Qt5Core/Qt5CoreConfigExtrasMkspecDir.cmake
   把构建期安装前缀的相对推导 `"${_qt5Core_install_prefix}/../b//mkspecs/linux-clang"`
   烘焙进包——`../b` 指向包外的 conan 构建目录（包上传后不存在）。上游 cmake 套件经
   CMAKE_PREFIX_PATH 消费 Qt5Core 时，`_qt5_Core_check_file_exists` 对该 mkspecs 目录
   做存在性校验失败，imported target "Qt5::Core" 创建即死。
2. **CMake >= 4 策略不兼容**：上游 module_includes 模板 `cmake_minimum_required(2.8)`，
   CMake 4.x 移除 < 3.5 兼容，需注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
3. **平台探测路径**：OHOS 工具链下 Qt5 config/mkspecs 探测需按 Linux 平台路径解析，
   需 `CMAKE_SYSTEM_NAME=Linux` 覆盖（与 test_package generate() 双覆盖同款）。

同根因异通道（差异定位，见「关系」节）：mlite 草稿是 qmake 通道（.pri/qt.conf 烘焙路径）；
E750 qtgamepad ③ 是制品包 cmake 消费通道（镜像+推导重写）；kirigami2
DRAFT-E5xx-qt5-conan-split-cmake-bridge 是伞形 find_package 跨包桥接通道（staged-fixed
复制改写）。**本条是「构建树内测试套件消费」通道的最小修复形态**——上一个符号链接解决，
零复制零改写。

## 方案：mkspecs 推导位符号链接 + cmake 三件套

前置：可写 Qt prefix（qt-prefix 模式，qtmultimedia/qtscxml 同款）——symlink 镜像 qtbase
包目录 + 重写 mkspecs .pri 构建路径 + 自写 qt.conf，落在 `<build>/qt-prefix`。

关键洞察：MkspecDir 的 `../b` 相对推导以 prefix 为锚点，而 prefix 与测试套件构建树同层
（都在 `<build>/` 下），于是 `"<prefix>/../b//mkspecs/linux-clang"` **恰好解析进本配方的
build 目录**——在推导位放一个 linux-clang 符号链接接回包内真 mkspecs，校验即通过：

```python
def _fix_mkspecs_dir_link(self, qtbase_pkg):
    link_root = os.path.join(self.build_folder, "b", "mkspecs")
    os.makedirs(link_root, exist_ok=True)
    link_path = os.path.join(link_root, "linux-clang")
    if not os.path.exists(link_path):
        os.symlink(os.path.join(qtbase_pkg, "mkspecs", "linux-clang"), link_path)
```

随后绕开上游 make check 入口，subprocess 直接驱动 cmake+ctest，注入三件套：

- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（环境变量）
- `-DCMAKE_SYSTEM_NAME=Linux` + `-DCMAKE_SYSTEM_PROCESSOR=aarch64`
- `-DCMAKE_PREFIX_PATH=<源树>;<qt_root>` + `-DQt5_MODULE_TEST_DEPENDS=Core` +
  `-DCMAKE_MODULES_UNDER_TEST=TextToSpeech`（module_includes 模板变量，按模块名换）

完整实现：PR !14839 archives/q/qt5-qtspeech/5.15.2/conanfile.py（`_fix_mkspecs_dir_link`
与上游 cmake 套件驱动段）。

## 回退

若可写 prefix 与 build 树不同层（`../b` 推导不落 build 目录、无处建链接）：退化为
staged-fixed——复制 qtbase lib/cmake 树、regex 修掉 MkspecDir 的 `../b/` 段、staged 根
排 CMAKE_PREFIX_PATH 最前（E750 ③ / DRAFT-E5xx-qt5-conan-split-cmake-bridge 同款，
代价 ~0.9MB 复制与改写）；再不济改上游测试 CMakeLists 为逐组件 find_package（侵入源码，
最后手段）。

## 验证（PR !14839）

- 无链接：find_package(Qt5Core) FATAL_ERROR（本地原型实测）
- 加链接+三件套：上游 cmake 套件 `1/1 module_includes Passed, 4.26-4.87s`（conan create
  build() 内 cmake+ctest 真跑）；test_package 12 断言 PASS；本地 CI 同款脚本
  build_and_test.sh（zsh）G0/KC/JC/L0-L5 全 pass，Build Summary 100.0%（1/1）

## 推广价值

对一切 qmake 构建的 Qt5 addon 模块的上游 cmake 测试套件同样有效——qtsvg / qtcharts /
qtscxml / qtmultimedia / qtgamepad / qtserialport 等全系（上游 tests/auto/cmake 均为
同款 module_includes 模板、同一 qtbase 依赖链）。测试形态为「同一根因 + 最小修复位」的
跨库横向复用：每适配一个 Qt5 addon 都会撞到，本条给出无需复制 cmake 树的标准解。

## 关系

- 同根因异通道：`mlite-0.5.5-qtbase-baked-buildpath-qmake`（qmake 通道）、`E750`
  qtgamepad ③（制品包 cmake 消费，镜像+推导重写）、`DRAFT-E5xx-qt5-conan-split-cmake-bridge`
  （伞形 find_package 跨包桥接，staged-fixed）
- 不同问题：E438/E495 是 Qt6 构建配置侧（mkspec 指定/QT_HOST_PATH），非包内残留路径；
  E321 草稿只讲 CMAKE_POLICY_VERSION_MINIMUM 单点（本条含其作为三件套之一并给组合场景）
