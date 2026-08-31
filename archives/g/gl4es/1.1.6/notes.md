# gl4es 1.1.6 适配笔记

## 编译环境
- 构建系统: cmake（无 install() 装头文件；install() 只写死 `/usr/lib/gl4es/`）
- 编译日期: 2026-08-30
- 编译器: clang/clang++
- 状态: built（配方已按仓库模板整理，待官方 CI 做 R26 构建 / R34 验证 / 发布 ohpcd）

## 路径判定

**A 类基础适配（可编出可用包）**。gl4es 把桌面 OpenGL 1.5/2.1 固定管线翻译到
OpenGL ES 2.0（内置 FPE 固定管线模拟器），鸿蒙 PC 只有 EGL+GLES3.2、无桌面 `libGL.so`，
故用 gl4es 产出 `libGL.so`（供 `-lGL` 链接）+ GL 头，让依赖桌面 OpenGL 的
C/C++ 库/游戏能跑。

## 编译步骤

```bash
# 关键 CMake 选项（写入 conanfile.py generate()）：
#   -DCMAKE_SYSTEM_NAME=Linux   # 必须匹配 Linux，src/CMakeLists 才编译 GLX/EGL 后端
#   -DNOX11=ON                 # 鸿蒙无 X11
#   -DNOEGL=OFF                # 用真实 EGL（libEGL.so）
#   -DDEFAULT_ES=2             # GLES2 后端，兼容 GLES3 硬件上下文
#   -DSTATICLIB=OFF            # 共享库（default shared:True）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(2.8.12)` 在 cmake 4.x 报错 | cmake 4.x 移除 <3.5 兼容 | `patches/0001-cmake-minimum-35.patch` 升到 3.5（configure 再传 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兜底） |
| 2 | `CMAKE_SYSTEM_NAME` 未匹配 "Linux" 则**不编 GLX/EGL 后端** | src/CMakeLists 用 `if(${CMAKE_SYSTEM_NAME} MATCHES "Linux")` | 强制 `-DCMAKE_SYSTEM_NAME=Linux` |
| 3 | 无 `install()` 装头文件；`install()` 只写死 `/usr/lib/gl4es/`（绝对路径） | 上游打包不完整 | `package()` 手动复制 `libGL.so*` + 完整 `include/` |
| 4 | 共享库 SUFFIX 是 `.so.1`，无 `libGL.so` 软链 | `set_target_properties(GL PROPERTIES SUFFIX ".so.1")` | `package()` 里 `libGL.so -> libGL.so.1` 软链，供 `-lGL` |
| 5 | codeload tar.gz URL 无扩展名（`/v1.1.6`） | Conan 误判 zip | conandata.yml 加 `filename: gl4es-1.1.6.tar.gz` 让 `get()` 用 untar |

## 源码修改

- `patches/0001-cmake-minimum-35.patch`：`CMakeLists.txt` 的 `cmake_minimum_required` 由 `2.8.12` 升到 `3.5`。

## 依赖版本

- 无额外 conan 依赖（不链系统库以外的东西）。
- 运行时依赖系统库（非 conan）：`/system/lib64/libGLESv3.so`、`/system/lib64/libEGL.so`（OHOS 无 `libGLESv2.so`）。

## 验证结果

```bash
# 本机 conan cache 已有成功构建产物：
#   lib/libGL.so.1 (1.53MB) + lib/libGL.so -> libGL.so.1 软链
#   include/{GL,GLES,EGL,KHR}/*.h + gl4esinit.h / gl4eshint.h
# 本机存在 /system/lib64/libGLESv3.so 与 libEGL.so（test 可真正调用 gl4es）
# 官方 CI 将执行 conan create 完成 R26 构建 + R34 验证（实际产物以 CI 为准）
```

## 本地离屏渲染验证（非 CI，已跑通）

本机（OHOS PC aarch64，HUAWEI Maleoon 916 GPU）用 gl4es 做了一次**真实离屏渲染自检**，
证明桌面固定管线不只是"能链接"，而是"**真的能画出像素**"——这直接对应 A 路径 A2
「主要功能实际工作」的实证（最终以官方 CI 的 R26/R34 为准）。

- **测试程序**：EGL pbuffer GLES2 上下文 + gl4es（`libGL.so`）画一个固定管线三角形
  （`glClear / glMatrixMode / glBegin / glEnd / glColor3f / glVertex3f`）+ `glReadPixels` 读回校验。
- **结果**：`nonblack=512/4096`（**纯黑清屏**下仅三角形区域非黑，具区分度）、中心像素 `(58,66,131)`、
  `glGetError=0x0` → **PASS**，exit 0。（评审指出旧 `4096/4096` 因清屏色非黑而断言空转，已改为纯黑清屏，
  PASS 判定要求中心像素非黑且 `glGetError()==GL_NO_ERROR`。）
- gl4es 启动日志确认：`EGL 1.4`、`Hardware vendor is HUAWEI`、`Targeting OpenGL 2.1`。
- **参考佐证（同链路已跑通）**：`archives/a/assaultcube/1.3.0.2` 的 B1 离屏渲染
  （SDL2 offscreen + gl4es）也已成功出图（`profile/screenshots/ac_run.jpg`）。

**R34 离屏渲染测试由 CI 执行**：`test_package` 为**真实离屏渲染**测试（`test.c` 创建 EGL pbuffer GLES2
上下文 + 固定管线三角形 + `glReadPixels` 校验：PASS 要求中心像素非黑且 `glGetError()==GL_NO_ERROR`）。
`find_library(EGL)` 已通过把 ohos sysroot 的 `usr/lib/aarch64-linux-ohos` 与 `/system/lib64` 加入搜索路径
解决（`CMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake 默认搜不到 libEGL）。**本地 CI 模拟
（`ci/conan/build_and_test.sh`）已通过**：`nonblack=512/4096`、`glGetError=0x0` → PASS，随 `conan create`
由 CI 执行（R34），并作为 A2「主要功能实际工作」的实证。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | gl4es Conan 配方（手动 copy 打包） |
| conandata.yml | 官方源码 URL + sha256 + filename + 补丁 |
| patches/0001-cmake-minimum-35.patch | cmake min 版本补丁 |
| test_package/ | R34 L1 测试（链接 + 调用 gl4es 固定管线 API） |
| manifest.yaml / notes.md / test_package/MANIFEST.yml | 归档/测试声明 |

## 注意事项

- **不要**改 `layout()`：gl4es 把产物写死到 `${CMAKE_SOURCE_DIR}/lib`，无 layout 时 conan 源码内构建最可靠（本机已实测）。
- `package()` 手动复制是必须的：上游 `cmake.install()` 会写到绝对路径 `/usr/lib/gl4es/`（污染系统、忽略 prefix）。
- 消费方运行时需 `LIBGL_GLES=/system/lib64/libGLESv3.so`、`LIBGL_EGL=/system/lib64/libEGL.so`。
