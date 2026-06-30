# hashcat

## 简介
hashcat 是世界上最快的密码恢复工具，支持多种哈希算法和攻击模式。

## 特性
- 支持 300+ 种哈希算法
- 多种攻击模式：字典、暴力、组合、规则等
- GPU 加速（OpenCL、CUDA）
- 支持分布式破解

## HarmonyOS 适配说明

### 已验证版本
- 7.1.2

### 编译配置
- 构建系统：自定义 Makefile
- 编译器：clang/clang++
- 平台适配：需要 3 个补丁

### 平台限制
- CPU 亲和性禁用（pthread_setaffinity_np 不可用）
- HMDFS 不支持 FIFO（需禁用并行构建）
- Python/Rust 插件可选（需要相应依赖）

### 补丁说明
| 补丁 | 用途 |
|------|------|
| 0001-deps-unrar-consio.cpp.patch | 替换 getpass 为 fgets |
| 0002-src-Makefile.patch | 添加 HarmonyOS 支持 |
| 0003-src-affinity.c.patch | 禁用 CPU 亲和性 |

## 使用方法

```bash
# 基本用法
hashcat -m 0 -a 0 hash.txt wordlist.txt

# 查看支持的算法
hashcat --help

# 查看版本
hashcat --version
```

## 依赖
- GNU sed 4.9+
- GNU coreutils 9.10+（ginstall）
- OpenCL 运行时（可选，用于 GPU 加速）

## 参考资料
- 官网：https://hashcat.net/hashcat/
- GitHub：https://github.com/hashcat/hashcat