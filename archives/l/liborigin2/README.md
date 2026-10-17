# liborigin2

> 读取 OriginLab Origin 4.1 – 8.5.1 工程文件（`.opj`）的 C++ 库

## 简介

liborigin2 由 QtiPlot 项目维护，用 C++ 解析 OriginLab Origin 的科学绘图工程文件，
提供电子表格、矩阵、函数、图形、笔记与工程树等数据结构的读取接口。SciDAVis 等
数据分析软件以此作为 Origin 文件导入后端。

本包为共享库（默认 `shared=True`，也支持静态构建），不产出命令行工具。

## 上游溯源（重要）

上游原始分发渠道已全部失效：作者主页 `soft.proindependent.com/liborigin2/` 已下线
（Debian 只能用 Wayback 快照做 Homepage），下载托管 `berlios.de` 已关闭，
`sourceforge.net/projects/liborigin2/` 返回 404。当前维护中的同名后继项目是
SourceForge 上的 **liborigin 3.0.x**，但它并没有 20110117 这个版本。

因此本包的源码取自 **Debian 源码池的 orig tarball**：
`liborigin2_20110117.orig.tar.gz`，其 sha256 与 `liborigin2_20110117-7.dsc` 中的
`Checksums-Sha256` 一致，是当前唯一可复现、可校验的 20110117 来源。

## OHOS 适配要点

- **不用 qmake**：上游只带 qmake 工程 `liborigin2.pro`，但本库**完全不依赖 Qt**
  （`.pro` 里 `QT -= gui core`，源码零 Qt 引用），qmake 只是构建工具。HarmonyOS
  上没有 Qt5 base/qmake，为构建一个小库而引入整套 Qt 构建依赖不划算，配方因此
  注入 `files/CMakeLists.txt`——源文件清单与 `.pro` 的 `SOURCES` 完全一致，
  不改变任何上游编译语义。
- **tree.hh 是缺失依赖**：上游 20110117 tarball 里没有 `tree.hh`，而
  `OriginParser.h` 直接 `#include "tree.hh"`，原样无法编译。本包用仓库已有的
  Conan 包 `tree-hh/3.18` 提供，不把第三方头文件 vendoring 进本仓库。
- **boost 只要头文件**：`lexical_cast` / `format` / `date_time` / `tuple` /
  `shared_ptr` / `lambda` / `bind` / `variant`。链接后 NEEDED 里没有 boost
  （实测，且 Debian 的 `--as-needed` 也是同样结论）。
  版本**必须 ≥ 1.90**：`boost/core/detail/sp_thread_sleep.hpp` 自 1.90 起带
  `!defined(__OHOS__)` 守卫，可跳过 OHOS musl 不提供的 `pthread_setcancelstate`。
- **6 个最小源码补丁**（见 `patches/`）：`auto_ptr` → `shared_ptr`、`logging.hpp`
  的流对象比较改为指针比较、补 `<algorithm>`、`boost::posix_time::seconds`
  整型化、运算符优先级 `h & 0x60 == 0x60`、移除 `register` 存储类。
  其中 `register` 一条是 clang 特有：gcc 只告警，clang 15 下是硬错误。
- **产物签名**：OHOS 上共享库必须带平台自签段，`package()` 会先剥离旧
  `.codesign` 再自签，否则 XPM 拒绝加载。

## 排除与替代

- 上游没有 `tests/`、`examples/`，也没有任何 `int main` 或 CTest 注册——
  **上游测试数为 0**（详见 `20110117/test_package/MANIFEST.yml` 中的核验命令），
  本包不做上游测试通过率声明，运行期验证全部来自消费者测试。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.90.0.4.1 | 仅头文件使用；≥1.90 是 OHOS 上的硬约束 |
| tree-hh | 3.18 | 提供上游缺失的 `tree.hh` |

### 消费者需要显式声明这两个依赖

liborigin2 的**公共头**直接 include 第三方头（`OriginObj.h` → `boost/variant.hpp`
等，`OriginParser.h` → `tree.hh`），消费者编译自己的代码时必须能解析它们。
本仓库环境实测：当 boost 只是 liborigin2 的传递依赖时，Conan 生成的
`Boost-config` 不带 include 路径，消费者需要**自己**声明：

```python
# 消费者 conanfile.py
def requirements(self):
    self.requires("liborigin2/20110117")
    self.requires("boost/1.90.0.4.1")   # 公共头需要
    self.requires("tree-hh/3.18")        # 公共头需要
```

```cmake
find_package(liborigin2 REQUIRED CONFIG)
find_package(Boost REQUIRED CONFIG)
find_package(tree-hh REQUIRED CONFIG)
target_link_libraries(app PRIVATE
    liborigin2::liborigin2 Boost::headers tree-hh::tree-hh)
```

`test_package/` 就是按这个用法写的，可直接作为消费示例。

## 功能验证

```cpp
#include "OriginFile.h"   // 公共头安装在 include/liborigin2/

OriginFile f("sample.opj");       // 读取文件偏移 0x7 的 4 字节版本号
double v = f.version();           // 如 8.1
f.parse();
f.spreadCount();                  // 电子表格数
f.project();                      // 工程树（tree<Origin::ProjectNode>*）
```

注意：`OriginFile` 的构造函数会在**当前工作目录**创建 `opjfile.log`（上游行为，
来自内置的 logging sink）。

## 参考

- [SourceForge 项目（后继 liborigin 3.x）](https://sourceforge.net/projects/liborigin/)
- [Debian 包页 liborigin2](https://packages.debian.org/source/sid/liborigin2)
