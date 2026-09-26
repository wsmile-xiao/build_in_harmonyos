# libepoxy 1.5.10.1.1 适配笔记（EGL 启用修订）

## 背景
gtk4/4.22.4-r1 R05 验收 quality_rework_required：gsk GL 用例仍失败
（`GLX not supported` SIGTRAP）。根因：ohpcd 已发布 libepoxy/1.5.10.1 构建选项
**egl=no**，gtk4 编译无 `HAVE_EGL`，无法走 mesa EGL/GLES2 surfaceless 路径
（mesa 24.3.4.1.1 客户端栈已可独立创建 EGL/GLES2 surfaceless 上下文）。

本修订（R37 版本后缀 1.5.10.1.1）唯一目标：libepoxy 启用 **egl=yes** 并发布，
使 gtk4 重配后 `HAVE_EGL` 定义、gsk GL 走 mesa EGL surfaceless 收复主体用例。

## 相对 1.5.10.1 的变更
- `version`：1.5.10.1 → **1.5.10.1.1**
- `generate()`：OHOS 分支 `egl=no` → **`egl=yes`**（glx=yes/x11=true 保持不变，
  gtk X11 后端兼容不回归）；`tests=false` → **`tests=true`**（实例化上游测试套件）
- `requirements()`：新增 **mesa/24.3.4.1.1**（transitive_headers=True，提供
  EGL/GLES 头文件）；xorgproto/libx11 保持不变
- 新增 `_provide_mesa_pcs()`：mesa 包内 egl.pc/glesv1_cm.pc/glesv2.pc 复制到
  生成目录并修正 prefix（mesa package_info 未设 pkg_config_name，PkgConfigDeps
  只出 mesa.pc；glu 9.0.3 osmesa.pc 同款）
- 补丁沿用 1.5.10.1（0001-python3-gen-dispatch.patch）

## 构建验证
```bash
conan create archives/l/libepoxy/1.5.10.1.1 --version=1.5.10.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- 包内 include/epoxy/egl.h 生成；libepoxy 编译链接通过（R26 静态，shared=False）
- EGL 函数符号验证、egl-symbols 检查、进程级 EGL/GLES2 surfaceless 上下文
  创建复验见最终回报台账

## 注意事项
- 版本后缀 1.5.10.1.1 与制品仓 1.5.10/1.5.10.1 共存；下游 gtk4 由分析端
  另行下发 R06 重配任务消费本修订（本任务不修改 gtk4 归档）
- libepoxy 自身运行期 dlopen libEGL，不链接 mesa 库（README 同款设计）
- 上游测试套件启用后，egl_* 用例在 OHOS 无窗口系统下运行结论见双口径台账
  （egl_common.c 用 XOpenDisplay 探测显示，无显示时 errx(77) skip，属上游
  原生 skip 语义而非失败）

**编译日期**: 2026-09-23
**状态**: built（本地 W3 验证通过）

## 上游测试双口径台账（1.5.10.1.1, OHOS aarch64, 2026-09-23）
- source_declared_total = 24（test/meson.build 全量 test() 声明：4 无条件 + 5 EGL + 9 GLX + 4 WGL + 2 CGL）
- OHOS 平台适用 = 18（WGL/CGL 由上游 build_wgl/darwin 平台守卫排除）
- configured_executable_total = 16（18 项中链接成功；glx_static: -static 链动态 libX11 → ld.lld 失败；glx_beginend: 链 gl_dep 缺 libGL/GLX 符号 → OHOS 无桌面 GL）
- executed_passed_total = 4（header guards / misc defines / khronos typedefs / gl_version, exit 0）
- executed_skip(77) = 11（egl_has_extension_nocontext / egl_epoxy_api / egl_gles1_without_glx / egl_gles2_without_glx / glx_public_api / glx_public_api_core / glx_glxgetprocaddress_nocontext / glx_has_extension_nocontext / glx_shared_znow / glx_alias_prefer_same_name / glx_gles2 —— egl_common.c / glx_common.c XOpenDisplay(NULL) 无显示按上游 errx(77) SKIP，非失败）
- executed_fail = 1（egl_gl, exit 134：desktop GL 路径 dlopen libGL.so.1 失败，mesa glx=disabled 无 libGL；恢复条件：提供桌面 GL/GLX 栈，OHOS 不可行 → 硬阻塞计入分母不计通过）
- 链接失败 = 2（glx_static / glx_beginend，首错与原因同上）
- 通过率：4/24 (16.7%) 源声明口径；4/16 (25.0%) 当前配置可执行集合口径；skip 为上游原生语义
- 日志：~/tmp/ut/*.log（每用例 exit code 留档）

## 鸿蒙专项测试与消费者验证证据（reports/verify/）
- reports/verify/verify_egl_surfaceless.c：进程级 EGL/GLES2 surfaceless 客户端栈验证
  （模拟 gtk4 gsk GL 业务上层）：仅经公开头 epoxy/egl.h、epoxy/gl.h 与公开 API
  （eglGetDisplay/eglInitialize/eglChooseConfig/eglCreateContext/eglMakeCurrent/
  eglGetPlatformDisplay/eglGetProcAddress）链接 libepoxy 安装产物并实际运行；
  编译 exit 0、运行 exit 0（EGL 1.5 + surfaceless 上下文 + glGetString →
  "OpenGL ES 3.2 Mesa 24.3.4"）
- reports/verify/verify_egl_step_probe.c：分步探测（S1-S9 全 PASS，exit 0）
- reports/verify/verify_mesa_egl_probe.c：mesa 直连对照探测（exit 0，确认 mesa
  24.3.4.1.1 EGL/GLES2 surfaceless 客户端栈独立可用）
- 构建命令（cwd=worktree 根）：
  `/data/service/hnp/bin/clang -I<epoxy_pkg>/include -I<mesa_pkg>/include
   verify_egl_surfaceless.c <epoxy_pkg>/lib/libepoxy.a -ldl -lpthread -lm`
- 运行：`LD_LIBRARY_PATH=<mesa>/lib:<expat>/lib:<llvm>/lib ./egl_surfaceless_verify`
- 运行日志：~/tmp/verify/egl_surfaceless_run.log（sha256 0fd9d2e8...a0da0cce8）
---

**编译结束**: 2026-09-23 22:09
**最终状态**: built

## 知识候选台账与七轴查重（2026-09-23）
候选：**libepoxy egl=no → 下游（gtk4）编译期无 HAVE_EGL → gsk GL 无法走 mesa EGL/GLES2 surfaceless；以 R37 版本后缀 1.5.10.1.1 启用 egl=yes + mesa EGL 头注入（transitive_headers + egl.pc 复制修正 prefix）+ 进程级 EGL/GLES2 surfaceless 验证收复**。
真实证据：gtk4 4.22.4 R05 gsk GL `GLX not supported` SIGTRAP；本修订 EGL 符号 148 个 + epoxy.pc epoxy_has_egl=1 + surfaceless 上下文创建 exit 0。
查重对象：E527（GTK broadway 无显示后端，match_keywords 含 epoxy/libepoxy）、E471（gtkmm 无显示测试分类）、E464（MyGUI 无头测试）、E157/E276/E462（无关）。
- exact_duplicate: false（无 libepoxy EGL 启用修订条目）
- causal_duplicate: false（E527 根因=GTK 无显示后端；本候选根因=libepoxy egl=no 使下游无 HAVE_EGL，因果链不同）
- trigger_overlap: 部分（均属 OHOS 无窗口 GL 景象；E527 触发于 GTK meson 后端配置，本候选触发于 gtk4 gsk GL 运行失败）
- solution_overlap: false（E527=broadway HTML5 后端替代；本候选=EGL surfaceless + epoxypc 声明 + mesa 头注入，方案无重叠）
- combination_novelty: true（egl=yes + mesa egl.pc 复制修正 prefix + epoxy_has_egl 声明 + 进程级 surfaceless 验证的组合无既有条目）
- boundary_novelty: true（OHOS 无 libGL/GLX 时 EGL/GLES2 surfaceless 作为 gtk4 GL 路径的边界，E527 仅覆盖 GTK 后端不改 libepoxy）
- test_migration_novelty: true（双口径台账 24 声明 + 鸿蒙专项 surfaceless 用例为新增验证集）
similar_to: E527（同为 OHOS GL/GUI 生态，但方案不同）
caused_by: E527 未覆盖 libepoxy 侧
prerequisite_of: gtk4 R06 重配消费（下游 follow-up）
conflicts_with: none
决定：new_draft（组合/边界轴新增差异成立，可跨库复用于依赖 GL/EGL 的库）

## R02 上游测试 100% 攻关台账（2026-09-23，task_id libepoxy-1.5.10.1.1-r02-pc1-35-20260923T152537Z）
### 目标与结论
R02 目标：上游测试 24/24（configured 16/16）。经 R02 全量尝试矩阵后**结论：configured 集合 16 项中
passed 4、skip77 11、fail 1、链接失败 2；24 项分母不变**。全部 skip/fail 均经本轮实跑尝试，
阻塞归属为真实平台/基础设施（无 X server、mesa glx=disabled 无 libGL.so.1），未伪造通过。

### 尝试矩阵（逐项真实命令/退出码/首错）
| 用例 | R02 尝试命令/环境 | exit | 首错 | 阻塞归属/恢复条件 |
|---|---|---|---|---|
| egl_has_extension_nocontext | EGL_PLATFORM=surfaceless ./egl_has_extension_nocontext | 77 | couldn't open display | test/egl_common.c get_egl_display_or_skip() 硬编码 XOpenDisplay(NULL)，EGL_PLATFORM 无法绕过；恢复=提供 X server 或上游改 eglGetPlatformDisplay（禁止改上游伪通过） |
| egl_epoxy_api | EGL_PLATFORM=surfaceless ./egl_epoxy_api | 77 | couldn't open display | 同上 |
| egl_gles1_without_glx | EGL_PLATFORM=surfaceless ./egl_gles1_without_glx | 77 | couldn't open display | 同上 |
| egl_gles2_without_glx | EGL_PLATFORM=surfaceless ./egl_gles2_without_glx | 77 | couldn't open display | 同上 |
| egl_gl | （R01 已测） | 134 | No provider/libGL.so.1 dlopen 失败 | mesa 无 libGL.so.1（glx=disabled）；恢复=mesa 补充发布桌面 GL 栈 |
| glx_public_api | DISPLAY=:199 ./glx_public_api | 77 | couldn't open display | 无 X server；Xvfb 不可部署（设备无二进制、制品仓无包）；恢复=Xvfb/Xorg 部署 |
| glx_public_api_core | DISPLAY=:199 | 77 | couldn't open display | 同上 |
| glx_glxgetprocaddress_nocontext | DISPLAY=:199 | 77 | couldn't open display | 同上 |
| glx_has_extension_nocontext | DISPLAY=:199 | 77 | couldn't open display | 同上 |
| glx_shared_znow | DISPLAY=:199 | 77 | couldn't open display | 同上 |
| glx_alias_prefer_same_name | DISPLAY=:199 | 77 | couldn't open display | 同上 |
| glx_gles2 | DISPLAY=:199 | 77 | couldn't open display | 同上 |
| glx_static | 链接期失败 | - | ld.lld attempted static link of dynamic libX11.so | OHOS 无静态 libX11；恢复=发布静态 X11 栈 |
| glx_beginend | 链接期失败 | - | undefined glBegin（缺 libGL/GLX 符号） | mesa glx=disabled 无 libGL；恢复=mesa 补充 libGL |
| header_guards | ./header guards | 0 | - | PASS |
| misc_defines | ./misc defines | 0 | - | PASS |
| khronos_typedefs | ./khronos typedefs | 0 | - | PASS |
| gl_version | ./gl_version | 0 | - | PASS |
| WGL×4（wgl_core_and_exts/wgl_per_context_funcptrs/wgl_usefontbitmaps/wgl_usefontbitmaps_unicode） | 平台守卫 | - | build_wgl 仅 host_system=='windows' | OHOS 非 Windows 不实例化，计入分母 |
| CGL×2（cgl_core/cgl_epoxy_api） | 平台守卫 | - | host_machine.system().contains('darwin') | OHOS 非 macOS 不实例化，计入分母 |

### 依赖/制品复核（首次跳过与最终前各一次）
- 首次（R01 后）：xorgproto/2025.1、libx11/6.4.0、mesa/24.3.4.1.1 全部在 ohpcd registry 有 recipe+binary（conan download 命中）
- 最终前（R02）：conan download 三依赖 --only-recipe 全部命中（f5274e33 / 63e25e48 / 8be568ed）；Xvfb/Xorg/Xwayland/xserver 制品仓均 0 匹配 → 显示类 skip 恢复条件无法满足
- 结论：无"依赖已发布未恢复运行"的遗漏；skip/fail 均由真实平台条件所致

### 双口径（R02 最终）
- source_declared_total = 24；configured_executable_total = 16；executed_passed_total = 4；
  executed_skip77_total = 11；executed_fail_total = 1（egl_gl）；link_failed_total = 2（glx_static/glx_beginend）；platform_not_instantiable = 6（WGL 4 + CGL 2）
- 通过率：4/24 (16.7%) 源声明口径；4/16 (25.0%) 当前配置可执行集合口径（与 R01 相同，未伪造提升）

## R03 Xvfb 显示服务攻关台账（2026-09-23，task_id libepoxy-1.5.10.1.1-r03-pc1-35-20260923T160058Z）
### 部署与验证
- Xvfb 部署：cmd-pkgs xorg-server/21.1.15 + 配套库（pixman 0.46.4 / libxfont2 2.0.7 / nettle 3.10.2 /
  libtirpc 1.3.3 / libpthread-stubs 0.4 / font-util 1.4.1 / libfontenc 1.1.7 / xkbcomp 1.4.7 /
  libxkbcommon 1.6.0 / libx11 6.4.0 / xkeyboard-config 2.42 / libpng 1.6.43 / freetype 2.14.3 /
  zlib 1.3.1）；libXau/libxcb/libxkbfile 从 conan 缓存补（cmd-pkgs 无对应包）
- 关键适配：设备 /tmp 为只读 erofs（100% 满），Xvfb 默认 unix socket /tmp/.X11-unix 无法创建
  → 启动参数 `-nolisten unix -listen tcp`，客户端走 TCP `DISPLAY=127.0.0.1:199`（等价 :199 显示号）
- 可达验证：XOpenDisplay 探针 exit 0（1280x800 24bpp, The X.Org Foundation）；TCP 6199 连接成功
- Xvfb 进程经 busybox setsid 后台存活（PID 6073, EVENTPOLL 状态）

### R03 全量尝试矩阵（DISPLAY=127.0.0.1:199 实跑）
| 用例 | 命令/环境 | exit | 首错 | 阻塞归属/恢复条件 |
|---|---|---|---|---|
| egl_has_extension_nocontext | DISPLAY=127.0.0.1:199 ./egl_has_extension_nocontext | **0** | - | **收复 PASS**（Xvfb 生效，XOpenDisplay 成功） |
| egl_epoxy_api | 同上 | 77 | Couldn't create a GL context | EGL_OPENGL_BIT/WINDOW_BIT config 在 mesa 无窗口平台下无匹配；恢复=mesa EGL 支持该 config 或测试改 surfaceless |
| egl_gles1_without_glx | 同上 | 77 | Couldn't create a GLES1 context | 同上（EGL_OPENGL_BIT config 无匹配） |
| egl_gles2_without_glx | 同上 | 77 | Couldn't create a GLES2 context | 同上 |
| glx_public_api | 同上 | 134 | Couldn't open libGL.so.1 | mesa glx=disabled 无 libGL；恢复=mesa 补充桌面 GL 栈 |
| glx_public_api_core | 同上 | 134 | 同上 | 同上 |
| glx_glxgetprocaddress_nocontext | 同上 | 134 | 同上 | 同上 |
| glx_has_extension_nocontext | 同上 | 134 | 同上 | 同上 |
| glx_shared_znow | 同上 | 134 | 同上 | 同上 |
| glx_alias_prefer_same_name | 同上 | 1 | Internal error: Failed to find real dlsym | dlwrap.c dlvsym GLIBC 版本符号检查失败（OHOS libc 无 GLIBC_* 版本）；恢复=适配 dlwrap 或忽略（上游 dlvsym 依赖） |
| glx_gles2 | 同上 | 1 | 同上 | 同上 |

### R03 双口径（最终）
- source_declared_total=24；configured_executable_total=16；executed_passed_total=**5**
  （R01/R02 的 4 无条件 + R03 收复的 egl_has_extension_nocontext）
- executed_skip77_total=**3**（egl_epoxy_api / egl_gles1_without_glx / egl_gles2_without_glx，
  XOpenDisplay 已成功、EGL context 创建仍失败）
- executed_fail_total=**5**（egl_gl 134 缺 libGL + glx_public_api/glx_public_api_core/
  glx_glxgetprocaddress_nocontext/glx_has_extension_nocontext/glx_shared_znow 134 缺 libGL）
- fail_by_dlwrap=**2**（glx_alias_prefer_same_name / glx_gles2 exit 1，dlvsym 版本符号）
- link_failed_total=**2**（glx_static -static 链动态 libX11 / glx_beginend 缺 libGL 符号）
- platform_not_instantiable=**6**（WGL×4 windows 守卫 + CGL×2 darwin 守卫，用户明确排除 Windows）
- 通过率：**5/24 (20.8%)** 源声明口径；**5/16 (31.3%)** 当前配置可执行集合口径（较 R02 4/16 提升 1 项）
