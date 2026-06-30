# acme.sh 3.1.3 适配笔记

## 编译环境
- 构建系统: none（纯 Shell 脚本）
- 编译日期: 2026-06-04
- 编译器: 无需编译器
- 状态: built

## 编译步骤

acme.sh 是一个纯 Shell 脚本工具，无需编译，直接安装即可：

1. 解压源码包：`tar xzf acme.sh-3.1.3.tar.gz`
2. 进入源码目录：`cd acme.sh-3.1.3.work`
3. 检查 acme.sh 可执行权限：已有执行权限（-rwxrwx---）
4. 创建测试安装目录：`mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin`
5. 复制主程序：`cp acme.sh $TEST_PREFIX$DEFAULT_PREFIX/bin/`
6. 复制辅助目录：`cp -r dnsapi deploy notify $TEST_PREFIX$DEFAULT_PREFIX/`
7. 验证安装：`$TEST_PREFIX$DEFAULT_PREFIX/bin/acme.sh --version` → v3.1.3 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G4 质量门禁失败 | manifest.yaml 中 build.system 设置为 autotools，但 acme.sh 无需构建系统 | 修改为 none |
| 2 | 质量门禁报告"无二进制文件" | acme.sh 是纯 Shell 脚本，不是 ELF 二进制 | 这是正常情况，无需处理 |

## 源码修改

无需修改源码。

## 依赖版本

无依赖。acme.sh 是独立的 Shell 脚本。

## 验证结果

```bash
$ /storage/Users/currentUser/test-install-acme.sh-3.1.3/storage/Users/currentUser/usr/local/bin/acme.sh --version
https://github.com/acmesh-official/acme.sh
v3.1.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| acme.sh-3.1.3-ohos-aarch64.tar.gz | 1823KB | 预编译包（包含 acme.sh、dnsapi、deploy、notify 目录） |
| acme.sh（本地安装） | 235KB | 已安装到 ~/usr/local/bin/acme.sh |

## 本地验证

```bash
$ /storage/Users/currentUser/usr/local/bin/acme.sh --version
https://github.com/acmesh-official/acme.sh
v3.1.3
```

## 注意事项

- acme.sh 是纯 Shell 脚本，无需 ELF 签名
- 需要复制 dnsapi、deploy、notify 目录到安装位置
- 安装时确保文件具有可执行权限
---

**编译结束**: 2026-06-04 11:43
**最终状态**: built
