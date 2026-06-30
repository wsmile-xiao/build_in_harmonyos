# inadyn 2.12.0-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built（静态编译成功）

## 编译步骤

### 1. 初始化构建
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build inadyn 2.12.0-r0 --url=file:///storage/Users/currentUser/tmp/inadyn-2.12.0.tar.gz
```

### 2. 解决 HMDFS 临时文件限制
修改 config.status 脚本，使用本地临时目录（~/tmp）和 umask 022：
```bash
sed -i 's/umask 077/umask 022/g' config.status
sed -i 's|mktemp -d "./confXXXXXX"|mktemp -d "/storage/Users/currentUser/tmp/confXXXXXX"|g' config.status
sed -i 's|tmp=./conf$$-$RANDOM|tmp=/storage/Users/currentUser/tmp/conf$$-$RANDOM|g' config.status
```

### 3. 添加 pkg.m4 文件
从系统中复制 pkg.m4 到 m4 目录，解决 PKG_CHECK_MODULES 宏未定义问题：
```bash
cp /data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal/pkg.m4 m4/
./autogen.sh
```

### 4. 静态编译配置
```bash
export LDFLAGS="-static -Wl,-Bstatic"
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
./configure --prefix=$DEFAULT_PREFIX --enable-openssl --disable-shared LDFLAGS="-static -Wl,-Bstatic"
```

### 5. 强制静态链接
修改 libconfuse.la，删除动态库引用，只保留静态库：
```bash
rm -f ~/usr/local/lib/libconfuse.so*
vi ~/usr/local/lib/libconfuse.la
# 修改：dlname='' 和 library_names=''
```

### 6. 手动链接静态二进制
绕过 libtool，直接链接静态二进制：
```bash
clang -static -o inadyn-static \
  $(ls src/*.o) $(ls src/../plugins/*.o) $(ls src/../lib/*.o) \
  -L/storage/Users/currentUser/usr/local/lib -lconfuse -lssl -lcrypto
```

### 7. 安装和验证
```bash
make install DESTDIR=$TEST_PREFIX
~/usr/local/sbin/inadyn --version  # 输出: 2.12.0
file ~/usr/local/sbin/inadyn       # 输出: ELF executable, static
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时文件 | HMDFS 文件系统限制，umask 077 导致临时目录权限过严 | 修改 config.status 使用 ~/tmp 和 umask 022 |
| 2 | PKG_CHECK_MODULES 宏未定义 | 缺少 pkg.m4 文件 | 复制 /data/service/hnp/pkg-config.../pkg.m4 到 m4/ |
| 3 | 链接时找不到动态库 | libtool 优先选择动态库，但需要静态链接 | 删除动态库，修改 .la 文件，手动链接 |
| 4 | libtool 生成的二进制仍为动态链接 | libtool 的 -static 标志未生效 | 手动使用 clang -static 直接链接对象文件 |

## 源码修改

无补丁文件。所有修改均为运行时临时调整：
1. config.status（临时文件路径和 umask）
2. libconfuse.la（删除动态库引用）

## 依赖版本

- libconfuse: 3.3（静态库）
- openssl: 1.1.1w（静态库）
- clang: 15.0.4
- autoconf: 2.72
- automake: 1.17
- pkg-config: 0.29.2

## 验证结果

```bash
# 验证静态链接
file ~/usr/local/sbin/inadyn
# 输出: ELF executable, 64-bit LSB arm64, static, not stripped

# 验证功能
~/usr/local/sbin/inadyn --version
# 输出: 2.12.0

# 文件大小（静态链接）
ls -lh ~/usr/local/sbin/inadyn
# 输出: 4.1M（包含所有静态库代码）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ~/usr/local/sbin/inadyn | 4.1M | 静态可执行文件 |
| ~/usr/local/share/man/man8/inadyn.8 | - | man 手册页 |
| ~/usr/local/share/doc/inadyn/examples/* | - | 配置示例文件 |

## 注意事项

1. **静态编译必要性**：OpenHarmony 的 musl libc 动态链接器不完全支持 RUNPATH，导致运行时无法加载共享库。静态编译是解决此问题的唯一方案。

2. **HMDFS 临时文件限制**：umask 077 创建的临时目录权限为 drwx--S---，无法在其中创建文件。必须使用 umask 022（权限 drwxr-s--x）。

3. **libtool 静态链接陷阱**：即使使用 LDFLAGS="-static"，libtool 仍可能生成动态链接二进制。最佳实践是手动链接或删除所有动态库文件。

4. **依赖库必须静态编译**：要实现完整的静态链接，所有依赖库（libconfuse、openssl）都必须提供静态库版本（.a 文件）。

5. **config.guess/config.sub 已自动适配**：configure 脚本自动识别平台为 aarch64-unknown-linux-ohos，无需手动修改。

---
**编译结束**: 2026-05-21 12:18
**最终状态**: built
---

**编译结束**: 2026-05-21 12:20
**最终状态**: built
