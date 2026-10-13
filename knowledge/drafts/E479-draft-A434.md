# E479 — HarmonyOS 可执行文件需在最后一次 ELF 修改后重签

## 错误特征

HarmonyOS 上启动 aarch64 ELF 时返回 `Operation not permitted`，即使文件有执行权限且 `llvm-objdump -h` 能看到 `.codesign` 段。依赖包内 Qt `lrelease` 和 CMake 安装后的应用可执行文件都可能遇到此症状。

## 触发条件

- 构建系统：Conan + CMake + Qt 6
- 平台：HarmonyOS PC aarch64
- 阶段：构建工具启动或安装包运行
- 适配案例：XaoS 4.3.4 使用 `qttools/6.11.1.1` 的 `lrelease` 生成翻译文件；CMake 安装后产生 `bin/XaoS`。

## 根因分析

文件里存在 `.codesign` 段不代表当前字节已通过 HarmonyOS 的执行校验。依赖包内 Qt 工具在 Conan 缓存中带有系统拒绝的签名；对 XaoS，CMake 安装/运行路径处理后内核同样拒绝启动安装后的 ELF。XaoS 可执行文件重签名后能够执行并完成实际渲染，说明仅改 chmod 权限位不能修复此错误。

## 解决方案

### 推荐方案

1. 对 Conan 缓存中的构建工具，只复制到配方的私有 `build_folder`，再移除旧 `.codesign` 并调用 HarmonyOS `binary-sign-tool sign -selfSign 1`。不要改写 Conan 缓存。
2. 对应用二进制，在 CMake `install()` 完成、RPATH 等内容最终确定后，剥离旧签名并重新签名，再保留原可执行权限并替换文件。
3. 先确认构建工具能启动，然后在目标设备运行真实工作负载并检查其输出。

XaoS 配方据此在 `build()` 中生成 build-local `lrelease` 副本，在 `package()` 中重签最终 `bin/XaoS`。HarmonyOS 真机上的 `test_package` 最终通过 `XaoS -render` 生成并解码 160×120 Mandelbrot PNG；像素至少有 1009 个不同值。

### 禁止做法

- ❌ 只运行 `chmod +x` 或 `chmod 0755`，然后把执行权限当作签名修复。
- ❌ 在 Conan 依赖缓存中原地改写 ELF，造成配方不可复现。
- ❌ 在 RPATH 或其他 ELF 内容仍会变化时提前签名。

## 验证

```bash
llvm-objcopy --remove-section .codesign <private-ELF>
binary-sign-tool sign -inFile <private-ELF> -outFile <private-ELF>.signed -selfSign 1
chmod 0750 <private-ELF>.signed
mv <private-ELF>.signed <private-ELF>
```

在 HarmonyOS aarch64 上实际执行 ELF，并验证其输出内容；XaoS 采用 PNG chunk/zlib 解码、160×120 尺寸和非均匀像素检查。不要只以文件存在或断言进程退出码代替功能验证。

## 关联条目

- 相关：E429，说明选择含有上游所需 Qt 模块的已发布 `qtbase` provider，并覆盖传递依赖 pin。
