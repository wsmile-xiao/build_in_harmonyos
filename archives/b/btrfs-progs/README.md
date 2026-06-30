# btrfs-progs

Btrfs 文件系统工具集

## 软件信息

- **名称**: btrfs-progs
- **描述**: Btrfs 文件系统管理工具，包括创建、检查、修复和调整 Btrfs 文件系统
- **主页**: https://btrfs.readthedocs.io/
- **类别**: filesystem

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 5.19.1 | built | 2026-06-16 | 旧版本，平台兼容性好 |

## 工具列表

编译成功后可用的命令：

- `mkfs.btrfs` - 创建 Btrfs 文件系统
- `btrfs` - Btrfs 文件系统管理工具
- `btrfsck` - 检查 Btrfs 文件系统
- `btrfs-image` - 创建/恢复 Btrfs 文件系统镜像
- `btrfs-map-logical` - 映射逻辑块到物理块
- `btrfstune` - 调整 Btrfs 文件系统参数

## 编译说明

### 平台兼容性

- **v5.x 系列**: 在 OHOS/musl 平台可正常编译
- **v6.x 系列**: 包含大量 Linux 内核代码和数据结构，需要完整内核用户空间兼容层，在 OHOS/musl 平台无法编译

### 编译参数

```bash
./configure --prefix=$DEFAULT_PREFIX \
  --disable-documentation \
  --disable-python \
  --disable-libudev \
  --disable-lzo \
  --disable-convert
make && make install DESTDIR=$TEST_PREFIX
```

### 已解决的问题

1. **E011**: HMDFS 文件系统 umask 权限问题
   - 修改 configure 中 `umask 077` 为 `umask 022`

2. **E007**: config.guess 无法识别 OpenHarmony 平台
   - 使用预编译的 config.guess/config.sub

3. **E051**: pthread_cancel 系统调用不可用
   - 创建 pthread-stubs.c stub 函数

## 依赖

- e2fsprogs (ext2fs/blkid/uuid)
- zstd
- lzo2 (可选)

## 注意事项

- Btrfs 文件系统需要内核支持，在 OHOS 上可能无法实际使用
- 旧版本（v5.x）工具主要用于文件系统检查和恢复场景
- 新版本（v6.x）因内核代码依赖无法编译

## 安装验证

```bash
# 查看版本
btrfs --version

# 查看帮助
btrfs --help

# 检查文件系统（需要 root 权限和内核支持）
# btrfs filesystem df /mount/point
```