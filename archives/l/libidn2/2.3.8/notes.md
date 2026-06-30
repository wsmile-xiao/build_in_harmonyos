# libidn2 2.3.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤

标准 autotools 构建流程：

```bash
# 1. 配置
./configure --prefix=/data/data/com.example.harmonyapp/files/usr/local

# 2. 编译
make -j2

# 3. 安装
make install DESTDIR=/path/to/staging

# 4. 打包预编译包
# 生成 libidn2-2.3.8-ohos-aarch64.tar.gz
```

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libunistring | 1.4.2 | Unicode 字符串处理库（cmd-pkgs 预编译包） |

## 重新编译记录（2026-05-20）

### 问题：动态库无法加载
- OpenHarmony 的 musl 动态链接器有安全限制
- musl 只从预配置的系统目录加载动态库
- 用户目录 ~/usr/local/lib 不在 musl 搜索路径中
- LD_LIBRARY_PATH、RUNPATH/RPATH、LD_PRELOAD 都不起作用

### 解决方案：完全静态链接
1. 安装 libunistring 1.4.2 预编译包（cmd-pkgs）
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libunistring 1.4.2
   ```
2. 创建 rpl_free.c 提供 gnulib 替换符号
   ```c
   void rpl_free(void *ptr) { free(ptr); }
   void libunistring_rpl_free(void *ptr) { free(ptr); }
   ```
3. 静态链接编译 idn2-static：
   ```bash
   clang -o idn2-static -I~/usr/local/include -static \
       simple_idn2.c rpl_free.o \
       ~/usr/local/lib/libidn2.a \
       ~/usr/local/lib/libunistring.a
   ```

### 功能验证：✓ PASS
```bash
$ ~/usr/local/bin/idn2 --version
idn2 (libidn2) 2.3.8

$ echo "测试.中国" | ~/usr/local/bin/idn2
xn--0zwm56d.xn--fiqs8s

$ echo "日本.jp" | ~/usr/local/bin/idn2
xn--wgv71a.jp
```

### 最终产物
- `~/usr/local/bin/idn2-static` (1.4MB) - 静态链接可执行文件
- `~/usr/local/bin/idn2` → idn2-static (符号链接)

### 限制说明
- 动态库只能从系统目录加载（用户环境下不可用）
- 静态链接是用户环境下唯一可行的方案
- 其他需要使用 libidn2 的程序也需要静态链接

## 知识提取记录

### 新发现的平台限制：musl 动态链接器安全限制
- **分类**: platform-limitation
- **严重级别**: 🔴 4（影响所有动态链接的软件）
- **现象**: LD_LIBRARY_PATH/RUNPATH/LD_PRELOAD 不生效
- **根因**: musl 只从预配置的系统目录加载动态库
- **解决方案**: 采用静态链接方式编译可执行文件