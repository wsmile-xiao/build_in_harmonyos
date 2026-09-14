# DRAFT: 无 GPU 上下文 CI 上真实测试函数指针表 loader（glad 2.0.8 实证）

## 问题描述

glad 等"函数指针表"式图形 loader 的上游运行用例依赖真实 GL/GLES/EGL 上下文：`test/c/run/*` 用例编译链接 `-lglfw`（或 mingw+wine），运行时创建显示上下文；OHOS CI（无 GPU、无显示服务器、无 GLFW/mingw/wine）下这些用例**硬阻塞**，R51 要求"逐项列举技术原因"而非跳过。

但 loader 的**初始化路径本身**不依赖真实上下文，可用 stub get-proc-address 驱动真实执行。

## 根因

- glad 的运行测试把 `gladLoadGL(load)` 的真实调用与 GTK/GLFW 等窗口上下文耦合
- CI 判定"无 GPU → 全部运行用例不可执行"是过度归因：表填充/版本解析/扩展探测都可独立验证
- glad2 的 `GLADloadfunc` 返回类型是 `GLADapiproc`（`void(*)(void)`）而非 `void*`——stub 签名写错（返回 `void*`）编译不报错但语义错误（本轮实测 `incompatible function pointer types` 警告）

## 解决方案

test_package 写 stub proc-address：

```c
static void stub_api(void) {}
static const GLubyte *stub_get_string(GLenum name) {
    (void)name; return (const GLubyte *)"4.6.0";
}
static GLADapiproc load(const char *name) {
    if (name && strcmp(name, "glGetString") == 0) return (GLADapiproc)stub_get_string;
    if (name && strcmp(name, "glClear") == 0)     return (GLADapiproc)stub_api;
    return NULL;
}
/* main: */
int version = gladLoadGL(load);
/* 断言: version != 0, GLAD_GL_VERSION_4_6 == 1, glad_glGetString != NULL, glad_glClear != NULL */
```

要点：
1. stub 签名必须与 `GLADloadfunc` 一致（返回 `GLADapiproc`），glGetString 返回版本串驱动 `glad_gl_find_core_gl` 的 sscanf 解析。
2. 除驱动链路上的符号外其余返回 NULL：避免初始化期间调用假地址崩溃（glad 对 `glGetString==NULL` 直接 return 0）。
3. 断言函数表项非 NULL = 证明表填充逻辑真实执行。

## 验证

- `test_glad`：rc=0，`loader init executed, version=4.6, table populated`
- `harmonyos_specific_test`：rc=0，`platform=OHOS(aarch64)`，`GL_VERSION_4_6 declared`
- conan create test_package L1 执行（ctest 双用例）通过

## 适用范围

- glad，以及任何函数指针表式图形 loader（GLEW、EGL loader、独立 GL loader）的无 GPU CI 测试
- 也适用于"无真实硬件但需验证装载/解析/表填充"的驱动类库

## 反例 / 边界

- 需要真实上下文才能验证的行为（如 `glGetString(GL_VERSION)` 真实字符串、扩展可用性）无法 stub 覆盖，仍如实记录为未运行
- 若库没有独立于上下文的表初始化 API（如 loader 直接把上下文绑定到静态全局），stub 方式受限

## 查重（四范围）

- 正式知识（E###/index.tsv）：零命中（无 GL loader/函数指针表 stub 测试条目）
- 知识图谱/草稿/doc：零命中（E471 显示上下文分类、E464 无头资源注册为相邻领域，非同方案）

**路径判断**：path B（new_draft）——候选已验证、可跨库复用、查重未命中。
关系：`caused_by` → 生成器工具交付形态（配对草稿）；`similar_to` → E471/E464（headless 领域但方案不同）。
适用边界/反例：无法覆盖需要真实 GL 上下文行为验证的场景（已在台账如实列为未运行）。

---

**草稿状态**: 待主编审核后提升为正式条目
**最后更新**: 2026-09-10