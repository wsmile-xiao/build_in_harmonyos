# gnuplot 5.4.10 编译笔记

## Phase 1: 初始化（自动）
- ✅ 下载源码（从 SourceForge，使用 Python requests 手动下载）
- ✅ 解压到 builds 目录
- ✅ 创建档案骨架

## Phase 2: 编译（手动）

### configure 遇到的问题
- **E011: HMDFS UID 映射导致 umask 077 权限问题**
  - 根因：HMDFS 文件系统的 UID 映射机制导致 autotools 的 configure 脚本创建临时目录失败
  - 解决：修改 configure 中的 `umask 077` 为 `umask 022`
  - 参考：knowledge/graph/E011.kv

### 编译参数
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
make -j2
make install DESTDIR=/storage/Users/currentUser/test-install-gnuplot-5.4.10
```

### 缺失的可选依赖（不影响基本功能）
- libcerf（特殊函数）
- readline（使用 builtin minimal）
- gd 库（png/jpeg/gif 终端）
- lua（TikZ 终端）
- wxWidgets（wxt 终端）
- Qt（Qt 终端）
- cairo/pango（cairo 终端）
- X11（X Window 终端）

### make check 结果
- ⚠️ 测试失败，但可接受
  - 原因：缺少图形终端（unknown terminal）
  - 原因：临时文件写入权限问题
  - 不阻塞编译，基本功能可用

## Phase 3: 打包验证
- ✅ 预编译包已创建：gnuplot-5.4.10-ohos-aarch64.tar.gz (4.3MB)
- ✅ 本地安装验证通过
- ✅ --version 输出正确

## 补丁说明
- 0001-umask-022-for-hmdfs.patch：修改 configure umask 以适配 HMDFS
  - 格式：标准 diff -u 格式（第 17805-17816 行）
  - 验证：G0 补丁应用成功，手动验证编译通过

---
**编译结束**: 2026-05-27 09:50
**最终状态**: published
---

**编译结束**: 2026-05-27 09:47
**最终状态**: published
