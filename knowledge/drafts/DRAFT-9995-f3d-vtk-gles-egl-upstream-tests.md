# DRAFT-9995: VTK/GLES 消费者上游测试真跑链（gl31.h + timer query + SONAME + 重签）

## 背景

f3d 3.5.0（PR #9995，rule4/rule5 修复）依赖本地构建的 VTK 9.4.1（GLES3/EGL 配置）。
上游 1018 个测试用例在 OHOS PC 设备上从 0 执行到 523/630（83%）真实通过，
过程中剥了四层平台洋葱。

## 四层问题与修法

### 1. vtk_glad.h GLES3 模式的 API 缺口（编译期）

VTK 以 `VTK_OPENGL_USE_GLES=ON` 构建后，`vtk_glad.h` 在 GLES3 模式只
`#include <GLES3/gl3.h>`。GLES 3.1 才引入的 compute shader API
（`glDispatchCompute`/`glMemoryBarrier`/`GL_SHADER_STORAGE_BARRIER_BIT`）
声明在 `gl31.h`；桌面 GL 的 timer query（`GL_TIME_ELAPSED`/`glGetQueryObjectiv`）
GLES 只有 EXT 扩展版（`gl2ext.h` 的 `GL_EXT_disjoint_timer_query` 块）。

```cpp
// 在 #include <vtk_glad.h> 之后：
#if defined(GL_ES_VERSION_3_0)
#include <GLES3/gl31.h>          // compute shaders
#define GL_GLEXT_PROTOTYPES 1
#include <GLES2/gl2ext.h>        // EXT timer query prototypes
#define GL_TIME_ELAPSED GL_TIME_ELAPSED_EXT
#define glGetQueryObjectiv glGetQueryObjectivEXT
#endif
```

### 2. 相对 DT_NEEDED 与 ctest 工作目录（链接期）

无显式 SONAME 的共享库被 OHOS lld 记录为相对路径
（`../lib/libf3d.so`），只在 bin/ CWD 下可解析；ctest 从 CMake
binary dir 运行测试 → 全量 `Error loading shared library ../lib/...`。

```cmake
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  set_target_properties(libf3d PROPERTIES LINK_FLAGS "-Wl,-soname,libf3d.so")
endif()
```
配合 ctest 的 `LD_LIBRARY_PATH` 前置构建 lib 目录。
（同根因条目：E207）

### 3. .codesign 影子数据随 copy 丢失（运行期）

OHOS 加载器 dlopen 要求有效 `.codesign` 段。HMDFS 把签名存为
sidecar 数据——**cp/dd/patchelf 均不保留**。conan 把构建树 so copy
进包缓存后，所有依赖 so dlopen 一律 `Permission denied`。

诊断手法：`readelf -SW <so>` 看 `.codesign` 段是否还在；同文件在
不同目录/副本上的 dlopen 行为差异即为此因。

```bash
/data/service/hnp/bin/binary-sign-tool sign -selfSign 1 \
  -inFile libX.so -outFile libX.so.signed && mv libX.so.signed libX.so
```
（配方内对全部依赖 so 批量重签后再跑 ctest；153 个库约 2 分钟。）

### 4. EGL probe 门控（CI 兼容）

CI 无头 Worker 无 GPU：配方内嵌 EGL/GLES3 能力探测（编译+运行小
probe），失败则跳过上游测试并记录原因，保持 CI 可绿。

## 效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| ctest 可执行 | 0（加载链断） | 630 |
| 通过 | 0/1018 | **523/630（83%）** |
| 剩余失败 | — | 81 截图差异（GLES vs 桌面 GL 像素差）、8 HMDFS NAME_MAX、4 EGL 深度纹理 segfault、14 同类断言 |

## 适用面

- 任何 VTK+GLES 消费者（ParaView 插件、其他 f3d 系工具）
- 任何需要在 OHOS 设备真跑上游测试的图形库 PR
- E207/E077/E083/E318 的组合场景（本次是四者的联合实战）

## 关联

- PR #9995（f3d 3.5.0）
- 相关条目：E207（SONAME）、E077（重签）、E083（selfSign）、E318（go test 签名链）
