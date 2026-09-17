# DRAFT-ohos-gl-symbols-are-dispatcher-stubs — OHOS 的 GL 直连符号是调度空桩：真函数必须经 `eglGetProcAddress`

> **对应结构化数据**：`knowledge/drafts/DRAFT-ohos-gl-symbols-are-dispatcher-stubs.kv`
> **验证实例**：freeglut 3.6.0（PR #10168，OHOS PC aarch64，SDK 26，GPU = HUAWEI Maleoon 916）
> **Status**: DRAFT ｜ **Severity**: 🔴 high ｜ **Updated**: 2026-09-15

## 1. 一句话

在 OHOS 上，`libGLESv2.so` **导出**的 GL 符号能链接、能调用、**不报错**，但**什么都不做** ——
它们是调度空桩（dispatcher stub）。真函数只能经 `eglGetProcAddress()` 取得；
库内部自持 GL 调用的库还必须加 `-Wl,-Bsymbolic`，否则库内引用仍会落到空桩上。

## 2. 现象（最坑的是「静默」）

### 症状 A：画面全黑，但一切「正常」

链接通过、运行无异常、`glGetError()` 返回 `0x0`，而画面不变/全黑。
排查方向极易跑偏到逻辑错误、着色器错误、上下文没创建成功上。

### 症状 B：链接期 GLES1 符号未定义

核心仍引用固定管线入口的库，在消费者链接时直接失败：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: glBegin
>>> referenced by libfreeglut-gles.so
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: glVertex3fv
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: glNormal3fv
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: glEnd
```

## 3. 实验（决定性对照）

同一个进程、同一个已经 `eglMakeCurrent()` 的 GLES2 上下文，只改「函数从哪来」：

| 取函数方式 | `glGetString(GL_VERSION)` | `glClearColor+glClear+glReadPixels` |
|-----------|--------------------------|-----------------------------------|
| **直连链接符号** | `NULL` | `glGetError()=0x0`，**像素仍全 0** |
| **`eglGetProcAddress()`** | `"OpenGL ES 3.2 B301"` | **真渲染**：`pixel=255,0,0,255` |

同一环境下 `GL_RENDERER = Maleoon 916`。

**结论**：符号存在 ≠ 函数可用。EGL 规范本就要求驱动入口经 `eglGetProcAddress` 获取，
OHOS 把这一要求**推广到了核心入口**。

## 4. GLES1：不是「版本低」，是「没有」

OHOS 只提供 GLES2/GLES3（`GLES2/gl2.h`、`libGLESv2.so`），
**无 `GLES/gl.h`、无 `libGLESv1_CM`**。实测经 `eglGetProcAddress` 探测 7 个固定管线入口：

| 入口 | `eglGetProcAddress` 结果 |
|------|------------------------|
| `glColor4f` | ✅ 可解析 |
| `glBegin` / `glEnd` / `glVertex3fv` / `glNormal3fv` / `glTexCoord2fv` / `glColor4fv` | ❌ **NULL** |

即 OHOS 上确实无实现 → 必须自备桩。这不是「用 GLES2 顶上」能解决的：
GLES2/GLES3 里根本没有 `glBegin`/`glEnd`/`glVertex3fv`。

## 5. 推荐方案

在库内加一层 **GL 调度层**：把受影响的入口包一层经 `eglGetProcAddress()` 解析，
并用 `-Wl,-Bsymbolic` 链接。**三个要点缺一不可**：

```c
/* ① 包装函数必须用 GL 原名（不能改别名），否则库内调用不会命中 */
const GLubyte *glGetString(GLenum name)
{
    static PFN_GLGETSTRING real;                    /* ② 静态缓存，只解析一次 */
    if (!real)
        real = (PFN_GLGETSTRING)eglGetProcAddress("glGetString");
    return real ? real(name) : NULL;
}
```

```cmake
# ③ 关键：-Bsymbolic 让库内引用绑定到本库包装函数，而非 libGLESv2.so 的空桩
list(APPEND LIBS "-Wl,-Bsymbolic")
```

```c
/* GLES1 固定管线（OHOS 无实现）：no-op 桩 + 一次性告警（避免刷屏） */
void glBegin(GLenum mode) { (void)mode; warn_once("glBegin"); }
void glEnd(void)          { warn_once("glEnd"); }
```

**只包装库内实际调用的入口**，不必全量包装。用静态检查列出清单：

```bash
readelf --dyn-syms lib<pkg>.so | awk '$7=="UND"{print $8}' | grep -E '^gl[A-Z]'
```

freeglut 实测：13 个未定义 GL 符号（其中 6 个 GLES2 已有、运行期可解析），
补上调度层后 **13 → 0**。

### 验证清单（必须全过）

1. `readelf --dyn-syms` 中未定义 `gl*` 符号**归零**；
2. 消费者侧链接**成功**（不再有 `--no-allow-shlib-undefined: glBegin`）；
3. 运行期**真实渲染**并 `glReadPixels` 读到**预期的具体像素值**（不是「无报错」）。

## 6. 禁止

- ❌ **以「链接通过 / 无报错 / `glGetError()==0`」证明 GL 可用** —— 三者都不构成证明，
  空桩路径下全部满足却什么都没发生。只有「经 `eglGetProcAddress` 取到 + 可观测渲染结果」才是证明。
- ❌ **写了调度层却忘了 `-Wl,-Bsymbolic`** —— 这是最易漏的一步，症状与「完全没写调度层」
  **一模一样**（依旧全黑），而且因为「代码里明明有调度层」反而更难怀疑到绑定问题。
- ❌ **指望用 GLES2/GLES3 替代 GLES1 固定管线** —— 二者是「有/无」的关系，
  GLES2 里没有 `glBegin` 等入口。
- ❌ **全量包装整个 GL API** —— 只需包装库内实际调用的入口，全量包装徒增补丁体积与合并冲突面。
- ❌ **见到 `glReadPixels` 全 0 就断定渲染逻辑有 bug** —— 先判定符号来源
  （直连 vs `eglGetProcAddress`），再谈渲染正确性。

## 7. 适用范围

**适用**：所有在 OHOS 上**自持 GL 调用**的库/应用，尤其中间层库 ——
freeglut、cogl、clutter、imgui、SDL 的 GL 后端、老式 GL 工具库。

**不适用/不受影响**：自己就走 `eglGetProcAddress` 的应用（现代引擎通常如此）。
**需特别注意**：纯 GLES1 固定管线库在 OHOS 上无法直接链接，需自备桩或改走 shader 路径。

## 8. 与既有条目的关系（差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **E471**（OHOS PC 无任何原生显示后端，gtkmm 场景）| 那条讲**无显示服务**导致 `gtk_init` 失败；本条是**显示栈可用但符号调用落空**，两者根因不同 |
| **E321**（gl4es 补桌面 GL 固定管线，B1 方案）| 那条是**补一个库层**（`libGL.so` 兼容层）解决固定管线缺失；本条是**同一个 GLES2 上下文内**的符号获取路径问题。E321 里也提到 `libGLv4.so 实为 stub——全符号同地址`，与本条「符号存在但不可用」同源，可作为该现象的旁证；但 E321 未给出「核心 GLES2 入口亦为空桩、需 `-Wl,-Bsymbolic` 调度层」这一结论 |

> 查重（2026-09-15）：main 上 `dispatcher stub` / `调度桩` / `符号是桩` / `Bsymbolic` /
> `GLES1` / `GLESv1` 均 **0 命中**；`eglGetProcAddress` 唯一命中 E276 是讲 conan `get()`
> 文件名解析（无关）；9 个 `dispatcher` 命中全是 `functools.singledispatch`（无 GL/EGL 相关）。
> 本条为空白领域。

## 9. 方法论提炼

1. **先做密闭探针判定平台行为**，再读代码猜。本次用一个约 66 行的 EGL 探针就定性了整条结论。
2. **用「直连 vs `eglGetProcAddress`」做受控对照** —— 只改一个变量，结论才可信。
3. **「无报错」不等于「生效」** —— 需要可观测结果（像素值）作为证据。
4. **静态检查 + 运行期验证双管** —— `readelf --dyn-syms` 看符号（链接期风险），
   `glReadPixels` 看像素（运行期实效）。
