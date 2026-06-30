# E103: argp.h 头文件缺失

## 错误特征

编译时出现头文件缺失错误：
```
fatal error: 'argp.h' file not found
 #include <argp.h>
          ^~~~~~~
```

## 触发条件
- 构建系统: Makefile / autotools
- 阶段: compilation（编译阶段）
- 项目类型: 使用 GNU argp 进行命令行参数解析的项目

## 根因分析

OpenHarmony 系统缺少 GNU argp.h 头文件。argp.h 是 GNU C 库（glibc）的一部分，用于命令行参数解析。

OpenHarmony 使用 musl libc 而非 glibc，因此不包含 argp.h。需要额外安装 argp-standalone 库来提供此头文件和静态库。

## 解决方案

### 方案 A：安装预编译包（推荐）

安装 argp-standalone 预编译包：

```bash
# 方案 1: 如果有预编译包
curl -k -LO https://example.com/argp-standalone-1.5.0-ohos-aarch64.tar.gz
tar -xzf argp-standalone-1.5.0-ohos-aarch64.tar.gz -C ~/usr/local

# 方案 2: 手动安装头文件和库文件
# 头文件
cp argp.h ~/usr/local/include/
cp argp-fmtstream.h ~/usr/local/include/

# 静态库
cp libargp.a ~/usr/local/lib/
```

安装后的文件结构：
```
~/usr/local/
├── include/
│   ├── argp.h
│   └── argp-fmtstream.h
└── lib/
    └── libargp.a
```

### 方案 B：从源码编译

从源码编译 argp-standalone：

```bash
cd ~/tmp/builds
curl -k -LO https://github.com/argp-standalone/argp-standalone/archive/refs/tags/1.5.0.tar.gz
tar -xzf 1.5.0.tar.gz
cd argp-standalone-1.5.0

./configure --prefix=$HOME/usr/local
make
make install
```

### 禁止做法
- ❌ 不要尝试使用 `apt-get install libargp-dev`（OpenHarmony 不是标准 Linux 发行版）
- ❌ 不要尝试使用 `yum install argp-standalone`（OpenHarmony 不支持 yum）

## 验证

安装后验证：
```bash
# 检查头文件是否存在
test -f ~/usr/local/include/argp.h && echo "argp.h exists" || echo "argp.h missing"

# 检查库文件是否存在
test -f ~/usr/local/lib/libargp.a && echo "libargp.a exists" || echo "libargp.a missing"

# 编译测试
echo '#include <argp.h>' | clang++ -I~/usr/local/include -c -x c++ - -o /dev/null
```

## 编译时使用

编译依赖 argp.h 的项目时，需要指定头文件和库路径：

```bash
# 编译时添加包含路径
clang++ -I~/usr/local/include -c source.cpp

# 链接时添加库路径和库名
clang++ -L~/usr/local/lib -o binary source.o -largp
```

或修改 Makefile：
```makefile
CXXFLAGS += -I$(HOME)/usr/local/include
LDFLAGS += -L$(HOME)/usr/local/lib
LIBS += -largp
```

## 关联条目
- 相关: E001 (glibc 头文件缺失), E002 (musl libc 差异)
- 应用: incron, util-linux (部分工具)

## 影响范围

已知受影响项目：
- incron 0.5.12
- util-linux (部分工具)
- 其他使用 GNU argp 进行命令行解析的项目

## 历史

- 2026-05-26: 首次发现（incron 0.5.12 编译）
- 2026-05-27: 知识条目创建