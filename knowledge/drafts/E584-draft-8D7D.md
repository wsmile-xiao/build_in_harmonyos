# E584 — meson C++ sanity-check 探针运行 rc=127（libc++_shared.so 缺失）：generate() 注入 OHOS SDK aarch64-linux-ohos 到 LD_LIBRARY_PATH

## 错误特征

conan create（meson 构建、项目声明 `['cpp','c']`）在 setup 阶段失败：

```
../meson.build:1:0: ERROR: Executables created by cpp compiler /data/service/hnp/bin/clang++ are not runnable.
```

meson-log.txt 中 C 探针（sanity_check_for_c.exe）rc=0 通过，C++ 探针（sanity_check_for_cpp.exe）rc=127：

```
Error loading shared library libc++_shared.so: (needed by .../sanity_check_for_cpp.exe)
```

## 触发条件

- 构建系统: meson，且项目语言含 C++（`project('...', ['cpp','c'])`）
- 阶段: configuration（meson setup / sanity check）
- 平台: OHOS（aarch64），conan create 走 ohos-aarch64 profile

## 根因分析

meson 对含 C++ 的项目在 setup 阶段编译并运行 C++ sanity check 探针。探针由 clang++ 链接，动态依赖 `libc++_shared.so`。该库位于 OHOS SDK 的 `llvm/lib/aarch64-linux-ohos/` 子目录；而 ohos-aarch64 profile 的 LD_LIBRARY_PATH 只前置了 `llvm/lib`（为 lld 解析 libxml2.so.16 而设），未包含 `aarch64-linux-ohos` 子目录 → 探针运行时动态加载器找不到 libc++_shared.so，以 rc=127 退出，meson 判定 "Executables ... not runnable"。

注意与 DRAFT-8960-libei 区分：libei 是 meson 探测 ninja 二进制失败（ninja 本身依赖 libc++_shared.so 且 LD_LIBRARY_PATH 有空格污染路径项）；本条目是 meson 自编探针链接 libc++_shared.so 且缺失 SDK 子目录，根因与修复均不同。

## 解决方案

### 推荐方案

在 conanfile.py `generate()` 中用 Environment + save_script 注入 SDK 子目录到 LD_LIBRARY_PATH（ast/2020.0.0 先例模式），使其进入 aggregated conanbuild 环境并被 meson 子进程继承：

```python
import glob
import os
from conan.tools.env import Environment

def generate(self):
    ...
    if self.settings.os == "OHOS":
        sdk_root = os.environ.get("OHOS_SDK_ROOT", "/data/service/hnp/ohos-sdk.org")
        sdk_libs = sorted(glob.glob(os.path.join(
            sdk_root, "*/ohos/native/llvm/lib/aarch64-linux-ohos")))
        if not sdk_libs:
            self.output.warning(
                "turnstile: OHOS SDK libc++ dir not found under %s; "
                "meson C++ sanity check may fail (LD_LIBRARY_PATH not "
                "extended). Set OHOS_SDK_ROOT if the SDK lives elsewhere." % sdk_root)
        else:
            env = Environment()
            for sdk_lib in sdk_libs:
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            env.vars(self).save_script("xxx_sdk_lib")
```

要点：
- SDK 根目录由 OHOS_SDK_ROOT 环境变量驱动（无则回退默认安装前缀），版本段用 glob 匹配，SDK 升级不失效
- `save_script` 生成的环境脚本被 conan 聚合进 conanbuild 环境，meson（含探针子进程）能继承
- SDK 目录未找到时显式 warning，避免静默失败难排查

### 禁止做法

- ❌ 不要用 `self.buildenv_info.append_path`（conan 2.29 实测不写入 aggregated env，meson 子进程取不到）
- ❌ 不要在 build() 里临时 `os.environ` 修改后依赖 Meson.configure()（内部以 conanbuild 环境运行，会覆盖）

## 验证

```bash
# 修复前：G2 FAIL（sanity_check_for_cpp.exe rc=127，libc++_shared.so 找不到）
conan create archives/t/turnstile/0.1.11 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 修复后：G2 PASS（meson setup 探针通过，meson.build 正常配置）
```

实证：turnstile 0.1.11（2026-09-21）：修复前 conan-verify G2 FAIL 报 "Executables created by cpp compiler ... not runnable"（日志含 rc=127 + Error loading shared library libc++_shared.so）；generate() 注入 SDK `llvm/lib/aarch64-linux-ohos` 后 conan-verify G2 PASS（G0-G4 + L2/L4/L5 全绿）。

## 适用边界

- 适用：meson 构建、含 C++ 语言、OHOS/aarch64、conan create 环境
- 不适用：纯 C 项目（无 C++ 探针）、非 OHOS 平台、其他构建系统（CMake 由 CMakeToolchain 处理）

## 关联条目

- similar_to: DRAFT-8960-libei（同 libc++_shared rc=127 症状，但触发/根因/修复不同：ninja 探测 vs sanity probe；/system/lib64 空格污染 vs SDK aarch64-linux-ohos 子目录缺失）
- similar_to: E132（同为 OHOS SDK 库路径未入 LD_LIBRARY_PATH 导致运行时加载失败；差异：E132 是 lld 链接器缺 libxml2.so.16（需 llvm/lib），本条是 meson C++ 探针缺 libc++_shared.so（需 llvm/lib/aarch64-linux-ohos），缺失库与注入目录不同）
- 参考先例: archives/a/ast/2020.0.0/conanfile.py（Environment+save_script 注入模式）、archives/t/turnstile/0.1.11/conanfile.py（本条目落地实现）
