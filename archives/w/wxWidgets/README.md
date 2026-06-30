# wxWidgets

## 简介
wxWidgets 是一个成熟的开源跨平台 C++ 框架，提供 GUI 和其他开发功能。它允许开发者使用单一的代码库在 Windows、Mac OS X、Linux 和其他平台上编写应用程序。

## OHOS 适配

### 适配要点
1. **构建系统选择**：autotools 在 HarmonyOS 上失败（config.status 无法创建），必须使用 CMake
2. **平台检测**：需要修改 `build/cmake/toolkit.cmake`，添加 HarmonyOS/OpenHarmony 平台检测
3. **musl libc 兼容**：
   - musl libc 不支持 glibc 扩展函数（`gethostbyname_r`, `getservbyname_r` 等）
   - wxWidgets 有 fallback 机制：使用 mutex + `gethostbyname` 保证线程安全
   - 需要在源码中添加 `HAVE_GETHOSTBYNAME`, `HAVE_INET_ATON` 等宏定义
4. **类型定义**：`socklen_t` 在 HarmonyOS 上是 `unsigned int`，需要正确定义

### 已知问题
- GUI 功能目前禁用（`wxUSE_GUI=OFF`），只编译基础库和网络库
- xlocale 功能禁用（musl libc 不支持 locale 扩展函数）

### 与 Linux 的差异
- Linux 使用 glibc，支持所有 `_r` 版本的网络函数
- HarmonyOS 使用 musl libc，只支持标准 POSIX 函数

## 依赖
wxWidgets 基础库无外部依赖，内置了：
- zlib（压缩）
- PCRE（正则表达式）

## 功能验证
```bash
# 检查库文件
ls ~/usr/local/lib/libwx*.a
# 应输出：libwx_baseu-3.2.a, libwx_baseu_net-3.2.a, libwxregexu-3.2.a, libwxzlib-3.2.a

# 验证网络库符号
nm ~/usr/local/lib/libwx_baseu_net-3.2.a | grep gethostbyname
```

## 参考
- 官网：https://www.wxwidgets.org
- 源码：https://github.com/wxWidgets/wxWidgets
- 文档：https://docs.wxwidgets.org/