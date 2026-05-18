# polipo 1.1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-14
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### 1. 源码下载
从 Ubuntu 源下载 polipo_1.1.1.orig.tar.gz：
```bash
wget -O polipo_1.1.1.orig.tar.gz "http://archive.ubuntu.com/ubuntu/pool/universe/p/polipo/polipo_1.1.1.orig.tar.gz"
```

### 2. 初始化编译
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build polipo 1.1.1 --url=file:///storage/Users/currentUser/tmp/polipo_1.1.1.orig.tar.gz
```

### 3. 编译
Polipo 是纯 Makefile 项目，无 configure 脚本：
```bash
make CC=clang PREFIX=$DEFAULT_PREFIX CDEBUGFLAGS="-fPIC -O2" all
```

### 4. 安装到 staging 目录
```bash
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
cp polipo $TEST_PREFIX$DEFAULT_PREFIX/bin/
```

### 5. 创建预编译包
```bash
# Strip + 签名
llvm-objcopy --strip-debug polipo
binary-sign-tool sign -inFile polipo -outFile polipo -selfSign 1
chmod +x polipo

# 打包
tar -czf polipo-1.1.1-ohos-aarch64.tar.gz *
```

### 6. 安装到本地验证
```bash
cp polipo $DEFAULT_PREFIX/bin/
$DEFAULT_PREFIX/bin/polipo -v
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 源 SSL 证书错误 | SSL 验证失败 | 从 Ubuntu 源下载 |
| 2 | 缺少 makeinfo | texinfo 包未安装 | 跳过文档生成，不影响二进制 |
| 3 | md5.c 编译警告 | 旧式 C 函数定义 | 非致命，忽略 |
| 4 | G0 验证失败 | polipo 无 configure 脚本 | 手动验证通过 |

## 源码修改

无补丁，纯 Makefile 项目无需修改源码。

## 依赖版本

- 无外部依赖
- 仅需标准 C 库（musl）

## 验证结果

```bash
$ polipo -v
Couldn't determine host name -- using ``polipo''.
Disabling disk cache: No such file or directory
Disabling local tree: No such file or directory
configFile (none) Configuration file.
CHUNK_SIZE 8192 Unit of chunk memory allocation.
...
✅ 程序正常运行
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| polipo-1.1.1-ohos-aarch64.tar.gz | 252KB | 预编译包（已 strip + 签名） |

## 注意事项

1. polipo 已停止维护（2014 年最后版本）
2. 运行时警告（主机名、缓存目录）属于配置问题
3. 可用于测试/学习，生产环境建议用更现代的代理
---

**编译结束**: 2026-05-14 19:24
**最终状态**: built
---

**编译结束**: 2026-05-14 19:24
**最终状态**: published
