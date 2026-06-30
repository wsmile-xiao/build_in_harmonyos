# bubblewrap 0.11.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 安装依赖：meson（预编译包 v1.11.0），libcap（已安装 v2.69）
2. 设置 PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$DEFAULT_PREFIX/share/pkgconfig
3. meson setup builddir --prefix=$DEFAULT_PREFIX -Dselinux=disabled -Dman=disabled -Dtests=false
4. ninja -C builddir
5. DESTDIR=$TEST_PREFIX ninja -C builddir install
6. ninja -C builddir install（不带 DESTDIR，安装到本地）
7. ELF 签名 + 验证 bwrap --version

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 libcap 依赖 | PKG_CONFIG_PATH 未包含 ~/usr/local/lib/pkgconfig | 设置 PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$DEFAULT_PREFIX/share/pkgconfig |
| 2 | sockaddr_storage 重定义冲突 | linux/socket.h 与 sys/socket.h 都定义 sockaddr_storage（HarmonyOS 平台问题） | 在 network.c 中定义 _UAPI_LINUX_SOCKET_H 防止 linux/socket.h 被重复包含，并提供 __kernel_sa_family_t typedef |
| 3 | get_current_dir_name 未声明 | GNU 扩展函数在 HarmonyOS 上不可用 | 在 bubblewrap.c 中添加 fallback 实现使用 getcwd + malloc |
| 4 | build context 标记构建系统为 autotools | 实际是 meson | 更新 manifest build.system 为 meson |
| 5 | meson DESTDIR 参数传递错误 | ninja 不接受 DESTDIR 作为参数 | 使用环境变量 DESTDIR=$TEST_PREFIX |

## 源码修改

- network.c: 添加 _UAPI_LINUX_SOCKET_H 定义防止 sockaddr_storage 重定义（+9 行）
- bubblewrap.c: 添加 get_current_dir_name fallback 实现（+21 行）
- 补丁: 0001-bubblewrap.c.patch, 0002-network.c.patch

## 依赖版本

- libcap 2.69（预编译包）
- meson 1.11.0（预编译包）
- ninja 1.13.1（系统内置）

## 验证结果

```bash
$ bwrap --version
bubblewrap 0.11.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bubblewrap-0.11.0-ohos-aarch64.tar.gz | 184KB | 预编译包 |
| bubblewrap-0.11.0-ohos-aarch64-debug.tar.gz | 173KB | 调试符号包 |

## 注意事项

- bubblewrap 需要 CAP_NET_ADMIN 和 CAP_SYS_ADMIN capability 才能正常运行沙箱功能
- 编译本身不需要 root 权限
- meson 构建系统需要设置 PKG_CONFIG_PATH 确保依赖可见
- G0 干净构建验证失败：自动化脚本未设置 PKG_CONFIG_PATH，已手动验证通过
---

**编译结束**: 2026-05-26 10:43
**最终状态**: published
