# bcrypt 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | bcrypt |
| 版本 | 1.0 |
| 官网 | https://github.com/trgl/bcrypt |
| 源码下载 | https://github.com/trgl/bcrypt/archive/refs/tags/v1.0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

bcrypt 是密码哈希工具和库：
- bcrypt 密码哈希算法
- Blowfish 加密
- 自动加盐（salt）
- 可配置工作因子（cost）

## 编译步骤

### 1. 下载源码

```bash
curl -L -o bcrypt-1.0.tar.gz "https://github.com/trgl/bcrypt/archive/refs/tags/v1.0.tar.gz"
tar -xzf bcrypt-1.0.tar.gz
cd bcrypt-1.0
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/bcrypt cmake --install build
```

## 使用方法

### 命令行

```bash
# 哈希密码
bcrypt -h "mypassword"
# 输出: $2a$08$abcdef...hash

# 验证密码
bcrypt -c "$2a$08$abcdef...hash" "mypassword"
# 输出: Match!

# 指定工作因子（cost）
bcrypt -h -c 12 "mypassword"  # cost=12
```

### C API

```c
#include <bcrypt.h>

// 哈希密码
char hash[64];
bcrypt_gensalt(12, salt);  // cost=12
bcrypt_hashpw("password", salt, hash);

// 铺证密码
if (bcrypt_checkpw("password", hash) == 0) {
    printf("Match!\n");
}
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| cost | 工作因子（迭代次数=2^cost） | 8 |
| salt | 128位随机盐 | 自动生成 |

## 性能

| Cost | 时间 | 用途 |
|------|------|------|
| 4 | ~0.1s | 测试 |
| 8 | ~0.3s | 默认 |
| 12 | ~1s | 安全 |
| 16 | ~4s | 高安全 |

## 编译产物

```
$HOME/usr/local/
├── bin/
│   └── bcrypt       # 命令行工具
├── lib/
│   └── libbcrypt.a  # 静态库
└── include/
    └── bcrypt.h     # 头文件
```

## 参考链接

- [bcrypt GitHub](https://github.com/trgl/bcrypt)
- [bcrypt 算法规范](https://en.wikipedia.org/wiki/Bcrypt)
