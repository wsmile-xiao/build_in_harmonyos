# scudo-malloc

SCUDO standalone memory allocator from LLVM compiler-rt.

## 软件信息

- **官方网站**: https://llvm.org/
- **源码地址**: LLVM compiler-rt subproject (https://github.com/llvm/llvm-project)
- **编译版本**: 19.1.6
- **编译状态**: built

## 功能介绍

scudo-malloc 是 LLVM compiler-rt 中的 SCUDO（Sanitizer Combined Allocator）standalone 内存分配器：
- 提供安全的内存分配功能（防堆溢出、防双重释放）
- 支持静态库和动态库两种形式
- 替代系统 malloc，提供额外安全保护

## 编译历史

| 版本 | 编译日期 | 状态 | 补丁数 |
|------|---------|------|--------|
| 19.1.6 | 2026-06-08 | built | 0 |

详见各版本目录下的 `manifest.yaml` 和 `notes.md`。

## 已知平台适配问题

1. **CMAKE_SYSTEM_NAME**: 需设置为 Linux 才能在 OHOS 上编译（OHOS 检测会导致编译失败）
2. **pthread_cancel**: musl 不支持 pthread_cancel syscall，scudo 核心功能可能受影响
3. **mremap syscall**: OHOS 不支持 mremap，可能影响内存重分配功能
4. **动态库签名**: OHOS ELF 签名工具不支持库文件签名，动态库无法执行

## 安装方式

预编译包：`scudo-malloc-19.1.6-ohos-aarch64.tar.gz`（1.1MB）

产物内容：
- `lib/linux/libclang_rt.scudo_standalone-aarch64.a`（静态库，推荐使用）
- `lib/linux/libclang_rt.scudo_standalone_cxx-aarch64.a`（C++静态库）

安装方法：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- scudo-malloc 19.1.6
```

验证安装：
```bash
ls ~/usr/local/lib/linux/libclang_rt.scudo_standalone-aarch64.a
```

## 注意事项

- **推荐使用静态库**：动态库未签名，在 OHOS 上无法执行
- **功能限制**：pthread_cancel 和 mremap syscall 不可用，需在实际环境测试
- **构建系统**：需要完整的 LLVM 源码树，不能单独编译 compiler-rt
- **配置参数**：`-DCMAKE_SYSTEM_NAME=Linux` 是必需的绕过方案