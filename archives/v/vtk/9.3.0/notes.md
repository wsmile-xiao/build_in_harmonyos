# VTK 9.3.0 适配笔记

本配方提供 VTK C++ 共享库、SDK、CMake 导出和 EGL/GLES 离屏渲染。原生 W3 构建通过，上游测试为 1830 通过、0 失败、2 项条件跳过；安装包的三个消费者、31 项正向断言及两个反向控制通过。

## 基线与范围

- 上游：Kitware/VTK，tag `v9.3.0`，BSD-3-Clause。
- 配方源码：`https://codeload.github.com/Kitware/VTK/tar.gz/refs/tags/v9.3.0`，是 GitHub 官方 tag 归档入口的重定向目标；下载文件名显式为 `VTK-9.3.0.tar.gz`。
- 源码 SHA256：`b4b7323fc24446f0a19813a0c8bdf4fd5b6f796c6f3caf2fb159f65425557a60`，42,387,253 字节。
- 原生验证仓库基线：`090ac16c6073191805e144d97438bdbf976d7ce1`；提交基线：`71cfb1495df2f9ab9ced380e79eb3d15933298a4`。相关规则、CI 脚本和 profile 的 Git blob 相同；SKILL.md frontmatter 为 v12.19，正文含后续门禁修订。分支 `feat/vtk-9.3.0`。
- 真机：HarmonyOS PC/OHOS aarch64、HiShell、Clang 15.0.4、HNP CMake 4.1.2、Ninja、SDK 26.0.0.18；EGL 1.4、GLES 3.2、Maleoon 916。
- Common、Filters、IO、Rendering 等启用模块及其内嵌 ThirdParty 一起构建；无外部 Conan requires。
- Python/Java 绑定、X11 窗口及需要外部依赖的可选后端未启用。这些配置边界与已启用 C++ 模块的测试分别记录。

## 实际问题与修复

58 个补丁由官方 `refresh-patch --auto` 按源文件生成，逐项名称和哈希见 `manifest.yaml`；Conan 从官方源码实际应用所有补丁。主要改动如下。

| 触发条件 | 根因及处理 | 验证 |
|---|---|---|
| CMake 平台识别、嵌入依赖配置与 EGL 发现 | 原生 OHOS 使用 POSIX 平台分支并保留原生 try_run；设置 CMake 3.5 策略下限；从 profile 编译器查询隐式头库目录 | 真机完整配置和构建 |
| musl、plain-char 类型解释 | Ioss 使用 POSIX unistd.h；HDF 增补 signed-char 映射；SEG-Y 格式 8 显式解释有符号 8 位采样 | 原始 HDF/SEG-Y 测试 |
| GLES shader 编译 | 修正版本行、保留字、数值类型、精度、uniform 依赖初始化与 sampler 声明；按实际上下文支持选择 shader 版本 | 上游渲染、LIC、流体和新增 sampler 编译检查 |
| 几何 shader、点和宽线绘制 | 每次 EmitVertex 前完整赋输出；点大小进入 shader；宽线保持垂直于线方向及深度语义 | 化学分子、图表、拾取与宽线回归 |
| GLES 纹理上传、下载和重分配 | 处理 RGB 浮点渲染格式、归一化 16 位类型、实际物理分配类型、PBO 字节范围及有效读回；保存并恢复关联 GL 状态 | HDR/16 位数据、重复上传、2D/3D resize、错误恢复 |
| 深度读写与 MSAA/偏移视口 | 使用匹配的深度格式与合法 resolve/copy 顺序，修正 RGBA 深度解码步长和视口源/目的坐标 | 体绘制、EDL、深度剥离、窗口 blit、偏移 MSAA 检查 |
| 请求 32 位深度但固定 32 位格式缺失 | 采用可用的 D32F/GL_FLOAT，纹理、renderbuffer 与中间目标保持一致 | 独立 EGL 深度探针及消费者 GS 深度检查 |
| RG32F MAX 混合能力判断 | 区分浮点可渲染与混合能力；缺少扩展声明时以实际双次 MAX 绘制判定并按上下文缓存 | 原始双深度剥离用例及状态回归 |
| aarch64 浮点收缩改变敏感几何判定 | 新增默认开启的通用 CMake 选项；OHOS 配方仅对 12 个已定位源文件关闭浮点收缩 | 原始几何、坐标轴、流线图像与独立数值对照 |
| 测试数据缓存与运行库加载 | 按上游哈希校验 ExternalData；私有目录用原子替换；执行库复制、签名并前置私有运行路径 | 完整 CTest、缓存校验和 Conan 消费者 |

源码修改使用 GLES 构建或能力条件及通用正确性修复；桌面 MSAA 复制保留原有颜色和深度行为。图像基线与图像误差阈值均保留上游值。

## 上游测试入口与数据

`generate()` 同时启用 `VTK_BUILD_TESTING=ON` 与 `BUILD_TESTING=ON`。`build()` 保存原始 CTest JSON 清单、构建全部目标，然后运行完整注册套件并写 JUnit。测试失败直接传递给 Conan。

当前配置注册 1832 项：1708 项 C++ 功能/算法/渲染、3 项其他原生接口、121 项 HeaderTest。HeaderTest 使用 Python 检查头文件，无需启用 VTK Python 绑定。文件清点数、CTest 条目数和断言数不混用。

数据 helper 从生成的完整 VTKData 规则解析上游内容哈希，逐对象校验并使用 Kitware/vtk.org 提供者。真机已证实 CMake 的 NO_REPLACE 重命名失败而 Python 原子替换可行，因此在 CMake 数据目标执行前填充经过校验的对象缓存；数据和上游测试入口保持原样。失败时保留部分清单并报错。

## 上游测试修改

1. `Common/Core/Testing/Cxx/UnitTestMath.cxx`：plain char 在目标 ABI 为无符号，原先相同的 [0,255] 输入被两处断言要求返回不同枚举。按 `numeric_limits<char>::is_signed` 选择与既有搜索顺序一致的期望。
2. `Filters/Selection/Testing/Cxx/TestLinearSelector3D.cxx`：四处顶点排除参数从 `1e-12` 调整为该功能默认的 `1e-6`，适配 float 顶点和相对端点判定。交点容差仍为 `1e-12`，期望输出数量 54/54/108/45 保持原值。

## 制品消费者

| 程序 | 正向断言 | 检查内容 |
|---|---:|---|
| `test_vtk` | 5 | 精确版本、对象/管线、226 点、448 单元 |
| `test_vtk_render` | 20 | EGL 实绘与 RGB 读回、纹理数值、resize/refill、错误与状态恢复、偏移 MSAA 和 GS 深度 |
| `test_vtk_viewports` | 6 | PROJ 数据库定位与 EPSG:3978 初始化、新建窗口下 legacy peeling/fluid 偏移视口、六类 sampler 声明、MSAA stencil/color-mask 隔离 |
| 合计 | 31 | 三个程序 |

前两个程序另各运行一次 `--expect-fail`，必须恰好退出 1；正常路径要求 0，初始化错误、崩溃等其他退出码均使测试失败。共 5 次进程调用、31 个正向断言、2 个反向控制。核心渲染得到 64×64 RGB 图像及 1020 个非背景像素。

主配方通过 `exports_sources` 携带与消费者同一份 `vtk_runtime.py`。私有库副本经校验和签名；动态路径通过 CMake cache_variables 更新；运行环境在保留 Conan 依赖环境的同时前置私有目录。实测 LD_LIBRARY_PATH 的顺序有效：包缓存优先退出 127，私有目录优先退出 0。

私有运行目录使用 `prefix/lib`，校验并复制同级 `share`，从而保留库的相对资源查找关系。构建树包含 `Testing/Temporary` 时只创建相应空目录，不复制旧测试结果。新增消费者实际读取 PROJ 数据库头并初始化投影。

## 实测结果与适用边界

完整第五轮（phase24）1830 通过、0 失败、2 跳过、0 未执行，CTest exit 0，381.59 秒；JUnit SHA256 为 `0e4434ec4a3fdbd26f4cae8a20bcf848890528ab1aa5d6c1c34e410814da29a3`。两项跳过为上游 AVIWriter、MP4Writer 未启用后端的条件结果。按总分母计算通过率为 99.89%；排除这两项条件跳过后为 100%。

phase29 的受影响 36 项回归全部通过。最终配方首次重建完成 9006 个目标后为 1828 通过、2 失败、2 跳过，两个失败定位到私有运行库目录缺失资源布局。修复布局后，完整 phase32 为 1830 通过、0 失败、2 跳过，安装包消费者的 31 项正向断言及两个反向控制通过。官方 W3 全新构建及安装包消费者也已通过；旧版四补丁 W3 单独作为历史证据。详细结果见 `reports/upstream_tests_report.md`。

## 知识与提交

复用 E019、E092、E187、E379 的平台、加载、构建与数据经验。新增 `knowledge/drafts/E429-draft-VTK9.kv` 及配套说明，记录已复现的 GS 深度写入问题及格式保持方案，范围限定于已测设备/驱动；这是待审草稿，不表示取得 B/C 专项认可。

独立 W4 审计通过，P0/P1 为零，报告见 `reports/audit-result.json`。

## 最终状态

本地构建、测试与 W3：COMPLETED。状态: built。

### 对话 #1 — 最终验证

2026-09-08 完成全新源码构建、完整 CTest 和安装包测试，结果如下。

## 最终 W3 实测结果

官方 finish 的全新源码构建和制品消费者已通过，退出 0。完整上游 CTest 为
1830 通过、0 失败、2 跳过、0 未执行，分母 1832；JUnit 耗时 178 秒。
三个消费者执行五次，31 项正向断言及两个反向控制通过，预期进程退出码为 0/1/0/1/0。

- 实际 W3 包：`vtk/9.3.0#58fb5a42258706b5ca3573d97ad883ef:5b7b8277201cc2f49e0dda85113c3ab9cc47f49e#c15b1b9167a022395fbf0969a5b4b3c3`。
- W3 日志 SHA256：`93c6aa1c4d757a8023948c31b99275edeeaf4638686e59827f6c83d60220fa95`。
- JUnit SHA256：`23f8a8623db246f71c166b786201148e710ec73643579ed1189d34ecdf3994d1`。
- 原始回传归档 SHA256：`acdab5a87ddf3ba8a45ca9e0b50a0f08777e9d1dd3b26dd1ed9a7d941ba7203a`。
- 机器记录：`native-validation.json`；完整原始归档在任务交付目录 `upstream/recipe-validation32/`。

两项跳过为上游 Windows 专用 AVIWriter/MP4Writer 条件，保留在总分母。
全部条目通过率 99.89%，有通过/失败结果条目的通过率 100%；五次消费者执行均符合预期。
此前 export-pkg 缓存准备与其前置完整套件在机器记录中单列，不充当全新构建。

原始 finish 总退出码为 1：W3 成功后，就绪检查发现报告/打包/暂存标记缺项，
The unchanged E219/E253/E305 entries contain multiline YAML values; the existing checker incorrectly reports them as empty. Their baseline Git blobs are unchanged. The original finish exit 1 is retained; missing task deliverables are completed and checked separately.
