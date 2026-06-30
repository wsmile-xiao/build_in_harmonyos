# libproxy 0.5.12 编译笔记

## 编译日期
2026-05-22

## 构建系统
Meson + Ninja

## 配置选项
- `--prefix=/storage/Users/currentUser/usr/local`
- `-Dcurl=false`（禁用 curl 支持）
- `-Ddocs=false`（禁用文档生成）
- `-Dtests=false`（禁用测试）
- `-Dconfig-gnome=false`
- `-Dconfig-kde=false`
- `-Dconfig-xdp=false`
- `-Dpacrunner-duktape=false`
- `-Dvapi=false`
- `-Dintrospection=false`
- `-Drelease=true`

## 依赖
- glib-2.0 >= 2.71.3（已满足：2.88.0）
- gio-2.0 >= 2.71.3（已满足：2.88.0）

## 遇到的问题

### 1. 下载失败
- **问题**：Savannah 下载服务器的 SSL 证书验证失败
- **解决**：使用 git clone 从 GitHub 获取源码

### 2. Ninja 构建权限问题
- **问题**：ninja 在检查依赖时无法 stat libz.so 文件
- **原因**：libz.so 符号链接的目标文件（libz.so.1.sdk）可能存在权限限制
- **解决**：修改符号链接指向 libz.so.1.3.1，并手动执行编译和链接命令

### 3. 链接时使用静态库导致的 PIC 错误
- **问题**：libz.a 不是 PIC 编译，无法用于共享库
- **解决**：使用 libz.so.1.3.1 的完整路径进行链接

### 4. musl 动态链接器不支持 RUNPATH
- **问题**：proxy 工具使用 musl 链接器，不支持 RUNPATH，无法找到 libproxy.so
- **尝试解决**：使用 patchelf 修改 RPATH，但遇到权限限制
- **状态**：库文件编译成功，但 proxy 工具无法独立运行

### 5. ELF 签名
- **问题**：鸿蒙系统要求所有可执行的 ELF 文件必须签名
- **解决**：使用 `ohc-run.py sign-elf --batch` 进行批量签名

## 构建产物
- `libproxy.so.0.5.12`（27KB）
- `libpxbackend-1.0.so`（11MB，包含静态链接的 glib）
- `proxy` 工具（23KB，无法独立运行）

## 平台限制记录
- musl 动态链接器不支持 RUNPATH，只支持 RPATH
- patchelf 在修改已签名的 ELF 文件时遇到权限限制
- 某些符号链接目标文件存在访问权限限制

## RUNPATH 修复（2026-05-22 第二轮）
- **问题**: meson 默认使用 RUNPATH，但 musl 动态链接器不支持
- **解决方案**: 修改 meson.build 文件添加 `-Wl,--disable-new-dtags` 链接参数强制使用 RPATH
- **修改文件**:
  - src/backend/meson.build: 添加 rpath_link_args
  - src/libproxy/meson.build: 添加 rpath_link_args
  - src/tools/meson.build: 添加 link_args + install_rpath 设置正确的绝对路径 RPATH
- **结果**: proxy 工具现在使用 RPATH `/storage/Users/currentUser/usr/local/lib:/storage/Users/currentUser/usr/local/lib/libproxy`
- **质量门禁**: G1-G4 全部通过
- **预编译包**: libproxy-0.5.12-ohos-aarch64.tar.gz (7.5MB) + debug.tar.gz (8.3MB)

## 编译结束
**最终状态**: published（所有门禁通过，预编译包已生成）
---

**编译结束**: 2026-05-22 12:10
**最终状态**: published
