# E607 — OHOS SDK ninja/cmake 依赖 libc++_shared.so，需注入 LD_LIBRARY_PATH

## 错误特征
```
ERROR: Could not detect Ninja v1.8.2 or newer        # meson setup 阶段
# ninja --version 测试需要 libc++_shared.so（修正：ninja --version）一般以验证命令为准
Error relocating /data/service/hnp/bin/cmake: _ZTISt12length_error: symbol not found
```

## 触发条件
- 工具链: OHOS SDK（/data/service/hnp/ohos-sdk.org/...）
- 阶段: configuration（meson 找 ninja）/ test_package build（cmake）
- LD_LIBRARY_PATH 未包含 `ohos/native/llvm/lib/aarch64-linux-ohos`

## 根因分析
OHOS SDK 的 ninja/cmake 二进制动态链接 libc++（libc++_shared.so 提供 C++ 运行时符号，cmake 还依赖 libc++ ABI 符号 _ZTI*）。该 .so 位于 `llvm/lib/aarch64-linux-ohos/` 子目录（不是 `llvm/lib/`）。LD_LIBRARY_PATH 缺该子目录时：
- ninja 无法加载 → meson 报 "Could not detect Ninja"
- cmake 无法加载 libc++ 符号 → "Error relocating ... symbol not found"
（与 E540 同族但变量不同：E540 是 PATH 缺可执行文件，本条是 LD_LIBRARY_PATH 缺运行库）

## 解决方案

### 推荐方案
conanfile 的构建环境（`_build_environment()`/`generate()` 注入）把
`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos`
prepend 进 `LD_LIBRARY_PATH`（`Environment.prepend_path` 或 os.environ 前缀），并确保 meson configure/compile、test_package 的子进程均继承。

### 禁止做法
- ❌ 修改系统 /data/service/hnp/bin/ninja / cmake（受保护环境目录）
- ❌ 仅注入 PATH 不注入 LD_LIBRARY_PATH（ninja 是动态库加载问题，PATH 无效）

## 验证
```bash
# 修复前
ninja --version    # Error loading shared library libc++_shared.so (rc 127)
# 修复后
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos:$LD_LIBRARY_PATH
ninja --version    # 1.13.1
```

## 适用与不适用边界
- 适用：所有在 OHOS SDK 环境下 conan create 调用 meson/ninja/cmake 的软件（libmalcontent 0.10.2 主包 + test_package 双处修复先例）
- 不适用：Linux 桌面（系统 ninja 链接系统 libstdc++/libc++ 正常）；OHOS SDK 路径变更后需同步目录

## 关联条目
- 相关（同族 OHOS 工具链路径）: E540（PATH 缺 /data/service/hnp/bin）
- 相关目录为 SDK 平台库路径的特殊化，非 E540 重复