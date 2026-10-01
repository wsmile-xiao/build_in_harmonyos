# FEX-Emu

FEX-Emu 是一个面向 AArch64 Linux 的**用户态 x86 / x86-64 模拟器**：它把 guest x86 指令翻译成
自有的 SSA 中间表示（IR），再由即时编译器（JIT）生成 AArch64 机器码执行，等价于 qemu-user /
box64 这一类动态二进制重编译器，但专注于指令级重编译与宿主 ABI 的紧耦合。

- 上游仓库：https://github.com/FEX-Emu/FEX
- 官网：https://fex-emu.com/
- 许可证：MIT

## HarmonyOS PC 适配要点

本包提供 FEX-Emu `2608` 月度发布版在 HarmonyOS PC（AArch64）上的适配与构建。

1. **平台放行**：上游 `CMakeLists.txt` 只接受 `Linux` 与 `Windows` 两种 `CMAKE_SYSTEM_NAME`，
   而 OHOS 的 Conan 工具链会设置 `CMAKE_SYSTEM_NAME=HarmonyOS`，因此补丁放行 HarmonyOS 三元组。
2. **libc++ 缺口补齐**：OHOS SDK 自带的 libc++（LLVM 15.0.4）**没有** C++17 的
   `<memory_resource>`（`std::pmr`）与 C++20 的 `std::atomic_ref`，且默认隐藏 C++20 ranges 算法。
   本包通过 `_LIBCPP_ENABLE_EXPERIMENTAL` 打开 ranges，并提供 `std::atomic_ref` / `std::pmr`
   两个可移植性 shim 头（仅在工具链缺失时生效，其它平台自动透传）。
3. **子模块自举**：上游 tag 的源码归档不含 git 子模块，构建脚本按 FEX-2608 tag 记录的提交
   逐个拉取需要的子模块（vixl / fmt / xxhash / range-v3 / unordered_dense / rpmalloc /
   Catch2 / drm-headers / cpp-optparse），并做 SHA256 校验。
4. **构建裁剪**：`FEXConfig`（Qt 前端）与 glibc 分配器 interposition 在 OHOS 上不适用，
   按需关闭；核心 JIT、Linux syscall 模拟、ASM 回归测试与自带单测保持开启。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| nasm | 2.16.03 | 仅构建期需要，用于汇编 FEXCore 的 x86-64 ASM 回归测试 |

第三方 C/C++ 依赖（fmt、vixl、range-v3 等）以源码子模块形式内嵌，不依赖制品仓。

## 功能验证

```bash
FEX --help
FEXGetConfig --help
```

## 参考

- [FEX-Emu 官网](https://fex-emu.com/)
- [源码仓库](https://github.com/FEX-Emu/FEX)
- [FEX-2608 发布说明](https://fex-emu.com/FEX-2608/)
