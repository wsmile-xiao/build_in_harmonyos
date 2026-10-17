# E544 — qmake 生成的 include 头文件是转发桩，直接 copy 会被迫打包整个构建树

## 错误特征
两种表现互为因果：

1. Conan 包体积异常膨胀 —— qt5-qtcharts 达 56MB，其中 51MB 是 `src/` 构建树（含 Makefile、`.moc`、`.o` 目标文件）
2. 若在 `package()` 中直接剔除 `src/`，下游 test_package 编译立即失败，报找不到头文件实体

## 触发条件
- 构建系统: qmake（Qt5 子模块）
- 阶段: package
- 影响范围: 所有 qmake 构建的 Qt5 子模块（qtsvg / qtcharts / qtdatavisualization 等）

## 根因分析
qmake 的 syncqt 在 build 目录下生成的 `include/<Module>/*.h` **并非真实头文件，而是转发桩（forwarding header）**：

```c
// include/QtCharts/qchart.h
#include "../../src/charts/qchart.h"

// include/QtCharts/5.15.2/QtCharts/private/qchart_p.h
#include "../../../../../src/charts/qchart_p.h"
```

桩文件用相对路径指回构建树 `src/`，因此"copy include/ + copy src/"能编译，但一旦不打包 `src/`，55 个公开桩 + 162 个私有桩全部指向空路径。

**手工 copy 子目录的打包方式与 qmake 的头文件布局假设根本不兼容。**

## 解决方案

### 推荐方案
不要手工 copy，改用 Qt 自带安装流程落地 syncqt 处理后的真实头文件：

1. `package()` 中执行 `make install INSTALL_ROOT=<tmpdir>` —— Qt 模块的 make install 会把**真实头文件**装到 `QT_INSTALL_HEADERS/<Module>`，而非桩
2. 再把 `<tmpdir>/<qtbase 包前缀路径>/` 下的 `lib/ include/ qml/ mkspecs/ plugins/` 搬迁到 `self.package_folder`
3. 搬迁后按 E543 的 `_BUILD_DIR_PATTERN` 重写 `.pc`/`.prl`/cmake config 中的 prefix 回指本包

真实头文件内部使用 `<QtCharts/...>` 尖括号引用，不依赖相对路径，天然自包含。

### 禁止做法
- ❌ `copy(self, "*", src=os.path.join(build_folder, "include"), ...)` 直接搬桩文件
- ❌ 为了让桩能解析而把 `src/` 构建树打进包
- ❌ 手工逐个改写桩文件的相对路径

## 验证
```bash
P=$(conan cache path "qt5-qtcharts/5.15.2:*" | tail -1)

# 1) 包内无构建树，体积合理（56MB -> 6.0MB）
ls -d $P/src 2>/dev/null && echo "FAIL: src/ 仍在包内"
du -sh $P

# 2) 无残留转发桩引用
grep -rl '\.\./\.\./src' $P/include/ | wc -l   # 期望 0

# 3) 头文件齐全
ls $P/include/QtCharts/*.h | wc -l                          # 期望 55
ls $P/include/QtCharts/5.15.2/QtCharts/private/*.h | wc -l   # 期望 162

# 4) 构建系统集成文件 prefix 正确
grep -m1 prefix $P/lib/pkgconfig/Qt5Charts.pc
ls $P/lib/cmake/Qt5Charts/Qt5ChartsConfig.cmake
```

## 预防
打包 qmake 类项目前，先确认头文件是桩还是实体：

```bash
head -1 <build>/include/<Module>/<lower>.h
```

看到 `#include "../../src/...` 即说明必须走 `make install`，禁止用 `copy(include)` 交付。

## 关联条目
- 相关: E543
- 原则: R36, W2
