# zlib 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | zlib |
| 版本 | 1.3.1 |
| 官网 | https://zlib.net/ |
| 源码下载 | https://zlib.net/fossils/zlib-1.3.1.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o zlib-1.3.1.tar.gz "https://zlib.net/fossils/zlib-1.3.1.tar.gz"
tar -xzf zlib-1.3.1.tar.gz
cd zlib-1.3.1
```

### 2. 配置

```bash
# ⚠️ 关键：必须设置 CFLAGS="-fPIC"，否则静态库链接到共享库会报错
CFLAGS="-fPIC -O3" ./configure --prefix=$HOME/usr/local
```

### 3. 编译

```bash
make -j$(nproc)
```

### 4. 安装

```bash
make install
```

### 5. 测试

```bash
make test
```

## ⚠️ 关键注意事项：CFLAGS="-fPIC" 必须设置

### 问题现象

如果不设置 `CFLAGS="-fPIC"`，编译 Python 时会报错：

```
ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC
>>> defined in /storage/Users/currentUser/usr/local/lib/libz.a(zutil.o)
>>> referenced by zutil.c
>>>               zutil.o:(zError) in archive /storage/Users/currentUser/usr/local/lib/libz.a
```

### 问题根因

zlib 的 configure 脚本对静态库和共享库使用不同的编译选项：

| 变量 | 用途 | 是否自动加 -fPIC |
|------|------|-----------------|
| `CFLAGS` | 静态库 (`libz.a`) | ❌ **不会自动加** |
| `SFLAGS` | 共享库 (`libz.so`) | ✅ 自动加 `-fPIC` |

zlib 的设计假设是：只有共享库需要 `-fPIC`，静态库不需要。

但在鸿蒙系统上：
- musl libc 默认使用 **BIND_NOW**（符号立即解析）
- 当静态库被链接到共享库（Python `.so`）时，静态库也必须使用 `-fPIC`

### 解决方案

```bash
# ✅ 正确方式：在 configure 命令前设置 CFLAGS
CFLAGS="-fPIC -O3" ./configure --prefix=$HOME/usr/local

# ❌ 错误方式：不设置 CFLAGS
./configure --prefix=$HOME/usr/local  # 静态库无 -fPIC，链接 Python 报错
```

### 为什么 export CFLAGS 可能无效？

1. **没有 export**：
   ```bash
   # ❌ 错误：只在当前 shell 生效，configure 是子进程
   CFLAGS="-fPIC -O3"
   ./configure
   
   # ✅ 正确：export 后子进程可继承
   export CFLAGS="-fPIC -O3"
   ./configure
   ```

2. **直接在命令行设置更可靠**：
   ```bash
   # ✅ 推荐：直接在 configure 前设置，最可靠
   CFLAGS="-fPIC -O3" ./configure --prefix=$HOME/usr/local
   ```

## 编译结果

安装后会生成以下文件：

```
$HOME/usr/local/
├── lib/
│   ├── libz.a          # 静态库（带 -fPIC）
│   ├── libz.so         -> libz.so.1.3.1
│   ├── libz.so.1       -> libz.so.1.3.1
│   └── libz.so.1.3.1   # 动态库
├── include/
│   ├── zlib.h          # 头文件
│   └── zconf.h         # 配置头文件
└── lib/pkgconfig/
    └── zlib.pc         # pkg-config 文件
```

## 兼容性说明

### ✅ 无需补丁

zlib 1.3.1 在 HarmonyOS 上可以**直接编译**，无需任何补丁修改。

configure 脚本能够自动检测：
- clang 编译器
- 共享库支持
- 系统类型和特性

### 配置检测项

configure 会自动检测以下特性：
- size_t 类型
- off64_t 类型
- fseeko 函数
- strerror 函数
- unistd.h 头文件
- stdarg.h 头文件
- vsnprintf 函数
- visibility 属性支持

## 依赖关系

### 被依赖

以下软件依赖 zlib：
- Python (_zlib 模块)
- curl
- git
- openssl
- libpng
- 以及许多其他软件

## 常见问题

### Q: 编译时找不到 zlib

确保设置了正确的环境变量：

```bash
export CFLAGS="-I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib"
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"
```

### Q: 运行时找不到 libz.so

确保库路径在搜索路径中：

```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

### Q: Python 编译报错 "recompile with -fPIC"

重新编译 zlib，确保设置 `CFLAGS="-fPIC -O3"`：

```bash
cd zlib-1.3.1
make clean
CFLAGS="-fPIC -O3" ./configure --prefix=$HOME/usr/local
make -j$(nproc)
make install
```

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.3.1 | 2024-01-23 | 当前最新稳定版 |
| 1.3   | 2023-08-18 | 安全更新 |
| 1.2.13 | 2022-10-13 | 旧稳定版 |

## 测试结果

```
zlib version 1.3.1 = 0x1310, compile flags = 0xa9
uncompress(): hello, hello!
gzread(): hello, hello!
gzgets() after gzseek:  hello!
inflate(): hello, hello!
large_inflate(): OK
after inflateSync(): hello, hello!
inflate with dictionary: hello, hello!
        *** zlib 64-bit test OK ***
```

## 参考链接

- [zlib 官方网站](https://zlib.net/)
- [zlib GitHub](https://github.com/madler/zlib)
- [zlib 文档](https://zlib.net/manual.html)