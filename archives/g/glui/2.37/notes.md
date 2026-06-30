# glui 2.37 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++
- CMake 版本: 4.1.2
- Make 版本: 4.4.1
- 状态: published

## 编译步骤

1. **init-build**: `ohc-run.py init-build glui 2.37 --url=file:///.../glui-2.37.tar.gz`
2. **source 上下文**: `source .build-context-glui-2.37`
3. **源码修改** (track-edit 追踪):
   - `ohc track-edit add glui 2.37 CMakeLists.txt`
   - `ohc track-edit add glui 2.37 gl-stubs/GL/gl.h`
   - `ohc track-edit add glui 2.37 gl-stubs/GL/glut.h`
4. **cmake 配置**: `mkdir build && cd build && cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`
5. **make 编译**: `make -j1` — 全部 32 个源文件编译成功（仅警告无错误）
6. **make install DESTDIR**: `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录
7. **测试验证**: ctest 无测试 / make check 无目标 / 替代验证（链接测试+符号检查）
8. **package**: `ohc-run.py package glui 2.37` — 生成 glui-2.37-ohos-aarch64.tar.gz (1.1M)
9. **make install**: `make install` — 安装到 $DEFAULT_PREFIX
10. **finish**: `ohc-run.py finish glui 2.37 published` — G0-G4 全 PASS，状态 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 gh-proxy.com 镜像下载 |
| 2 | cmake_minimum_required(2.8) 不兼容 CMake 4.x | 版本过旧 | 升级到 cmake_minimum_required(3.5) |
| 3 | find_package(GLUT REQUIRED) 失败 | OpenHarmony 无 OpenGL/GLUT | 改为 QUIET + 创建 stub 头文件 |
| 4 | GLUquadricObj 未定义 | stub 头文件缺少 GLU 类型 | 在 gl.h 中添加 GLU 类型和函数 |
| 5 | glColor3ubv/glColor3b/glColor3d 未声明 | stub 头文件缺少部分 GL 函数 | 补充缺失的 GL 函数声明 |
| 6 | GLUT_LEFT 未定义 | stub 头文件缺少该常量 | 添加 #define GLUT_LEFT |
| 7 | glGetError 返回 void 导致类型错误 | stub 声明返回类型错误 | 改为返回 GLenum |
| 8 | gluBuild2DMipmaps 未声明 | stub 头文件缺少 GLU 函数 | 添加 gluBuild2DMipmaps 声明 |
| 9 | verify-build G4 失败: manifest 缺少 build_system | 模板字段未填 | 添加 build_system: cmake |
| 10 | finish 阻塞: 知识草稿为空 | E090/E091 草稿未填 | 填写草稿内容并创建 .knowledge-done |
| 11 | manifest patches_applied 为空列表 | 补丁列表未更新 | 填写 3 个补丁文件名 |
| 12 | 缺少软件级 README.md | 未创建 | 创建 archives/g/glui/README.md |

## 源码修改

### 1. CMakeLists.txt (+41/-20)
- cmake_minimum_required 从 2.8 升级到 3.5（兼容 CMake 4.x）
- find_package(GLUT/OpenGL) 改为 QUIET 模式（非 REQUIRED）
- 添加平台检测：GL 不可用时使用 gl-stubs 目录的 stub 头文件
- 条件构建：无 GL 时不编译 examples 和 tools
- 添加 install targets (lib + include)

### 2. gl-stubs/GL/gl.h (+175/-0，新增)
- GL 基本类型定义 (GLenum, GLfloat, GLint, GLubyte, GLuint, GLdouble 等)
- GL 常量定义 (GL_POINTS, GL_LINES, GL_MODELVIEW, GL_COLOR_BUFFER_BIT 等)
- GL 函数声明 (glBegin, glEnd, glVertex*, glColor*, glClear, glViewport 等)
- GLU 类型 (GLUquadricObj) 和函数 (gluNewQuadric, gluSphere, gluBuild2DMipmaps 等)

### 3. gl-stubs/GL/glut.h (+172/-0，新增)
- GLUT 常量定义 (GLUT_RGB, GLUT_DOUBLE, GLUT_LEFT_BUTTON, GLUT_DOWN 等)
- GLUT 光标常量 (GLUT_CURSOR_INHERIT, GLUT_CURSOR_NONE 等)
- GLUT 键盘常量 (GLUT_KEY_F1-F12, GLUT_KEY_LEFT 等)
- GLUT 字体指针类型 (GLUTbitmapChar)
- GLUT 函数声明 (glutInit, glutCreateWindow, glutDisplayFunc, glutMainLoop 等)

## 对话记录

### AI: 初始化编译环境
```
$ python3 $SKILL_ROOT/scripts/ohc-run.py init-build glui 2.37 --url=https://github.com/libglui/glui/archive/refs/tags/2.37.tar.gz
```
GitHub 直连超时，改用 gh-proxy.com 镜像下载源码包 (487,912 bytes)。

### AI: 依赖分析
检查系统 OpenGL/GLUT 库 — 未找到。检查 cmd-pkgs 预编译包 — 1248 个包中无匹配。
决策：创建 stub 头文件实现 headless 编译，仅编译核心库。

### AI: CMakeLists.txt 适配
CMake 4.1.2 不兼容 cmake_minimum_required(2.8) → 升级到 3.5。
find_package(GLUT REQUIRED) → find_package(GLUT QUIET) + 回退 stub。
仅编译核心库源文件，禁用 examples 和 tools。

### AI: stub 头文件创建
迭代式创建 GL/GLUT stub 头文件，根据编译错误逐步补充缺失的类型和函数声明：
- 第1轮: 基本类型 + 核心函数
- 第2轮: GLUquadricObj + gluBuild2DMipmaps
- 第3轮: glColor3ubv/glColor3b/glColor3d
- 第4轮: GLUT_LEFT + glGetError 返回 GLenum

### AI: 编译成功
```
make -j1 → 32 个源文件全部编译成功
libglui.so (379KB) + libglui_static.a (681KB)
```

### AI: 测试验证
- ctest: 无测试用例
- make check: 无 check 目标
- 静态库链接测试: PASS
- 共享库链接测试: 预期失败（需 GL/GLUT 运行时）
- 符号验证: 794 个导出符号

### AI: 打包
```
ohc-run.py package glui 2.37 → glui-2.37-ohos-aarch64.tar.gz (1.1M)
```

### AI: 收尾
```
ohc-run.py finish glui 2.37 published
→ G0 干净构建验证通过
→ G1-G4 全部 PASS
→ 状态: published
```

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- make 4.4.1
- 运行时依赖: OpenGL, GLUT (由用户应用在链接时提供)

## 验证结果

```bash
# Staging install 验证
ls $TEST_PREFIX/$DEFAULT_PREFIX/lib/libglui*
  libglui.so (379328 bytes)
  libglui_static.a (681614 bytes)
ls $TEST_PREFIX/$DEFAULT_PREFIX/include/GL/glui.h
  glui.h (94295 bytes)

# ctest 结果
No tests were found!!! (glui 无自动化测试套件)

# 静态库链接测试
clang++ test.cpp libglui_static.a -o test && ./test → PASS

# 共享库 ELF 验证
file libglui.so → ELF shared object, 64-bit LSB arm64
readelf -d → NEEDED: libc++_shared.so, libc.so
nm -D → 794 个导出符号, 150 个未定义符号 (GL/GLUT)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libglui.so | 379,328 bytes | AArch64 共享库 |
| libglui_static.a | 681,614 bytes | AArch64 静态库 |
| include/GL/glui.h | 94,295 bytes | 公共头文件 |
| glui-2.37-ohos-aarch64.tar.gz | 1.1M | 预编译打包产物 |
| glui-2.37-ohos-aarch64-debug.tar.gz | 159K | 调试符号包 |

## 注意事项

- glui 是 OpenGL/GLUT UI 库，在无显示环境的 OpenHarmony 上只能编译库文件
- stub 头文件仅提供编译所需的类型和函数声明，实际 GL/GLUT 实现在用户应用链接时提供
- examples 和 tools 被禁用，因为它们需要实际链接 GL/GLUT 库
- 源码中的 `last_live_text == ""` 警告是 GLUI 原始代码的 bug（应为赋值 `=`），不影响编译
- 共享库链接需要目标设备有 OpenGL 实现才能解析 GL/GLUT 符号

---

**编译结束**: 2026-06-25 14:46
**最终状态**: published
