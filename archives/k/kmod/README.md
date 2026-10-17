# kmod

Linux 内核模块管理库与命令行工具集。

## 功能概述

- **libkmod**：查询/加载/卸载内核模块的 C 库（读取 /proc/modules、/sys 与模块索引，支持 gzip/xz/zstd 压缩模块与 PKCS7 签名校验）
- **CLI 工具**：`kmod`（多路调用入口，经符号链接提供 `depmod`/`modinfo`/`insmod`/`rmmod`/`lsmod`/`modprobe`）

## OHOS 适配

- 构建系统使用 **meson**（上游主构建），`-Dmanpages=false`（无 scdoc）、`-Dzstd/xz/zlib/openssl=enabled`（全功能）
- 补丁 `0001-musl-compat.patch`：
  - OHOS musl 无 glibc 扩展 `program_invocation_name/short_name` → 以 `__progname` 初始化并取 basename
  - `get_current_dir_name()` → `getcwd(NULL, 0)` 等价回退
  - meson 安装符号链接脚本对 toybox ln 长选项容错（实际链接由配方 python 创建）
- **上游测试套件（testsuite）无法在 OHOS 运行**：需要 Linux 内核 kbuild 树构建假内核模块，且缺 GNU install/cp --archive/zstd CLI；真实 API 验证由 test_package R34 承担（kmod_new/get_dirname/new_from_name/get_name 已实测通过）
- 共享库需 OHOS codesign（配方 binary-sign-tool 重新签名）

## 依赖关系

- 编译/运行依赖：zlib、xz（liblzma）、zstd、openssl（libcrypto）

## 参考资料

- 官网/源码：https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git
- 上游版本：34（2025）
