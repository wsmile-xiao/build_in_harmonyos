# glib 2.88.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-04-21
- 编译器: clang (LLVM)
- 状态: success（静态库构建）

## 编译步骤
1. 下载 glib-2.88.0.tar.xz 并解压
2. 应用 4 个补丁
3. meson 配置：
```bash
meson setup builddir --prefix=$HOME/usr/local \
  -Dnls=disabled -Dlibmount=disabled -Dselinux=disabled \
  -Dtests=false -Ddefault_library=static -Doss_fuzz=disabled \
  -Dxattr=false -Ddtrace=disabled -Dsystemtap=disabled \
  -Dintrospection=disabled
```
4. `ninja -j$(nproc) -C builddir`（596/596 targets）
5. `ninja -C builddir install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | host_system == 'linux' 不匹配 harmonyos | Meson 识别 OHOS 为 'harmonyos' | 改为 `host_system in ['linux', 'harmonyos']`（3处 meson.build） |
| 2 | gjournal-private.c 未编译导致 _g_fd_is_journal undefined | 问题1 导致 | 同上修复 |
| 3 | linux/socket.h 重定义 sockaddr_storage | OHOS 内核头文件与 musl 冲突 | #define 宏重命名冲突符号（gio/gnetworkmonitornetlink.c） |
| 4 | 共享库运行时加载失败 | musl ldso 无法加载未签名 .so | 使用 `default_library=static` |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| meson.build | host_system == 'linux' → in ['linux', 'harmonyos'] | ✅ 0004 |
| glib/meson.build | 同上 | ✅ 0003 |
| gio/meson.build | 同上 | ✅ 0002 |
| gio/gnetworkmonitornetlink.c | sockaddr_storage 冲突宏保护 | ✅ 0001 |

## 依赖版本
- libffi, zlib, pcre2

## 验证结果
- pkg-config --modversion glib-2.0 = 2.88.0 ✅
- 头文件、库文件完整性验证通过 ✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| glib-latest-ohos-aarch64.tar.gz | 63.6MB | 主包（静态库） |
| glib-latest-ohos-aarch64-debug.tar.gz | - | 调试符号 |

## 注意事项
- 使用静态库构建（default_library=static）避免 OHOS 共享库签名问题
- 所有补丁均为平台适配，可考虑添加 meson 的 HarmonyOS 平台支持
