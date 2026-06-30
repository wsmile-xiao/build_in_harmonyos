# acl 2.3.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

### 1. 依赖准备

**attr 库已安装但缺少 pkg-config 文件，需要手动创建：**

```bash
cat > $HOME/usr/local/lib/pkgconfig/attr.pc << 'EOF'
prefix=/storage/Users/currentUser/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: attr
Description: Extended Attributes library
Version: 2.5.2
Libs: -L${libdir} -lattr
Cflags: -I${includedir}
EOF
```

### 2. HMDFS 适配

设置临时目录避免 HMDFS 文件系统限制：

```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

### 3. config.sub 更新

下载最新版本支持 ohos 操作系统：

```bash
cd /storage/Users/currentUser/builds/acl-2.3.2.work
curl -L -o config.sub 'https://git.savannah.gnu.org/cgit/config.git/plain/config.sub'
curl -L -o config.guess 'https://git.savannah.gnu.org/cgit/config.git/plain/config.guess'
chmod +x config.sub config.guess
```

### 4. 编译配置

设置正确的环境变量：

```bash
export TMPDIR=$HOME/tmp
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LDFLAGS="-L$HOME/usr/local/lib"
export CFLAGS="-I$HOME/usr/local/include"

./configure --prefix=$HOME/usr/local
```

### 5. 编译和安装

```bash
make -j2
make install DESTDIR=$HOME/tmp/test-install-acl-2.3.2  # Staging 验证
make install  # 安装到本地
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 找不到 attr 库 | attr 预编译包缺少 pkg-config 文件 | 手动创建 attr.pc 文件 |
| 2 | HMDFS 无法创建临时目录 | config.status 使用 mktemp 创建嵌套目录 | 设置 TMPDIR=$HOME/tmp |
| 3 | config.sub 不识别 ohos | config.sub 版本过旧 | 下载最新版支持 ohos |
| 4 | getxattr 链接失败 | 未设置 LDFLAGS | export LDFLAGS="-L$HOME/usr/local/lib" |

## 源码修改

- 替换了 config.sub 和 config.guess 为最新版本（2026-05-17）

## 依赖版本

- attr: 2.5.2（已安装）
- gettext: 系统自带
- libtool: 2.4.7

## 验证结果

```bash
# 二进制文件验证
$ ls -lh $HOME/usr/local/bin/getfacl $HOME/usr/local/bin/setfacl
-rwxrwx--- 1 20001006 file_manager 43K 2026-06-09 17:52 /storage/Users/currentUser/usr/local/bin/getfacl
-rwxrwx--- 1 20001006 file_manager 63K 2026-06-09 17:52 /storage/Users/currentUser/usr/local/bin/setfacl

# 库文件验证
$ ls -lh $HOME/usr/local/lib/libacl.*
-rw-rw---- 1 20001006 file_manager 80522 2026-06-09 17:52 /storage/Users/currentUser/usr/local/lib/libacl.a
lrwxrwxrwx 1 20001006 file_manager    19 2026-06-09 17:52 /storage/Users/currentUser/usr/local/lib/libattr.so -> libacl.so.1.1.2302
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| getfacl | 43KB | 获取文件 ACL 工具 |
| setfacl | 63KB | 设置文件 ACL 工具 |
| chacl | 40KB | 更改文件 ACL 工具 |
| libacl.so.1.1.2302 | 64KB | ACL 运行时库 |
| libacl.a | 80KB | ACL 静态库 |

## 注意事项

1. **必须先编译 attr**：acl 依赖 attr 库，需要先编译并安装 attr
2. **HMDFS 限制**：所有 autotools 项目都需要设置 TMPDIR
3. **pkg-config 文件**：某些预编译包缺少 pkg-config 文件，需要手动创建
4. **环境变量持久化**：建议将环境变量设置写入 ~/.zshrc 或编译脚本

---
**编译结束**: 2026-06-09 17:52
**最终状态**: published
---

**编译结束**: 2026-06-10 09:55
**最终状态**: built
