# triehash 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | triehash |
| 版本 | 0.3 |
| 官网 | https://github.com/julian-klode/triehash |
| 源码下载 | https://github.com/julian-klode/triehash/archive/refs/tags/0.3.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

triehash 是 Trie 哈希函数生成器：
- Perl 脚本工具
- 生成最小完美哈希函数
- 保留键顺序
- C 语言输出

## 安装步骤

### 1. 下载源码

```bash
curl -L -o triehash-0.3.tar.gz "https://github.com/julian-klode/triehash/archive/refs/tags/0.3.tar.gz"
tar -xzf triehash-0.3.tar.gz
cd triehash-0.3
```

### 2. 安装脚本

```bash
mkdir -p $HOME/usr/local/bin
# 修复 shebang（perl 可能不在默认路径）
sed -i '1s|#!/usr/bin/perl|#!$(which perl)|' triehash.pl
cp triehash.pl $HOME/usr/local/bin/triehash
chmod +x $HOME/usr/local/bin/triehash
```

## 使用方法

### 生成哈希函数

```bash
# 输入键列表文件
cat > keys.txt <<EOF
key1
key2
key3
EOF

# 生成 C 语言哈希函数
triehash --output=trie.c keys.txt

# 生成的 trie.c 可直接编译使用
```

### 生成的 C 代码示例

```c
// trie.c 生成的函数
int trie_hash(const char *key) {
    switch(*key) {
        case 'k':
            if (strcmp(key, "key1") == 0) return 0;
            if (strcmp(key, "key2") == 0) return 1;
            if (strcmp(key, "key3") == 0) return 2;
            break;
    }
    return -1;  // 未找到
}
```

## 用途

- APT 包管理器（包名哈希）
- 编译器关键字识别
- 命令解析器
- 状态机生成

## 编译产物

```
$HOME/usr/local/bin/
└── triehash    # Perl 脚本
```

## 参考链接

- [triehash GitHub](https://github.com/julian-klode/triehash)
- [APT 使用案例](https://salsa.debian.org/apt-team/apt)
