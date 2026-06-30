# X.Org Server 21.1.15 编译笔记

## 编译日期
2026-05-30

## 编译环境
- OpenHarmony
- TMPDIR=/data/storage/el2/base/cache
- 编译器: clang

## 源码修改

### 1. os/utils.c
修改锁文件路径使用 TMPDIR 环境变量：
- 将硬编码的 `/tmp` 替换为 `getenv("TMPDIR")`
- 修改 `link()` 为 `rename()` 以解决跨设备链接问题

### 2. xkb/ddxLoad.c
修改 XKB 输出目录：
- `OutputDirectory()` 函数使用 TMPDIR 替代 `/tmp`

### 3. meson 配置
禁用 Unix socket 以绕过只读 /tmp/.X11-unix：
```bash
meson setup build --prefix=$PREFIX \
  -Dxvfb=true -Dxorg=false \
  -Dlisten_unix=false -Dlisten_tcp=true \
  -Dudev=false -Dglx=false
```

## 测试验证
✅ Xvfb 启动成功
✅ x11_test 测试程序连接成功
✅ 所有 5 个测试项目通过

## 关键发现
1. OpenHarmony 的 /tmp 是只读 erofs 文件系统
2. 必须使用 TMPDIR 或其他可写目录
3. Unix socket 创建失败需要禁用 listen_unix
4. XKB 配置需要完整的 xkeyboard-config

## 预编译包
- xorg-server-21.1.15-ohos-aarch64.tar.gz (8.0M)
- 包含: bin/Xvfb