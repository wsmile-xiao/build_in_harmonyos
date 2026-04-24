# fcrackzip 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | fcrackzip |
| 版本 | 1.0 |
| 官网 | https://github.com/hyc/fcrackzip |
| 源码下载 | https://github.com/hyc/fcrackzip/archive/refs/tags/fcrackzip-1.0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

fcrackzip 是 ZIP 文件密码破解工具：
- 暴力破解（Brute force）
- 字典攻击（Dictionary）
- 多线程支持
- 支持标准 ZIP 和 AES 加密

## 编译步骤

### 1. 下载源码

```bash
curl -L -o fcrackzip-1.0.tar.gz "https://github.com/hyc/fcrackzip/archive/refs/tags/fcrackzip-1.0.tar.gz"
tar -xzf fcrackzip-1.0.tar.gz
cd fcrackzip-fcrackzip-1.0
```

### 2. 配置

```bash
./configure --prefix=$HOME/usr/local
```

### 3. 编译

```bash
make -j$(nproc)
```

### 4. 安装

```bash
make install DESTDIR=$HOME/tmp/fcrackzip
```

## 使用方法

### 暴力破解

```bash
# 破解 4 位数字密码
fcrackzip -b -c 1 -l 4-4 protected.zip

# 破解 6 位字母密码
fcrackzip -b -c a -l 6-6 protected.zip

# 破解 4-8 位混合密码
fcrackzip -b -c aA1 -l 4-8 protected.zip
```

### 字典攻击

```bash
fcrackzip -D -p passwords.txt protected.zip
```

### 参数说明

| 参数 | 说明 |
|------|------|
| -b | 暴力破解模式 |
| -D | 字典模式 |
| -c | 字符集：a(小写), A(大写), 1(数字), !(特殊) |
| -l | 密码长度范围 |
| -p | 字典文件路径 |
| -u | 尝试解压验证 |

## 性能

- 单线程：~385 cracks/sec（bcrypt 测试）
- 多线程：~1500 cracks/sec（4线程）

## 编译产物

```
$HOME/usr/local/
├── bin/
│   └── fcrackzip    # 主程序
└── share/
    └── man/man1/    # 手册页
```

## 参考链接

- [fcrackzip GitHub](https://github.com/hyc/fcrackzip)
