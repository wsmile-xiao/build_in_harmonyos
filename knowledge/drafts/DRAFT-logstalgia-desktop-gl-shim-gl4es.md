# DRAFT：OHOS 无桌面 GL 栈的 shim 自解范式——gl4es 兼容层 + GLU 五函数 Mesa 移植 + GLEW 三符号自写 shim

## 错误特征 / 触发场景

```
场景：上游依赖桌面 OpenGL 固定管线 + GLU + GLEW，目标平台 OHOS PC 只有 EGL + GLESv3（无 X11/无桌面 GL）
表象（三层连锁断裂）：
  checking for GL... no          ← AX_CHECK_GL 找不到 gl.pc（PKG_CHECK_MODULES 失败）
  checking for GLU... no         ← 同上，GL_LIBS=no 传给 conftest 连锁崩
  fatal error: 'GL/glew.h' file not found        ← GLEW 头完全缺失
  undefined reference to `gluProject'            ← gl4es 只带 GLU 声明不带符号实现
  undefined reference to `glewInit'              ← GLEW 库缺失
  glBindBuffer' undeclared       ← gl4es gl.h 只到 GL 1.2 基线，VBO 原型在 glext.h 且需 GL_GLEXT_PROTOTYPES
  Error loading shared library libGL.so.1        ← 运行时找不到翻译层
```

## 根因（机制层）

"运行时翻译层 ≠ 头文件完备 ≠ 实用工具库符号齐"——三个断层的组合：

1. **头文件/链接层**：OHOS 系统无 GL/gl.h、GL/glew.h、GLU/glu.h 与 libGL.so
2. **configure 检测层**：AX_CHECK_GL 走 `PKG_CHECK_MODULES([GL],[gl])` 找不到 gl.pc；AC_SEARCH_LIBS 又无 -L 注入 → 检测失败后 GL_LIBS=no 传给 conftest 连锁崩
3. **符号层**：gl4es 补了 libGL.so 与 GL/gl.h，但只带 GLU **声明**（glu.h）不带 glu* 符号**实现**；GLEW 完全缺失（上游 Core 的 gl.h 会 `#include <GL/glew.h>`，且消费 glewInit/GLEW_VERSION_2_0）

## 解法（四层组合，零上游源码补丁）

1. **gl4es 兼容层打底**（制品仓 gl4es/1.1.6）：libGL.so（桌面 GL 1.5/2.1 → GLES2 运行时翻译，含 FPE 固定管线模拟）+ GL/gl.h + GL/glext.h
2. **GLU 五函数 shim**：先 grep 上游实际用到的 GLU 函数（`grep -rhoE "glu[A-Z][A-Za-z]+\(" src/ | sort -u`），按 Mesa 公开域数学实现移植编 libGLU.a。⚠️ GL 矩阵约定两个实测坑：
   - gluUnProject 的 viewport 逆映射**运算序**（先除后乘，同 Mesa）
   - invert_matrix 输出**补转置**（消元在转置系上运行，inv 实为 (A^-1)^T，列向量乘约定需再转置）
3. **GLEW 三符号 shim**（compat/GL/glew.h）：转 include gl4es 头 + `#define GL_GLEXT_PROTOTYPES 1`（VBO 原型可见）+ GLEW_OK/GLEW_ERROR_NO_GLX_DISPLAY/GLEW_VERSION_2_0（防 ffp 误回退）+ GL_COMPUTE_SHADER=0x91B9（GL 4.3 常量，gl4es 不含但上游引用，运行时不触达）；glewInit/glewGetErrorString/glewExperimental 实现放 libGLU.a（C ABI）
4. **configure 走别名 .pc + 环境覆盖**：PkgConfigDeps 输出目录生成 gl（→gl4es）/glu（→libGLU.a）/glew（→shim 头+libGLU.a）/freetype2（版本号写 libtool 号）别名 .pc；PKG_CONFIG_PATH 注入；`--build/--host=aarch64-linux` 跳过 config.guess

**运行时环境**：LD_LIBRARY_PATH（gl4es lib + /system/lib64）+ `LIBGL_GLES=/system/lib64/libGLESv3.so LIBGL_EGL=/system/lib64/libEGL.so`（gl4es 后端选择）。真机实测（OHOS PC + Maleoon 916 GPU）：`Using GLES 2.0 backend`、`Hardware Full NPOT detected and used`、`Hardware vendor is HUAWEI`——桌面 GL 栈在 OHOS 真实硬件初始化成功。

## 验证

- CI #42999 绿（本地干净 clone 全绿）
- 真机 2026-09-09：`./logstalgia --help` 打印完整帮助 exit 0 + gl4es 日志确认 GLES2 后端加载
- selftest 矩阵数学自测：headless 下 gl4es loader 初始化崩溃 → GL stub 链接跑通（矩阵自测无需真 GL）

## 适用范围（跨库复用）

任何依赖**桌面 GL/GLU/GLEW** 的图形程序（可视化/游戏/模拟器/老旧 OpenGL 代码库）在 OHOS/嵌入式 GLES-only 平台的适配：
- logstalgia / 同类固定管线可视化工具
- 引用 gluProject/gluPerspective 的 CAD/科学可视化工具
- GLEW 消费者（大量桌面 GL 项目的标准引导库）

## 关联与区别

- **#2864 issue**（.gitignore 静默吞 include）：同 PR 的**文件流转**教训（compat/include/GL/glew.h 被 gitignore 吞）——本条聚焦 **GL 栈本身**（shim 技术方案），互补不重叠
- **DRAFT-sdl2-egl-querydevices-fallback**（#7529）：SDL2 的 EGL 设备枚举 fallback——同为 headless/EGL 域但属 SDL2 窗口系统层，非 GL/GLU/GLEW 符号层
- **E443/E445 类 X11/图形栈条目**（如有）：知识图谱 grep "GL|glew|GLU|gl4es" 零命中——空白域

## 红线

- shim 面积由上游实际符号消费决定（grep 实测清单），禁止盲目抄全量 Mesa GLU
- GLU 矩阵数学必须过列主序约定自测（gluProject↔gluUnProject 往返断言）——转置坑是实测翻过车的
- 运行时类测试在无头 CI 用 GL stub 链接，真机才走 gl4es 真路径，两层都要有证据
