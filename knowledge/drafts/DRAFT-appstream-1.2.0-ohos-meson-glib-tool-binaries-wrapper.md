# DRAFT-appstream-1.2.0-ohos-meson-glib-tool-binaries-wrapper — meson 侧 glib 工具经 machine file [binaries] wrapper 修复

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: blocking (3) | **Category**: build-system / meson / hmdfs / toolchain / conan / ohos
> **Audience**: 所有 meson + Conan + glib 家族在 OHOS/HMDFS 上构建的项目

## 触发（trigger）

- appstream 1.2.0 OHOS 适配：meson 构建 src/ 的 `appstream.gresource.xml` 时，ninja 调用
  glib 包内 `glib-compile-resources` 生成 `as-resources.c/h`。

## 症状（symptom）

```
FAILED: [code=127] src/as-resources.c
glib-compile-resources ../src/appstream.gresource.xml ... 
Error loading shared library libgio-2.0.so.0: (needed by .../glib-compile-resources)
Error loading shared library libglib-2.0.so.0
Error loading shared library libgobject-2.0.so.0
```

早期尝试：`buildenv_info.prepend_path("LD_LIBRARY_PATH", glib_pkg/lib)` 不生效
（聚合 env 未携带）；`PATH` prepend wrapper 也不生效（ninja 直接调用 configure 期
解析出的绝对原路径）。

## 机制（root cause）

1. OHOS/HMDFS 上 conan 缓存副本从缓存路径直接 exec 已签名 ELF 受限；
2. glib-compile-resources 运行时需 LD_LIBRARY_PATH 指向 glib 包 lib
   （libglib-2.0.so.0 等），buildenv_info 的 LD_LIBRARY_PATH 实测未聚合进
   conanbuild 环境；
3. meson 在 configure 期用 find_program 把工具解析为绝对路径写入 build.ninja，
   运行时不再走 PATH——所以 PATH prepend 方案无效。

## 修复（rec）

generate() 中为 glib 包内 ELF 工具生成 wrapper（先 export LD_LIBRARY_PATH 再 exec 原
二进制），并把工具名通过 MesonToolchain `tc.binaries[工具名] = wrapper` 写入 machine
file `[binaries]`：meson find_program 优先读机器文件，configure 期解析到 wrapper，
ninja 调用 wrapper → 运行时环境正确。

```python
tools_dir = os.path.join(self.build_folder, "glib-tools")
os.makedirs(tools_dir, exist_ok=True)
for tool in ("glib-compile-resources", "glib-mkenums"):
    src = os.path.join(glib_pkg, "bin", tool)
    wrapper = os.path.join(tools_dir, tool)
    with open(wrapper, "w") as fh:
        fh.write("#!/bin/sh\n")
        fh.write(f"export LD_LIBRARY_PATH={glib_pkg}/lib:$LD_LIBRARY_PATH\n")
        fh.write(f'exec "{src}" "$@"\n')
    os.chmod(wrapper, 0o755)
    tc.binaries[tool] = wrapper
```

## 验证（verification）

conan create 中 `as-resources.c/h` 正常生成（原 FAILED code=127 消除），主库与全部
测试编译链接成功；test_package 消费者 1/1 通过。

## 适用边界 / 反例

- 纯 python 脚本工具（glib-mkenums）无动态库依赖时，可直接 PATH prepend 或同样走
  tc.binaries（本候选两者都写 wrapper，简化统一）；
- 反例：工具可从系统 PATH 正常 exec 且无动态库路径问题时不适用；
- 反例：能改 glib 配方 runenv_info 使动态库随环境注入的场景可替代（但改动依赖库，
  本方案在消费方配方内自包含）。

## 关系

- `similar_to`: DRAFT-ohos-autotools-glib-tool-inject（autotools 侧工具注入）、
  E527（gtk broadway 工具 native wrapper）
- 差异：该草稿/条目覆盖 autotools/pkg-config 机制，本候选是 **meson machine file
  [binaries] 映射**路径，且点明 PATH prepend 无效的根因。

## 证据

- 配方：`archives/a/appstream/1.2.0/conanfile.py`（generate() glib-tools 段）
- 构建日志：`archives/a/appstream/1.2.0/reports/conan-create.log`
- 台账：`archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md` 候选 3