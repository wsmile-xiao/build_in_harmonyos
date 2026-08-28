# DRAFT-gtk4-glib-tool-codesign-rpath

依赖包 bin 工具 `.codesign` 失效 + 无 RPATH → `gnome.compile_resources` 执行失败（HarmonyOS OHOS）

- 触发事件：GTK4 4.22.4 HarmonyOS PC 适配（`glib/2.84.0.1.1 shared=True`）
- 触发命令：`ninja` → `glib-compile-resources`（生成 `gdk/gdkresources.c/h`）

## 问题

Meson 构建 GTK4 时，`gdk/meson.build` 通过 `gnome.compile_resources` 调用 pkg-config
变量 `glib_compile_resources`（来自 `gio-2.0.pc`）所指向的
`glib/2.84.0.1.1`（shared）包内工具 `bin/glib-compile-resources`，ninja 报：

```
FAILED: [code=126] gdk/gdkresources.c
/storage/Users/currentUser/.conan2/p/glibd610586c02b9c/p/bin/glib-compile-resources gdk/gdk.gresource.xml ...
/bin/sh: /storage/.../glib-compile-resources: Operation not permitted
```

## 根因

HarmonyOS 上两个独立缺陷叠加：

1. **签名失效（EPERM）**：glib shared 包的 bin 工具携带过旧的 `.codesign` 段，OHOS XPM
   拒绝执行 → `Operation not permitted`（exit 126）。即使文件有执行位也无济于事。
2. **无 RPATH（动态库找不到）**：该工具是动态链接 ELF（NEEDED `libgio-2.0.so.0`、
   `libglib-2.0.so.0`、`libintl.so.8`），但无 RPATH/RUNPATH，加载器无法找到包自身 lib 目录，
   重签后仍报 `Error loading shared library libgio-2.0.so.0`，直至把包 lib 目录加入
   `LD_LIBRARY_PATH` 才成功输出 `2.84.0`。

## 适用边界

OHOS/Meson 构建中，共享 Conan 依赖包提供 host 工具并被子项目
`gnome.compile_resources / gnome.compile_schemas / gnome.mkenums` 消费时；特别是依赖 recipe
只对 `.so` 重签（post-install）而未处理 `bin/` 可执行文件，且这些工具动态链接且无 RPATH。

## 最小复现命令

```sh
# 1) 单独执行失败（修复前）
$CONAN_GLIB_PKG/bin/glib-compile-resources --version
#    → Operation not permitted （code 126）

# 2) 重签 ELF 工具
llvm-objcopy --remove-section .codesign $CONAN_GLIB_PKG/bin/glib-compile-resources
binary-sign-tool sign -inFile $CONAN_GLIB_PKG/bin/glib-compile-resources \
                       -outFile $CONAN_GLIB_PKG/bin/glib-compile-resources -selfSign 1

# 3) 重签后仍缺库路径，必须设置 LD_LIBRARY_PATH
LD_LIBRARY_PATH=$CONAN_GLIB_PKG/lib $CONAN_GLIB_PKG/bin/glib-compile-resources --version
#    → 2.84.0  （成功）
```

## 诊断证据（GTK4 r86 实测）

| 检查项 | 结果 |
|---|---|
| 工具绝对路径 | `~/.conan2/p/glibd610586c02b9c/p/bin/glib-compile-resources` |
| 符号链接 | 无（普通文件） |
| 来源 / package ID | glib/2.84.0.1.1 shared（binary rev e9dea3c4…，pkg b55f7a48…） |
| 权限与可执行位 | 770（rwxrwx---） |
| 文件类型/架构 | ELF shared object, 64-bit LSB arm64, dynamic musl |
| 签名/白名单 | `.codesign` 段存在但失效；重签后恢复执行 |
| 动态依赖 | libgio-2.0.so.0, libglib-2.0.so.0, libintl.so.8, libgobject-2.0.so.0, libc.so |
| 最小复现 | 修复前 EPERM(126) → 重签+LD_LIBRARY_PATH 后 `2.84.0`(0) |

## 修复方案（消费者 recipe generate() 内综合修复）

```python
objcopy=/data/service/hnp/bin/llvm-objcopy
signer=/data/service/hnp/bin/binary-sign-tool
gbin=<glib pkg folder>/bin ; glib=<glib pkg folder>/lib
export LD_LIBRARY_PATH="$glib:$LD_LIBRARY_PATH"
for t in "$gbin"/*; do
  [ -f "$t" ] || continue
  head -c4 "$t" | grep -q $'\x7fELF' || continue     # 跳过 shebang 脚本（如 gdbus-codegen）
  $objcopy --remove-section .codesign "$t" 2>/dev/null || true
  $signer sign -inFile "$t" -outFile "$t" -selfSign 1
done
```

落地位置：GTK4 `conanfile.py` 的 `_prepend_glib_bin_to_path()`（在 `MesonToolchain.generate()`
与 ninja 运行之前），与现有 ML-0043 `.so` post-install 重签模式一致，扩展到依赖包 bin 工具。

## 验证结果

- GTK4 `conan-verify` G2（`conan create`）：**PASS** —— `gdk/gdkresources.c/h` 正常生成，包
  `gtk4/4.22.4`（shared=True）构建并安装成功。
- 鸿蒙特有测试（重写 `test_package/main.c`）：7/7 PASS，退出 0，本机（HarmonyOS aarch64）
  原生运行，验证 GTK4 版本 API 与 OHOS 仅 Broadway（无 X11/Wayland）适配事实。

## 失败条件 / 禁止事项

- **禁止**仅凭一条 `Operation not permitted`/`Permission denied` 判定 `external_blocked`；
  必须先核验工具绝对路径、来源/package ID、权限与可执行位、ELF 架构与格式、签名/白名单、
  动态依赖闭包、runner/工作目录/环境变量，并以最小复现命令重试。
- **禁止**只重签不改 `LD_LIBRARY_PATH`（或反之）：两缺陷独立叠加，缺一不可，否则被误判
  修复无效而错误回退版本。

## 查重结果

- 与 **E077**（ELF 修改后重签四步流程，post-install 阶段、针对自身产物）部分相邻；
  本条目差异：作用于**依赖包 bin 工具**、发生在 **generate()/build() 阶段**、且必须**同时**
  处理无 RPATH 的 `LD_LIBRARY_PATH` 注入，以及 pkg-config 工具变量消费链。
- 与 **E019**（LD_LIBRARY_PATH 通用设置）相邻；本条目将其与 OHOS ELF 签名失效问题组合，
  限定于 Meson `gnome.compile_resources/compile_schemas` 工具链场景。
- 结论：无完全重复条目，按新草稿提交。

## 边界与后续

- 本草稿随 GTK4 4.22.4 r87 原子范围提交（`knowledge/drafts/`）。
- 未编造知识编号/链接/审核结论；正式 promote 由主编审核后执行。