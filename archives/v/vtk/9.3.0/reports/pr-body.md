- **三方库名称**：vtk（VTK — The Visualization Toolkit）
- **上游版本**：9.3.0
- **上游仓库地址**：https://github.com/Kitware/VTK
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent；E019、E092、E187、E379；新增 `E429-draft-VTK9` 深度格式适配记录。

新增 VTK 9.3.0 的 HarmonyOS PC 原生构建，提供 C++ 共享库、SDK、CMake 导出和 EGL/GLES 离屏渲染。修复 GLES 着色器、纹理读写、深度/MSAA、数值计算及运行资源查找问题，`conan create` 中运行上游 CTest 和安装包消费者测试。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|---|---:|---|
| 单元/原生类：不带外部数据参数 | 303 | CTest 原生入口中不含 `-D/-V` 的条目 |
| 集成/数据类：带数据或基线参数 | 1408 | CTest 原生入口中包含 `-D/-V` 的条目，含图像回归 |
| 其他测试 | 121 | HeaderTest 头文件检查 |
| **合计** | **1832** | 当前启用产品配置的全部 CTest 注册条目 |

前两类按 CTest 命令是否包含 `-D/-V` 数据参数分组。按入口统计，共有 1708 个 C++ 测试、3 个其他原生测试和 121 个 HeaderTest。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|---|---:|---|---|
| 单元/原生类：不带外部数据参数 | 303 | 不变 | 保留全部入口 |
| 集成/数据类：带数据或基线参数 | 1408 | 不变 | 保留全部入口与图像基线 |
| 其他测试 | 121 | 不变 | HeaderTest |
| 鸿蒙消费者进程测试 | 5 | 新增 5 | 三个正向执行及两个反向控制 |
| **合计** | **1837** | **+5** | 1832 个上游条目及 5 次消费者执行 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **是**，存在两处测试源文件的修改。

1. **`Common/Core/Testing/Cxx/UnitTestMath.cxx`**：plain char 在目标 ABI 为无符号，原有两处断言对同一 [0,255] 范围要求不同结果。使用 `numeric_limits<char>::is_signed` 选择与原搜索顺序一致的预期枚举。
2. **`Filters/Selection/Testing/Cxx/TestLinearSelector3D.cxx`**：四处端点排除参数从 `1e-12` 调整为默认 `1e-6`，适配 float 顶点的相对判定。交点容差 `1e-12` 及输出数量 54/54/108/45 保持原值。

图像基线、图像误差阈值及全部已注册测试保持不变。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有完整测试；另增加制品消费和已定位问题的回归验证。

| 新增文件 | 覆盖 |
|---|---|
| `test_package/src/main.cpp` | 版本、对象与管线、226 点/448 单元；5 个正向断言及一个反向控制 |
| `test_package/src/test_render.cpp` | EGL 实绘、RGB/HDR/16 位读写、2D/3D resize、错误/状态恢复、偏移 MSAA 与 GS 深度；20 个正向断言及一个反向控制 |
| `test_package/src/test_viewports.cpp` | PROJ 资源定位与 EPSG:3978 初始化、新建窗口下 legacy peeling/fluid 偏移视口、六类 sampler 编译、MSAA stencil/color-mask 状态隔离；6 个正向断言 |

三个程序共 31 个正向断言。五次进程执行期望退出码为 0/1/0/1/0；反向控制仅接受退出 1，崩溃和初始化错误均判失败。`CMakeLists.txt`、`conanfile.py` 与共享 `vtk_runtime.py` 负责链接、签名副本、资源布局及当前运行路径。

## 验证结果

- 原生构建：9006/9006 个目标完成，W3 返回 0。
- 上游测试：1830 通过、0 失败、2 跳过、0 未执行，总计 1832，CTest 耗时 178.21 秒。
- 上游通过率：按全部注册条目为 **1830/1832（99.89%）**；按有通过/失败结果的条目为 **1830/1830（100%）**。
- 两项跳过：`TestAVIWriter` 依赖 Video for Windows，`TestMP4Writer` 依赖 Microsoft Media Foundation。两项后端在上游默认关闭且限定 WIN32，测试按上游条件返回跳过码。
- 安装包消费者：5/5 次执行符合期望退出码，31 个正向断言及两个反向控制通过。
- 正常图像验证：64×64 RGB、1020 个非背景像素。
- 详细统计、修改依据及日志 SHA256：`archives/v/vtk/9.3.0/reports/upstream_tests_report.md`。

## 补充说明

源码来自 Kitware/VTK 的 `v9.3.0` tag，SHA256 为 `b4b7323fc24446f0a19813a0c8bdf4fd5b6f796c6f3caf2fb159f65425557a60`。58 个补丁按源文件生成，逐项说明见 conandata.yml、manifest.yaml。

主要修复覆盖 GLSL 版本/类型/精度、几何 shader 输出、点与宽线、纹理/PBO、深度格式及 MSAA/视口语义、RG32F 混合探针、敏感数值计算、HDF/SEG-Y 类型和 musl 头。浮点收缩选项默认开启，OHOS 配方只对 12 个已定位源文件关闭收缩。

目标环境为 HarmonyOS PC aarch64、Clang 15.0.4、CMake 4.1.2、Ninja、EGL 1.4/GLES 3.2、Maleoon 916。启用模块使用上游内嵌依赖，无外部 Conan requires。ExternalData 按上游内容哈希获取并验证。

本配置包含 C++ 库和离屏渲染，Python/Java 绑定、X11 窗口和需外部依赖的可选后端未启用。HeaderTest 不要求 VTK Python 绑定。运行库通过私有目录中的签名副本承载，保留 `prefix/lib` 与同级 `share` 关系；RPATH 及 LD_LIBRARY_PATH 顺序在真机核对。

`E429-draft-VTK9` 记录了 Maleoon 916 上几何着色器显式深度写入的数值差异，以及保持 D32F 格式的修复与验证。

```sh
conan create archives/v/vtk/9.3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

W3 日志 SHA256：`93c6aa1c4d757a8023948c31b99275edeeaf4638686e59827f6c83d60220fa95`。包 revision、JUnit 哈希及完整结果见 `archives/v/vtk/9.3.0/reports/native-validation.json` 和 `reports/test-report.md`。
