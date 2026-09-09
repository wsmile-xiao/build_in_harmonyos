# E545：OHOS python subprocess 工具链子进程动态库加载失败三变体（ninja/lld 裸名探测静默失败）

## 错误特征

```
ERROR: Could not detect Ninja v1.8.2 or newer
ERROR: Unable to detect linker for compiler ... clang -Wl,--version
Error loading shared library libc++_shared.so: (needed by .../ninja)
Error loading shared library libxml2.so.16: (needed by .../lld)
Error relocating lld: xmlFreeDoc: symbol not found
```

## 根因

OHOS 上动态链接的工具链组件（ninja、lld）在 python subprocess 子进程链路中按继承的 LD_LIBRARY_PATH 解析伴生共享库。三条故障变体同根因：

- **V1**：ninja + libc++_shared.so——桌面环境继承的 LD_LIBRARY_PATH 含应用层路径，`/data/service/hnp/bin/ninja` 加载 libc++_shared.so 失败 rc=127 无 stderr，meson 把 127 当"不可运行"静默跳过 → "Could not detect Ninja"（本地 conan create 场景）
- **V2**：lld + libxml2.so.16——OHOS SDK 的 lld 动态链接 libxml2.so.16，真机 SSH 环境自带该路径，CI worker 缺失 → `clang -Wl,--version` 拉起 lld 失败 → "Unable to detect linker"（CI 场景，三台 worker 实证）
- **V3**：裸名 PATH 解析——OHOS python subprocess 对裸名命令不做 PATH 搜索，`subprocess.run(['ninja'])` 直接 FileNotFoundError

共性：上层工具把子进程失败**静默降级为"工具不可用"**，报错完全不指向真实根因（动态库加载），极易误判为"没装工具"而放弃配方侧修复。

## 解法（配方层根治，不改框架）

1. **meson 探测（configure 前）**：MesonToolchain 生成后改写 conan_meson_native.ini 的 c/cpp 为 wrapper 脚本（wrapper 内 `export LD_LIBRARY_PATH=<SDK llvm/lib>` 后 exec 真编译器）——探测/编译/链接统一经 wrapper。⚠️ buildenv_info.prepend_path 方案已实证失效（meson 探测子进程不继承 conanbuild.sh）
2. **test_package CMake try-compile（第二暴露面）**：必须在 build() 里文件级改写 conan_toolchain.cmake 的 CMAKE_C/CXX_COMPILER 为 wrapper（conf.update 时机不可靠）
3. **ninja 专项**：`environment.define_path("NINJA", shutil.which("ninja"))` 绝对路径绕开裸名解析

## 诊断口诀

交互 shell 能跑 + 子进程报"工具不存在" = 先查动态库加载（LD_LIBRARY_PATH），再查裸名解析（NINJA/绝对路径），最后才怀疑工具本身。

## 关键教训

- 先例会随 CI 环境演进失效（pycairo 1.29.0 的 buildenv_info 方案 8/13 合入、9/4 实证已失效）
- **wrapper（脚本内 export 后 exec）是唯一不依赖环境继承机制的根治法**

## 实证

gupnp-av 0.14.5（PR !7999）七轮 CI 攻坚完整证据链：本地 V1/V3 实证；V2 在三台 worker（CI-031/037/011）实证。融合 pycairo 1.29.0（#21029）与 glib 2.84.0 先例，统一为跨构建系统（meson/cmake/autotools）通用诊断模式。
