# E630 — Meson sanity check 编译的 C++ 测试二进制因缺少 libc++_shared.so 运行库路径而不可运行

## 错误特征

meson setup（conan create 内）报：

```
../meson.build:1:0: ERROR: Executables created by cpp compiler /data/service/hnp/bin/clang++ are not runnable.
```

meson-log.txt 中可见：

```
Sanity check: `<build>/meson-private/sanity_check_for_cpp.exe` -> 127
stderr: Error loading shared library libc++_shared.so: (needed by ...)
-- returncode: 127
```

## 触发条件

- 构建系统: meson（`project(... )` 声明 `['c', 'cpp']` 或纯 cpp 语言）
- 阶段: configuration（meson setup / conan create 内 MesonToolchain generate + configure）
- 环境: OHOS（aarch64-linux-ohos），OHOS SDK clang++ 15

## 根因分析

OHOS SDK（ohos-sdk_26.x）中 clang++ 编译产物默认链接 `libc++_shared.so`。该库位于 SDK 的：

```
<SDK>/ohos/native/llvm/lib/aarch64-linux-ohos/libc++_shared.so
```

而 Conan profile `ci/conan/profiles/ohos-aarch64` 的 `[buildenv] LD_LIBRARY_PATH` 只覆盖 `<llvm>/lib` 根目录（该目录是 lld 依赖 libxml2.so.16 所需）。meson 对 C++ 编译器做 sanity check 时会**运行**编译出的测试二进制，加载器在 LD_LIBRARY_PATH 中找不到 `libc++_shared.so` → returncode 127 → meson 误判编译器不可运行。

另注意：meson 探测第三方头文件可能无条件执行（如 libplacebo5 的 `src/vulkan/meson.build` 即使 `-Dvulkan=disabled` 也探测 `vulkan/vulkan_core.h`）。此时优先复用 OHOS SDK sysroot 自带头文件（`<SDK>/ohos/native/sysroot/usr/include/vulkan/vulkan_core.h`），不需要为空的 3rdparty submodule 目录额外下载头文件。

## 解决方案

### 推荐方案（conanfile.py generate() 内补运行库路径）

在 conanfile.py 的 `generate()` 中，构造并 prepend SDK C++ 运行时目录到 LD_LIBRARY_PATH：

```python
def generate(self):
    # OHOS 缺 ar——同场景必修
    os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
    # meson sanity check 需加载 libc++_shared.so（SDK <llvm>/lib/aarch64-linux-ohos/ 子目录，
    # profile LD_LIBRARY_PATH 仅覆盖 <llvm>/lib 根目录）
    cpp_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
               "ohos/native/llvm/lib/aarch64-linux-ohos")
    if os.path.isdir(cpp_lib):
        cur = os.environ.get("LD_LIBRARY_PATH", "")
        if cpp_lib not in cur.split(os.pathsep):
            os.environ["LD_LIBRARY_PATH"] = cpp_lib + os.pathsep + cur
    tc = MesonToolchain(self)
    # ... 项目选项 ...
```

对于上游对第三方头文件的无条件探测（vulkan.h 等），确认 SDK sysroot 自带后无需下载 submodule。

### 禁止做法

- ❌ 仅因 `-Dvulkan=disabled` 仍报 vulkan.h 缺失就下载 Vulkan-Headers submodule——SDK sysroot 已自带，且源站下载（gh-proxy/urllib）在本机 SSL 证书不全时二次失败
- ❌ 把 LD_LIBRARY_PATH 注入共享系统前缀（R49/PF6 拦截）

## 验证

```bash
# 修复前（libplacebo5 5.264.1）
conan create ... → ../meson.build:1:0: ERROR: Executables created by cpp compiler ... are not runnable.

# 修复后：conan-verify G2 conan create 通过
ohc-run.py conan-verify libplacebo5 5.264.1
# G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
```

## 关联条目

- 相关: E481（零依赖 meson C 库 OHOS 适配，本条目侧重 C++ sanity check 运行库路径缺失）
- 相关: E501（OHOS runner 运行库环境，Makefile 场景）