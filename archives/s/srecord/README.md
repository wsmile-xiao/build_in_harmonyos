# SRecord

SRecord 提供 EPROM、微控制器和嵌入式系统固件加载文件的读取、转换、比较与检查工具，同时提供可供其他程序使用的 C++ 静态库。

## 功能概述

- `srec_cat`：转换、合并、裁剪和过滤 Motorola S-Record、Intel HEX 等格式。
- `srec_cmp`：比较两个加载文件表示的有效数据。
- `srec_info`：显示文件格式、地址范围和执行入口等信息。
- `lib_srecord`：提供格式解析、输出及校验算法的 C++ API。

## OHOS 适配

- 修复上游 CMake 强制将安装前缀覆盖为 `/usr` 的问题，支持框架的 `DEFAULT_PREFIX + DESTDIR` 安装模型。
- 增加 `SRECORD_BUILD_DOCUMENTATION` 开关。OHOS 构建关闭生成文档，避免依赖 Doxygen、Graphviz、Ghostscript、Groff、Netpbm、Psutils 和 Libpaper。
- 非 Windows 平台不再在安装阶段扫描并复制编译主机的运行库，防止把 libc、动态加载器及 libgcrypt 的主机版本装入软件包。
- 当前适配保留上游静态库构建方式；命令行工具运行时依赖 libgcrypt 和 libgpg-error。

## 依赖

编译依赖：

- CMake 3.22 或更高版本
- Clang/Clang++
- libgcrypt 开发头文件和库

运行依赖：

- libgcrypt
- libgpg-error
- C++ 运行库

## Conan 配方

路径：`archives/s/srecord/1.65.0/`

- `conanfile.py` / `conandata.yml`：CMake 构建，依赖 `libgcrypt/1.11.0`
- `test_package/`：`smoke_test.sh` 消费侧验证 + `MANIFEST.yml`
- `commands.json`：声明 CLI 工具（R38）

## 功能验证

- 主机侧官方 CTest：208/208 通过。
- OHOS aarch64 `conan create`：构建与打包通过；交叉主机上校验 `srec_*` 为 aarch64 ELF。
- 原生 OHOS CI worker 将执行完整 `cmake.test()`。
- 按任务约定，暂未进行真机执行、ELF 签名与预编译包安装验证。

## 参考

- 官网：https://srecord.sourceforge.net/
- 源码：https://sourceforge.net/projects/srecord/
- Homebrew 配方：https://formulae.brew.sh/formula/srecord
