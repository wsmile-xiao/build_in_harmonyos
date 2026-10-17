# DRAFT-libsoup3-shared-glib-release-form-fix — libsoup3 静态内嵌 gobject 的依赖侧修复：对齐共享 glib 发布形态

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-10
> **Severity**: 🟡 medium | **Category**: ohos / gobject / glib / libsoup3 / gtk4 / meson / conan
> **来源任务**: libsoup3-3.6.5-r3-r01-pc1-8-20260910T095049Z
> **同族草稿**: DRAFT-libshumate-libsoup3-static-gobject-dual-glib-sigabrt（问题识别/阻塞报告，
>  本条目是其"恢复条件"的配方级实现）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本候选的增量（差异化） |
|---------|---------|--------|----------------------|
| **DRAFT-libshumate-libsoup3-static-gobject-dual-glib-sigabrt** | 草稿 | 消费侧问题识别 + 0/N 阻塞上报 + 恢复条件（"分析端发布共享 glib 变体"） | 本候选是**依赖侧配方级修复实现**：具体 requires 对齐、pc 覆盖补 -lintl、Requires.private 剥除、NEEDED/符号取证 |
| **E538**（harfbuzz glib shared 选项冲突） | 正式收录 | 依赖图解析/包 ID 层面 | 本候选是运行时类型系统双副本的**修复配方**，非解析层面 |
| **E452 / E517**（shared ELF codesign/dlopen） | 正式收录 | 签名校验层面 | 本候选签名正常，是类型系统重复注册的修复 |
| **gssdp 单副本方案**（.pc Libs 置空） | 已收录配方 | 消费侧单副本化 | 本候选证明含 gtk4 链时**消费侧不可修**，改走依赖侧修复——边界新增 |

## Scope（何时用）

ohpcd 已发布某库的**静态内嵌 gobject 发布二进制**（NEEDED 无 libgobject-2.0.so.0、
nm -D 见 `T g_type_register_fundamental`），且消费链通过 gtk4 等必然加载共享 glib；
需要**从依赖侧消除双副本**时：

- 目标库 meson 构建、conan 配方可改（requirements 可对齐共享 glib）；
- 进程级症状 `cannot register existing type 'gchar'`（gvaluetypes.c:453 SIGABRT）；
- 修复后需无损取证确认：NEEDED 含 libgobject-2.0.so.0 + 无 `T g_type_register_fundamental` 强导出。

## Symptom（修复前）

```text
(process:37627): GLib-GObject-CRITICAL **: cannot register existing type 'gchar'
GLib-GObject:ERROR:../gobject/gvaluetypes.c:453:_g_value_types_init: assertion failed: (type == G_TYPE_CHAR)
Bail out! # 测试 exe exit=134 (SIGABRT)
llvm-nm -D libsoup-3.0.so.0 | grep ' T g_type_register_fundamental'  # 有（静态内嵌）
llvm-readelf -d libsoup-3.0.so.0 | grep NEEDED                       # 无 libgobject-2.0.so.0
```

## Root Cause

依赖发布二进制把 glib 副本静态内嵌进 .so 并导出完整 g_* 符号表，与消费链必须加载的
共享 glib 形成进程内双 GObject 类型系统 → 基本类型重复注册 SIGABRT。根因在**依赖
发布形态**（配方链接了非共享 glib 副本），而非消费者代码。

## 修复（依赖侧，可跨库复用）

1. **requirements 对齐共享 glib**（gtk4 链 r85/r86 硬约束同款）：
   ```python
   self.requires("glib/2.84.0.1.1", options={"shared": True},
                 transitive_headers=True, transitive_libs=True)
   ```
   必须与消费链使用同一 glib 包/版本，否则即使 shared 也会多副本。
2. **官方 glib-2.0.pc 覆盖 PkgConfigDeps 生成版**：生成版 Libs 缺 `-lintl`
   （libsoup 的 soup-init.c 经 glib i18n 宏引用 `g_libintl_bindtextdomain`，ld.lld
   报 undefined symbol）。用 glib 包内官方 .pc（修正 prefix 为 package_folder）
   覆盖 generators 同名文件：
   ```python
   _text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", _text, count=1, flags=re.M)
   _text = re.sub(r"^Requires\.private:.*$", "", _text, count=1, flags=re.M)  # 剥 pcre2/zlib 传递 .pc 缺失
   ```
3. **取证三连确认修复生效**：
   ```bash
   llvm-readelf -d libsoup-3.0.so.0 | grep NEEDED    # 必含 libgobject-2.0.so.0
   llvm-nm -D libsoup-3.0.so.0 | grep ' T g_type_register_fundamental'  # 无命中
   <test-exe> 2>&1 | grep 'cannot register existing type'               # 无输出
   ```
4. **工具链/签名已知坑沿用**：generate() 清 AR/AS/STRIP/NM/RANLIB 坏环境变量并
   shutil.which 定位真实工具；tc.strip=None（strip 破坏 .codesign 哈希导致
   dlopen Permission denied）；package() 用 builddir 原始链接产物覆盖 meson
   install 改写的 .so。

## 边界与反例

- **gssdp 单副本方案（消费侧 .pc 置空）不可用于含 gtk4 链的图**：共享 glib 副本
  无法从进程移除；此时必须依赖侧修复（本条目）。
- 本条目不适用于依赖图解析冲突（E538）或签名校验 dlopen 拒绝（E452/E517）。
- 未修复前消费者测试 0/N 如实上报（计入分母不计通过），不伪造通过率。

## 验证（单库实证 libsoup3/3.6.5-r3）

- conan create exit=0，test_package L1 通过；
- 取证：NEEDED 含 libgobject-2.0.so.0；nm -D 无 `T g_type_register_fundamental`；
- 进程级：test_package + ohos 专项测试 exit=0，无 gchar 冲突；
- 上游测试：33 个测试可执行构建成功，29 个实际运行 413 例通过（86.6%）；
  失败项为 hsts 断言 SIGTRAP（2 项）与平台限制（unix-socket/http2 TLS 后端缺失）；
- 下游 libshumate 恢复条件命中：修复后可重跑其上游测试（恢复验证由 libshumate 侧任务执行）。
