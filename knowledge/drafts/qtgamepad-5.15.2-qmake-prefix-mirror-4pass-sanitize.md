# qtgamepad-5.15.2-qmake-prefix-mirror-4pass-sanitize（拟 E750）

## 症状

qmake 构建的 Qt5 addon 模块（本例 qt5-qtgamepad 5.15.2，依赖制品仓 qt5-qtbase/5.15.2.2）
在 OHOS aarch64 交叉构建时，链接行被注入指向早已消亡的 qtbase 构建目录的绝对路径：

```
ld: cannot find /home/.../.conan2/p/b/qt5f140ab856c797/b/lib/libQt5Core.so
# 或：子 Makefile 的 LIBS 行携带 /…/.conan2/p/b/qt5…/b/lib（构建期绝对路径）
```

三个顽固特征（12 轮构建迭代实锤）：

1. **清洗后复发**：即便配方在 qmake 前清洗过元数据，`make` 递归到子目录时由
   QMAKE 规则再次调用 qmake 重新生成子 Makefile，重新读取未清洗元数据，把死亡
   路径重新注入链接行——单点清洗必然复发；
2. **只读不可改**：陈旧路径全部烘焙在共享 conan 缓存里的 qtbase 制品包中，缓存包
   只读，任何修复必须在私有副本上进行；
3. **多形态分布**：同一类陈旧前缀散布在 `.prl`/`.la`/`.pc`/`mkspecs/modules*/qt_lib_*.pri`
   /`lib/cmake/Qt5*/*ConfigExtrasMkspecDir.cmake` 多种文件、两种后缀形态
   （`/b` 严格后缀与 `/p` 宽松后缀，`.la` 的 libdir 行用 `/p/lib`）。

## 根因

qtbase 制品包的四层交叉陈旧路径烘焙 + qmake 的两个机制特性：

| 层 | 烘焙位置 | 陈旧内容 | 触发机制 |
|----|----------|----------|----------|
| ① | `lib/*.prl`、`*.la`（符号链接回共享包） | 原构建树 libdir（`/…/conan2/p/b/qt5…/b`） | qmake **link_prl**：从 module .pri 声明的 libdir 顺藤读 `.prl`，原样注入链接行 |
| ② | `mkspecs/modules*/qt_lib_*.pri` | QT.module-libs/libdir 指向包目录 | link_prl 顺着 .pri 指向读**包内未清洗** `.prl` |
| ③ | `lib/cmake/Qt5*/Qt5*ConfigExtrasMkspecDir.cmake` | `${_qt5Core_install_prefix}/../b//mkspecs/…` 推导（仅对 qtbase 原构建布局有效） | cmake 消费者 find_package(Qt5) 拿到错误 mkspecs 路径 |
| ④ | `bin/qmake`（镜像内是符号链接） | qmake 经 `/proc/self/exe` 解析自身前缀 | 符号链接解析回共享缓存包，镜像前缀失效 |

致命时序：`make -C src/...` 递归 → QMAKE 规则再跑 qmake → 生成新子 Makefile →
重新读 ①② 未清洗元数据 → 陈旧路径回到链接行——**这就是"清洗过还是坏"的机理**。

## 方案：私有可写 Qt prefix 镜像 + 四重清洗

### 第 0 层：镜像骨架

`_build_qt_tree()`：`build_folder/qt-prefix/` 下，除 `bin`/`mkspecs`/`lib` 外全部
条目符号链接到 qtbase 包；`mkspecs` 整树 copy（symlinks=True，后续可改写）；
`bin`/`lib` 单独构建（见下）。

### ① 镜像内 .prl/.la/.pc 物化清洗（双后缀正则）

镜像 `lib/` 下的 `.prl`/`.la`/`.pc` 多为指向共享缓存包的符号链接——**先物化为
私有副本再清洗**（递归 qmake 生成子 Makefile 时会读，如 evdev 插件链接行）。
正则必须双形态，缺一不可：

```python
# 严格 /b 后缀（.prl 主体）
_BUILD_DIR_PATTERN = re.compile(
    r"(/[^\s\"]*/(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+/b)")
# 宽松 /p 后缀（.la libdir 行用 /p/lib，严格正则够不到；E543 .cache 形态同覆盖）
_PKG_DIR_PATTERN = re.compile(
    r"(/[^\s\"']*/(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+/p)(?=[/'\"]|$)")
```

替换目标：qtbase 制品包 `package_folder`（活路径）。**豁免当前构建目录自己的
qt-prefix 前缀**（`root == CUR` 直接返回）——镜像 `bin/qmake` 符号链接是活的、
被递归 sub-make 的 QMAKE 规则使用，绝不能重写。

### ② module .pri 重定向镜像 lib（携带清洗副本）

`_prepare_mkspecs()`：`mkspecs/modules` 与 `modules-inst` 下 `qt_lib_*.pri` 的库
路径重定向到**镜像 lib/**（其中已放 ① 的清洗副本）——否则 link_prl 会顺着 .pri
指向读**包内未清洗** `.prl`，"清洗后再注入"复发链不断。

### ③ cmake 树物化 + MkspecDir 推导重写

`lib/cmake/Qt5*/Qt5*ConfigExtrasMkspecDir.cmake` 中
`${_qt5Core_install_prefix}/../b//mkspecs/linux-clang` 重写为
`${_qt5Core_install_prefix}/mkspecs/linux-clang`（镜像布局 mkspecs 直接在安装
前缀下）。

### ④ qmake 实体物化 + 生成期清洗 wrapper

镜像 `bin/qmake` 物化为 `qmake.real` + Python wrapper：

- **实体文件**让 `/proc/self/exe` 解析进镜像（符号链接会解析回共享包）；
- wrapper 在**每次 qmake 生成 Makefile 后就地清洗**（PAT_B/PAT_P 双正则），
  兜住 make 递归期间的每一次再生成——这是根治"复发"的关键一层。

```python
# wrapper 骨架：先透传执行，再清洗本次生成的 Makefile，最后透传退出码
rc = subprocess.call([REAL] + sys.argv[1:])
for name in os.listdir("."):
    if name != "Makefile" and not name.startswith("Makefile."):
        continue
    ... fixed = PAT_P.sub(_sub, PAT_B.sub(_sub, content)) ...
sys.exit(rc)
```

### 配套（非清洗但同链必需）

- `QMAKE_STRIP=""`：OHOS loader 拒收被 strip 的 ELF（strip --strip-unneeded 破坏
  动态符号表）；`make install` 用 `STRIP=true`。
- 打包后重写本包 `.prl/.la/.pc` 残留 build-dir/source-dir 为 `package_folder`
  （消费者不再二次踩坑）。

## 回退

- 最低限度：①+④（物化清洗 .prl/.la + wrapper 生成期兜底）可救链接行，但
  cmake 消费者缺 ③ 会拿到错误 mkspecs 推导；
- 终极兜底：放弃镜像、完整源码重编 qtbase（构建时长与产物体积膨胀一个量级，
  失去 addon 模块复用制品的意义）。

## 验证（PR #14870）

- 本机 `conan create -pr:h=ohos-aarch64 --build=missing` 干净重跑 **RC=0**；
- 上游 ctest `tests/auto/cmake`（module_includes）**1/1 PASS**
  （"100% tests passed, 0 tests failed out of 1"；CMAKE_POLICY_VERSION_MINIMUM=3.5
  兼容 cmake_minimum_required(2.8)）；
- 消费者 test_package **58/58 断言 PASS**（QGamepadManager/QGamepad/
  QGamepadKeyNavigation + evdev 插件 QPluginLoader 真实 dlopen+IID/Keys 契约）。

## 推广价值

- 一切 qmake 构建的 Qt5 addon 模块：qtsvg / qtwebsockets / qtcharts /
  qtgamepad / qtdatavisualization / …（先例 qtsvg/qtwebsockets 单点用法、
  E543/E544 单点子问题，本条给出系统性根治链）；
- 更一般地：任何"**制品包元数据烘焙构建期绝对路径 + 构建工具递归再生成**"的
  组合（不限 Qt）——四层法（物化清洗 / 入口重定向 / 推导重写 / 实体物化断链+
  生成期兜底）是同一模式的通用解。

## 关系

- similar_to: E543（.pri 路径重写正则形态——本条②的单点子问题）、
  E544（syncqt 转发桩 make-install-root——qt5 addon 打包配套）
- reference: PR #14870 `archives/q/qt5-qtgamepad/5.15.2/conanfile.py`
