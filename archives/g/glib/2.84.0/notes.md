# glib v2.84.0 编译笔记

## 编译信息
- **编译日期**: 2026-05-16
- **编译器**: clang 15.0.4 + GNU ld (bfd)
- **构建系统**: meson 1.11.1 + ninja 1.13.1
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64

## 主要问题及解决方案

### 问题1: meson sanity check 与 ELF 签名冲突
- **问题**: meson 配置阶段编译测试程序需要运行，但鸿蒙要求 ELF 签名
- **解决**: 创建 clang-wrapper 脚本，编译后自动签名可执行文件

### 问题2: lld 链接器缺少 libxml2.so.16
- **问题**: lld 需要 libxml2.so.16 但无法找到
- **解决**: wrapper 使用 GNU ld (bfd) 代替 lld

### 问题3: sockaddr_storage 重复定义
- **问题**: 鸿蒙 SDK 的 linux/socket.h 和 sys/socket.h 都定义了 sockaddr_storage
- **解决**: 禁用 HAVE_LINUX_TCP_H 和 HAVE_NETLINK

### 问题4: host_system 条件不包含 HarmonyOS
- **问题**: gjournal-private.c 等文件只在 host_system == 'linux' 时编译
- **解决**: 修改 meson.build，将 `host_system == 'linux'` 改为 `host_system in ['linux', 'harmonyos']`

### 问题5: pcre2 SSL 证书问题
- **问题**: meson 无法下载 pcre2 子项目
- **解决**: 使用系统预装的 pcre2 10.47

## 补丁文件

1. **0001-disable-netlink-for-harmonyos.patch**
   - 注释掉 gnetworkmonitornetlink.c 的编译
   - 禁用 HAVE_NETLINK 定义

2. **0002-add-harmonyos-host-support.patch**
   - 修改 glib/meson.build 和 gio/meson.build
   - 添加 HarmonyOS 到 host_system 条件

## 编译命令总结

```bash
# 创建 clang-wrapper
cat > ~/tmp/bin/clang-wrapper << 'WRAPPER'
#!/usr/bin/env zsh
# ... (详见上文)
WRAPPER

chmod +x ~/tmp/bin/clang-wrapper

# 配置
export CC="clang-wrapper"
meson setup build --prefix=$DEFAULT_PREFIX --default-library=static \
  -Dselinux=disabled -Dlibmount=disabled -Dtests=false

# 编译
ninja -C build

# 安装
ninja -C build install
```

## 功能验证
- libglib-2.0.a ✅
- libgio-2.0.a ✅
- gio 二进制 ✅
- glib-compile-schemas ✅

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-05-16*
