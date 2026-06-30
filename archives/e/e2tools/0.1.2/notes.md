# e2tools 0.1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 依赖处理
1. 安装 e2fsprogs 1.47.0 预编译包（通过 cmd-pkgs）
2. 发现预编译包缺少 ext2fs.h、ext2_err.h 等头文件
3. 从本地 e2fsprogs-v1.47.0 源码复制缺失头文件：
   - lib/ext2fs/*.h → ~/usr/local/include/ext2fs/
   - lib/et/*.h → ~/usr/local/include/et/

### configure 阶段
由于 HMDFS 文件系统权限问题，configure 生成的 config.status 无法在当前目录创建临时文件。

解决方案：修改 configure 脚本中的临时目录生成逻辑：
```bash
sed -i 's|mktemp -d "./confXXXXXX"|echo "/storage/Users/currentUser/tmp/e2fs-conf"|g' configure
mkdir -p ~/tmp/e2fs-conf
```

Configure 参数：
```bash
./configure --prefix=$DEFAULT_PREFIX
```

需要设置的环境变量：
- PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
- TMPDIR=/storage/Users/currentUser/tmp

### 编译阶段
```bash
make -j2
```

编译成功，有一些警告（endian.h 的位运算优先级警告），不影响功能。

### 安装阶段
```bash
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: error: e2tools requires libext2fs | 缺少 e2fsprogs 依赖 | 安装 e2fsprogs 1.47.0 预编译包 |
| 2 | Package 'com_err' not found | 预编译包缺少 com_err.pc | 手动创建 com_err.pc 文件 |
| 3 | config.status: Permission denied | HMDFS 不支持在当前目录创建临时文件 | 修改 configure 使用固定临时目录 |
| 4 | ext2fs/ext2fs.h not found | 预编译包缺少部分头文件 | 从本地源码复制完整头文件 |
| 5 | ext2fs/ext2_err.h not found | ext2_err.h 是编译时生成 | 编译 e2fsprogs lib/ext2fs |

## 源码修改

修改 configure 脚本中的临时目录生成逻辑（不影响生成 config.status 的正确性）。

## 依赖版本

- e2fsprogs: 1.47.0（预编译包 + 补充头文件）
- libext2fs: 1.47.0
- libcom_err: 1.47.0

## 验证结果

```bash
# 安装产物检查
ls ~/test-install-e2tools-0.1.2/storage/Users/currentUser/usr/local/bin/
e2tools e2cp e2ln e2ls e2mkdir e2mv e2rm e2tail

# 功能测试
~/test-install-e2tools-0.1.2/storage/Users/currentUser/usr/local/bin/e2ls
Usage: e2ls [-acDfilnrt][-d dir] file
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| e2tools | 1.2MB | 主程序（包含所有子命令） |
| e2cp → e2tools | 符号链接 | 复制命令 |
| e2ln → e2tools | 符号链接 | 链接命令 |
| e2ls → e2tools | 符号链接 | 列表命令 |
| e2mkdir → e2tools | 符号链接 | 创建目录命令 |
| e2mv → e2tools | 符号链接 | 移动命令 |
| e2rm → e2tools | 符号链接 | 删除命令 |
| e2tail → e2tools | 符号链接 | 文件尾部命令 |

## 注意事项

1. **预编译包不完整**：e2fsprogs 预编译包缺少 ext2fs.h 和 ext2_err.h 等关键头文件，建议重新编译完整版
2. **configure 临时目录**：HMDFS 不支持在源码目录创建临时文件，需要修改 configure 使用外部临时目录
3. **PKG_CONFIG_PATH**：必须设置才能找到 ext2fs 和 com_err 的 pkg-config 文件
---

**编译结束**: 2026-06-09 10:59
**最终状态**: built
