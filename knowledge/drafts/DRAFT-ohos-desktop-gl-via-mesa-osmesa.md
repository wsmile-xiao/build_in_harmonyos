# DRAFT-ohos-desktop-gl-via-mesa-osmesa — OHOS 无桌面 GL 时，用 Mesa OSMesa 满足「需要一份 GL 实现」的库

> **对应结构化数据**：`knowledge/drafts/DRAFT-ohos-desktop-gl-via-mesa-osmesa.kv`
> **验证实例**：glu 9.0.3（Mesa GLU，PR #10090，OHOS PC aarch64，SDK 26）
> **Status**: DRAFT ｜ **Severity**: 🟡 medium ｜ **Updated**: 2026-09-15

## 1. 一句话

OHOS 没有桌面 OpenGL（无 `libGL.so` / `GL/glx.h` / `glu.h`），但**这不等于「不可适配」**——
先分清库需要的到底是「一份 GL **实现**」还是「GLX/X11 窗口集成」还是「固定管线**入口**」。
若是第一种，可用 **Mesa OSMesa**（`mesa/24.3.4.1` 的 `libOSMesa.so`）替代。

## 2. 症状

```bash
fatal error: 'GL/gl.h' file not found      # 或 'GL/glu.h'
cannot find -lGL
Could NOT find OpenGL
```

常见误判：直接归为「不可适配」。

## 3. 分层判据（关键：别把三种需求混为一谈）

| 库实际需要什么 | 判定依据 | 出路 |
|---|---|---|
| 「一份提供 OpenGL API 的**实现**」 | `glX`/X11 引用数 **= 0** | ✅ **本条目**：OSMesa |
| 「**GLX / X11 窗口集成**」 | `glX*` / `XOpenDisplay` 引用 > 0 | ⚠️ OHOS 无 X11，需另作评估 |
| 「桌面 GL **固定管线入口本身**」 | 调 `glBegin`/`glMatrixMode`/`glOrtho` 等 | ⚠️ 走 **E321**（gl4es）或自备桩 |

**判据要用 grep 数引用，不是看库名。**

## 4. 实证：glu 9.0.3 属第一种

```bash
# ① 决定性前置检查：是否真依赖 GLX / X11
grep -rn "glX\|GL/glx.h\|XOpenDisplay\|XCreateWindow" src/ include/ | wc -l
# → 0   说明只需「一份 GL 实现」，不依赖 X11
```

而 `mesa/24.3.4.1`（**已发布 ohpcd**，实测 `mesa/24.3.4` 与 `24.3.4.1` 均可见）
提供的 **OSMesa** 正是这样一份实现：

- 交付 `libOSMesa.so` + `include/GL/gl.h`
- **不需要** X11 / Wayland / DRM（离屏软件桌面 GL）

更关键：glu 的构建脚本**原生支持**这一组合 —— meson 选项 `gl_provider` 的
choices 就是 `['glvnd', 'gl', 'osmesa']`。

## 5. 推荐方案

```python
# 配方侧
def requirements(self):
    self.requires("mesa/24.3.4.1")
# 生成期指定 provider
tc.project_options["gl_provider"] = "osmesa"
```

### 必踩的坑：`.pc` 名称对不上

conan 的 `PkgConfigDeps` 按**包名**生成 `mesa.pc`，而上游 meson 找的是
`dependency('osmesa')` —— **名字不匹配，直接失败**。

mesa 包内虽自带 `lib/pkgconfig/osmesa.pc`，但其 `prefix=/` → `libdir=/lib`，
照用会让 pkg-config 发出 `-L/lib`，实测报：

```
ld.lld: error: unable to find library -lOSMesa
```

**解法**（在 `generate()` 里动态修正，不要硬编码路径）：

```python
copy(self, "osmesa.pc", src=os.path.join(mesa_pkg, "lib", "pkgconfig"),
     dst=self.generators_folder)
replace_in_file(self, dst, "prefix=/", f"prefix={mesa_pkg}")
```

### 验证

```bash
readelf -d <pkg>/lib/lib<pkg>.so | grep -E 'NEEDED.*OSMesa'
# 期望：libOSMesa.so.8
```

⚠️ **必须用 `readelf -d` 确认 NEEDED 真含 `libOSMesa.so.<N>`** ——
构建 `rc=0` 不代表链接目标正确（freeglut 案例已证明这点）。

## 6. 禁止

- ❌ **「无桌面 GL → 不可适配」** —— 先分清三种需求。glu 实测 `glX` 引用 0，属可适配。
- ❌ **凭库名判断依赖面** —— 名字带 `gl`/`GLU` ≠ 依赖桌面 GL / GLX。判据是
  `grep -rn "glX\|GL/glx.h\|XOpenDisplay"` 的**实际引用数**。
- ❌ **硬编码 `-L` 路径或手改 `.pc` 出处** —— 应在 conan 生成期**动态**修正 prefix
  为实际 `package_folder`。硬编码会在 CI（cache 路径不同）失败而本地通过。
- ❌ **把 OSMesa 当固定管线方案** —— OSMesa 是「软件渲染的桌面 GL 实现」，
  不等于「固定管线入口在 OHOS 侧可用」。需按实际探测判断，必要时走 E321。
- ❌ **只验 `rc=0` 不验 `readelf -d`** —— 必须确认 NEEDED 里真有 `libOSMesa.so.<N>`。

## 7. 适用范围

**适用**：任何「面向桌面 OpenGL但**没有 GLX/X11 依赖**」的库/工具 ——
老式 GL 图形库、GL 工具库（GLU 类）、需 GL 头/上下文做离屏或软件渲染的场景。
典型信号：出现 `GL/gl.h` / `GL/glu.h` 的 include、`-lGL` 的链接需求，
但 `glX*` 调用为 **0**。

**不适用**：真正依赖 GLX/X11 窗口集成的库；需要固定管线入口本身的库（走 E321）。

## 8. 与既有条目的关系（差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **E321**（gl4es 补桌面 GL 固定管线）| **互补的两条轴**：E321 解决「缺**固定管线入口**」（用 gl4es 做 OpenGL 1.5/2.1 → GLES2 翻译 + FPE 模拟，提供 `libGL.so` 兼容层）；本条解决「缺**一份 GL 实现**」（用 Mesa OSMesa，`glX` 引用为 0 的库够用）。**选择顺序**：先判断库需要「实现」还是「固定管线入口」—— GLU 属前者，纯固定管线游戏（assaultcube）属后者。E321 **未提及 OSMesa**（实测 0 处），两者不重叠 |
| **E471**（OHOS PC 无原生显示后端）| 那条讲**无显示服务**导致 `gtk_init` 失败与测试分类原则；本条是**编译/链接期的 GL 实现选择**，问题层不同 |
| **DRAFT-ohos-hidden-symbol-visibility-exports-zero** | 同批产出的姊妹条目（glu 适配的另一条发现），讲符号可见性而非依赖选择 |

> 查重（2026-09-15）：main 上 `OSMesa` / `osmesa` / `gl_provider` / `osmesa.pc` /
> `libOSMesa` **均 0 命中**；E321 全文 `osmesa`/`OSMesa` 命中 **0**。
> 本条为空白领域。

## 9. 方法论提炼

1. **选择替代实现前先「验需求面」，不要「看名字」** —— 用 grep 数实际引用
   （`glX`/X11 调用数）判定库真正需要什么。
2. **「无某能力」≠「不可适配」** —— 先找是否有等效实现（OSMesa 之于桌面 GL）。
3. **优先用上游既有的 provider 开关** —— 别自己改 pkg-config 或 hardcode 路径。
4. **跨平台路径必须动态生成** —— `.pc` 的 prefix 要按实际 `package_folder` 改写，
   硬编码会在 CI 与本地之间产生不一致。
5. **验证要落到产物**（`readelf -d` 的 NEEDED），而非构建流程的绿灯。
