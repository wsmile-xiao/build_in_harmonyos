# DRAFT-astromenace-1.3.2-gles2-null-context: OHOS 无 GL 上下文调用真实 GLES2 的 glGetString 触发 SIGSEGV，需 eglGetCurrentContext 判空的拦截器空指针防护

> **Contributor**: junshi_liu | **Status**: Draft（pending editor review）| **Updated**: 2026-08-27
> **Source**: AstroMenace 1.3.2 HarmonyOS PC 适配（build_in_harmonyos，archives/a/astromenace/1.3.2）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 场景

在 headless / 无 GL 上下文的 HarmonyOS (OHOS) 主机上对桌面 OpenGL 库做 GLES2 兼容转发时，某个 GL 入口缺拦截器或拦截器无空上下文防护，进程立即 SIGSEGV（退出码 139），整条兼容测试程序崩溃，无法区分是哪个调用失败。

## 问题

可复用问题签名（日志症状）：

```text
Segmentation fault
process exit code 139 (SIGSEGV)
# 或 gdb 报告 signal SIGSEGV, Segmentation fault
```

真实证据（AstroMenace 1.3.2, pc2-5 OHOS 主机）：
- 二分定位：隔离 11 个拦截器调用，case 1-10 全部 rc=0，**唯一崩溃点 case 11 `glGetString` rc=139**；
- 根因：`gles_compat.cpp` 缺 `glGetString` 拦截器，测试解析到真实 `libGLESv2`，无 GL 上下文时 SIGSEGV。

## 根因

`dlsym`/`eglGetProcAddress` 解析到真实 `libGLESv2` 后，在没有 GL 上下文（`eglGetCurrentContext()==NULL`）时调用其内部实现，函数访问当前线程 GL 状态时解引用空上下文指针，触发 SIGSEGV。**解析到真实符号 ≠ 可以在任意时刻调用**：凡缺失空上下文防护的拦截器都会在无上下文路径上崩溃。

## 修复（最小方案）

为缺失的 GL 拦截器加空上下文防护：先 `eglGetCurrentContext()` 判空，无上下文时安全返回（NULL），有上下文才 `dlsym`/`eglGetProcAddress` 转发真实 GLES2。

```cpp
static void* g_real_glGetString = nullptr;

static const char* interceptor_glGetString(GLenum name) {
    if (eglGetCurrentContext() == nullptr) {
        return nullptr; // 无 GL 上下文：安全返回，避免解引用空上下文 SIGSEGV
    }
    if (!g_real_glGetString) {
        g_real_glGetString = (void*)dlsym(RTLD_NEXT, "glGetString");
        if (!g_real_glGetString)
            g_real_glGetString = (void*)eglGetProcAddress("glGetString");
    }
    return ((PFNGLGETSTRINGPROC)g_real_glGetString)(name);
}
```

原则：拦截器必须**双重防护**——符号解析判空（`g_real_glXxx` 是否已缓存）与上下文判空（`eglGetCurrentContext()==NULL` 提前返回），缺任一无上下文路径都会崩溃。与 `glEnable`/`glDisable` 已有的 `if (g_real_glXxx)` 防护同模式。

## GLU / ALUT shim 边界

- **GLU**：OHOS 无 GLU，用 `gles_compat` 提供最小 GLU 声明/降级（链接期满足符号），不实现真实算法；
- **ALUT**：OHOS 无 alut，提供 `alut_shim.h`（103 行）作为链接/调用占位，满足 AstroMenace 对 `alutInit` 等符号的引用。

## 验证

- `gles_compat_test_fixed` 完整测试：修复前 rc=139 → **修复后 rc=0**；
- 二分 `mini_crash` case 11（glGetString）：rc=0；
- 构建：`[100%] Built target AstroMenace`，产物 ELF64 PIE AArch64 3.0MB；
- 上游无自动化测试套件（CMake 测试钩子=0）。

## 可复用边界

- 适用：任何桌面 OpenGL→GLES2 移植在 headless / 无 GL 上下文 OHOS 主机上的验证；
- 限制：需要真实 EGL 上下文才能完整验证转发路径；R8 合规（不用 `#ifdef __OHOS__` 平台宏，用运行时判空表达）；
- 查重：对 `AstroMenace`/`fixed-function OpenGL`/`GLES2 compatibility`/`glGetString`/`eglGetCurrentContext`/`GLU`/`ALUT` 在 `knowledge/` 及索引全量检索无等价条目（E276 为 Conan BadZipFile 主题，非等价）。

## 关联条目

- `E013`：`dlopen/dlsym/-ldl` 动态链接 —— 同族 dlsym 解析，但 E013 是链接期符号缺失；本稿是运行时无上下文崩溃。