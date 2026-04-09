# bzip2 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | bzip2 |
| 版本 | 1.0.8 |
| 官网 | https://sourceware.org/bzip2/ |
| 源码下载 | https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
wget -O bzip2-1.0.8.tar.gz "https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz"
tar -xzf bzip2-1.0.8.tar.gz
cd bzip2-1.0.8
```

### 2. 修改 Makefile

bzip2 没有 configure 脚本，需要直接修改 Makefile：

```bash
# 修改编译器
sed -i 's/^CC=gcc/CC=clang/' Makefile
sed -i 's/^AR=ar/AR=llvm-ar/' Makefile
sed -i 's/^RANLIB=ranlib/RANLIB=llvm-ranlib/' Makefile

# 修改安装路径
sed -i 's/^PREFIX=\/usr\/local/PREFIX=\$(HOME)\/usr\/local/' Makefile

# ⚠️ 关键：添加 -fPIC
sed -i 's/CFLAGS=-Wall -Winline -O2 -g/CFLAGS=-Wall -Winline -O2 -g -fPIC/' Makefile

# 修改共享库 Makefile
sed -i 's/^CC=gcc/CC=clang/' Makefile-libbz2_so
```

### 3. 编译

```bash
# 编译静态库和可执行文件
make -j$(nproc)

# 编译共享库
make -f Makefile-libbz2_so
```

### 4. 安装

```bash
# 安装静态库和工具
make install

# 手动安装共享库
cp libbz2.so.1.0.8 $HOME/usr/local/lib/
```

### 5. 创建符号链接

```bash
cd $HOME/usr/local/lib

# ⚠️ 注意：鸿蒙的 ln -sf 有 bug，必须先删除再创建
/bin/rm -f libbz2.so libbz2.so.1 libbz2.so.1.0
/bin/ln -s libbz2.so.1.0.8 libbz2.so.1.0
/bin/ln -s libbz2.so.1.0.8 libbz2.so.1
/bin/ln -s libbz2.so.1.0.8 libbz2.so
```

## ⚠️ 关键注意事项

### 1. CFLAGS 必须添加 -fPIC

bzip2 的 Makefile 默认不包含 `-fPIC`，但在鸿蒙系统上静态库被链接到共享库时必须使用 `-fPIC`：

```bash
# ❌ 错误：不添加 -fPIC
make  # 静态库无 -fPIC，链接 Python 报错

# ✅ 正确：修改 Makefile 添加 -fPIC
sed -i 's/CFLAGS=-Wall -Winline -O2 -g/CFLAGS=-Wall -Winline -O2 -g -fPIC/' Makefile
make
```

### 2. 鸿蒙系统 ln -sf 有 bug

鸿蒙系统的 `ln -sf` 会创建带随机后缀的文件，而不是覆盖现有符号链接：

```bash
# ❌ 错误：ln -sf 会创建 libbz2.so_abc123 这样的文件
ln -sf libbz2.so.1.0.8 libbz2.so

# ✅ 正确：先删除再创建
/bin/rm -f libbz2.so
/bin/ln -s libbz2.so.1.0.8 libbz2.so
```

### 3. 共享库需要单独编译

bzip2 的默认 Makefile 只编译静态库，需要使用 `Makefile-libbz2_so` 来编译共享库：

```bash
# 静态库
make

# 共享库（需要单独编译）
make -f Makefile-libbz2_so
```

## 编译结果

安装后会生成以下文件：

```
$HOME/usr/local/
├── lib/
│   ├── libbz2.a          # 静态库（带 -fPIC）
│   ├── libbz2.so         -> libbz2.so.1.0.8
│   ├── libbz2.so.1       -> libbz2.so.1.0.8
│   ├── libbz2.so.1.0     -> libbz2.so.1.0.8
│   └── libbz2.so.1.0.8   # 动态库
├── include/
│   └── bzlib.h           # 头文件
└── bin/
    ├── bzip2             # 压缩工具
    ├── bunzip2           -> bzip2
    ├── bzcat             -> bzip2
    ├── bzip2recover      # 恢复工具
    ├── bzgrep            # 搜索工具
    ├── bzmore            # 查看工具
    └── bzdiff            # 比较工具
```

## 依赖关系

### 被依赖

以下软件依赖 bzip2：
- Python (_bz2 模块)
- tar（.tar.bz2 格式）
- dpkg
- rpm
- 以及许多其他压缩工具

## 常见问题

### Q: 编译时找不到编译器

确保 clang 在 PATH 中：

```bash
which clang
# 应该输出: /data/service/hnp/bin/clang
```

### Q: Python 编译报错 "recompile with -fPIC"

重新编译 bzip2，确保修改了 Makefile 中的 CFLAGS：

```bash
cd bzip2-1.0.8
make clean
sed -i 's/CFLAGS=-Wall -Winline -O2 -g/CFLAGS=-Wall -Winline -O2 -g -fPIC/' Makefile
make -j$(nproc)
make install
```

### Q: 符号链接变成带后缀的文件

这是鸿蒙系统 `ln -sf` 的 bug，需要先删除再创建：

```bash
/bin/rm -f libbz2.so
/bin/ln -s libbz2.so.1.0.8 libbz2.so
```

### Q: 运行时找不到 libbz2.so

确保库路径在搜索路径中：

```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

## 验证编译结果

```bash
# 检查安装的文件
ls -la $HOME/usr/local/lib/libbz2*
ls -la $HOME/usr/local/include/bzlib.h

# 测试压缩功能
echo "test" > test.txt
$HOME/usr/local/bin/bzip2 -z test.txt
$HOME/usr/local/bin/bzip2 -d test.txt.bz2
cat test.txt

# 测试库链接
cat > test_bz2.c << 'EOF'
#include <stdio.h>
#include <bzlib.h>
int main() {
    printf("bzip2 version: %s\n", BZ2_bzlibVersion());
    return 0;
}
EOF
clang -o test_bz2 -Wl,-rpath,$HOME/usr/local/lib test_bz2.c -L$HOME/usr/local/lib -lbz2
./test_bz2
# 输出: bzip2 version: 1.0.8, 13-Jul-2019
```

## 兼容性说明

### ✅ 无需补丁

bzip2 1.0.8 在 HarmonyOS 上可以**直接编译**，无需任何补丁修改。

只需修改 Makefile 中的编译器设置和添加 `-fPIC` 选项即可。

### 构建系统特点

bzip2 使用简单的 Makefile，不使用 autotools 或 cmake：

| 特点 | 说明 |
|------|------|
| 配置方式 | 直接修改 Makefile |
| 编译器设置 | CC=, AR=, RANLIB= |
| 安装路径 | PREFIX= |
| 共享库 | 需要单独使用 Makefile-libbz2_so |

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.8 | 2019-07-13 | 当前最新稳定版 |
| 1.0.7 | 2019-06-27 | 安全更新 |
| 1.0.6 | 2010-09-20 | 旧稳定版 |

## 参考资料

- bzip2 官方网站：https://sourceware.org/bzip2/
- bzip2 手册：https://sourceware.org/bzip2/manual/manual.html