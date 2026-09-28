# DRAFT-lightmapper-2.8-gl-link-stub-headless-cpu-test

> 路径 B 草稿（new_draft）— 产生库：lightmapper 2.8（task_id
> lightmapper-2.8-r01-bootstrap-and-adapt-pc2-38-20260927T110937Z）
> 状态：待审核（不得直接 promote；分析端复核后另行处理）

## 问题

GL 引用型单头文件 C/C++ 库（如 lightmapper.h：公共 API 声明引用
GL_UNSIGNED_BYTE/GL_FLOAT 等常量，LIGHTMAPPER_IMPLEMENTATION 实现区直接调用
桌面 GL 函数 glBindVertexArray/glGenFramebuffers/glReadPixels 等）以
header-only 配方打包时，test_package 若定义 LIGHTMAPPER_IMPLEMENTATION 以
链接真实实现，就会因 GL 常量未定义（编译失败）或 GL 函数无实现（链接失败）
而无法在无 GPU/无 GL 开发环境与 OHOS CI 中完成消费者验证。

## 根因

- 单头库按设计假定消费者自带 OpenGL（声明与实现均引用 GL 符号），配方与
  test_package 处于无 GL 环境；
- test_package 必须真实调用被测库 API（R34），但只调 CPU 侧图像后处理 API
  （lmImageMin/Max/Power/Dilate/FtoUB/Add/Scale/SaveTGAub）时，链接器仍要求
  同一编译单元内实现区引用的全部 GL 符号有定义；
- 该需求是**库形态**造成的（GL 引用单头库在无 GL 环境打包验证），非本库特有。

## 方案

test_package 内建 `gl_shim.h` + `gl_shim.c`：

1. `gl_shim.h`：定义 lightmapper.h 用到的全部 GL 常量（GL_UNSIGNED_BYTE、
   GL_TEXTURE_2D、GL_FRAMEBUFFER 等，取值与桌面 GL 一致），并声明实现区引用
   的 ~45 个 GL 函数原型（返回类型按调用点语义）；
2. `gl_shim.c`：为每个 GL 函数提供**链接期 stub**（无操作/返回合理默认值，
   如 glCheckFramebufferStatus→GL_FRAMEBUFFER_COMPLETE、glCreateProgram→0、
   glGen*→写 0）；
3. test.c：先 include gl_shim.h，再 `#define LIGHTMAPPER_IMPLEMENTATION`
   并 include lightmapper.h，然后只调用 CPU 侧 lmImage* API 并断言——
   GL stub 在运行时**不被执行**，仅满足编译/链接；
4. CMakeLists.txt 将 gl_shim.c 与 test.c 一起编译链接，目标链接
   lightmapper::lightmapper。

## 验证

- `python3 scripts/ohc-run.py conan-verify lightmapper 2.8` → G1-G4/L2/L4/L5 全过；
- `finish` W3 build_and_test.sh → conan create 内 test() 运行 test_lightmapper，
  `all 14 checks passed`，exit 0；
- 冒烟（本机 clang 15 直编）同样 14/14 通过；
- TGA 落盘断言验证 lmImageSaveTGAub 真实写文件（非 print-only 空壳）。

## 适用边界

- 适用：GL（或 EGL/Vulkan）符号引用的**单头文件/header-only 库**，消费者自带
  GL，CPU 侧存在可无头验证的纯计算 API；
- 不适用：需要真实 GL 上下文才能验证的库（应走 EGL pbuffer 真机路径，如
  gl4es/E464 MyGUI Dummy 资源注册）；库自身链接系统 GL 库（-lGL）的配方。

## 反例与限制

- 反例：仅打印字符串/只 include 不链接实现（R34 空壳）；把 GL stub 当真实
  渲染结论上报；把无头环境写成本库 GL 路径已适配；
- 限制：GL stub 不验证任何渲染路径正确性；若库无 CPU 侧 API 可测，本方案
  不适用，需 EGL 真机/CI GPU 环境。

## 查重差异

快照（head c611f7d61b422eda200fc49481cf0d404e63f10c）graph+drafts 全库检索：
- E464（MyGUI Dummy 无头）：资源注册/DataStream EOF，非 GL 符号 stub；
- DRAFT-c-turtle（单头打包 include 布局）：根级相对 include 随包分发；
- DRAFT-cute_files（零测试证据）：MANIFEST 申报 + 消费者测试替代；
- E281/E255（资源包 stub_test）：资源完整性验证，非 GL 链接；
均与本候选（GL 引用单头库 test_package 链接期 GL stub 无头 CPU 验证）不同类，
无等价命中。GL 符号链接期 stub 的 header-only 无头验证策略为全库首次沉淀。
