# jsonlint 1.6.3 适配笔记

## 编译环境
- 构建系统: custom (Node.js npm包，非传统C编译)
- 编译日期: 2026-06-11
- 运行时依赖: Node.js v24.13.0
- 状态: published

## 编译步骤

jsonlint 是纯 JavaScript/Node.js 应用，无需传统 configure/make 编译流程。

1. 源码下载: `https://registry.npmjs.org/jsonlint/-/jsonlint-1.6.3.tgz`
2. 全局安装: `npm install -g jsonlint@1.6.3 --prefix=$DEFAULT_PREFIX`
   - npm自动下载依赖: nomnom@1.8.1, JSV@4.0.x, chalk, strip-ansi, ansi-styles, has-color, underscore
   - npm自动创建bin链接: `$DEFAULT_PREFIX/bin/jsonlint -> ../lib/node_modules/jsonlint/lib/cli.js`
3. Staging安装: 复制 `$DEFAULT_PREFIX/lib/node_modules/jsonlint/` 到 `$TEST_PREFIX/$DEFAULT_PREFIX/lib/node_modules/jsonlint/`
   - 创建bin链接: `rm -f && ln -s ../lib/node_modules/jsonlint/lib/cli.js $TEST_PREFIX/$DEFAULT_PREFIX/bin/jsonlint`
4. 功能验证: jsonlint --version → 1.6.3 ✅
   - 有效JSON验证 ✅
   - 无效JSON错误检测 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build未自动找到npm包URL | jsonlint不在传统源码仓库 | 手动指定npm registry URL |
| 2 | cp -r lib/ 导致嵌套lib/lib/ | cp -r 目录时追加了一级 | mv修正路径，或从npm install结果直接复制 |

## 源码修改

无补丁，无需修改源码。jsonlint是纯JavaScript应用，所有文件在npm包中已预构建。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| node | 24.13.0 | 运行时 |
| nomnom | 1.8.1 | npm依赖 |
| JSV | 4.0.x | npm依赖 |
| chalk | - | npm依赖 |
| underscore | - | npm依赖 |

## 验证结果

```bash
$ jsonlint --version
1.6.3

$ echo '{"valid": true}' | jsonlint -q
[成功]

$ echo '{"invalid": true, missing}' | jsonlint
Error: Parse error on line 1...
```

## 交付物

| 文件 | 说明 |
|------|------|
| jsonlint-1.6.3-ohos-aarch64.tar.gz | 预编译包 |

## 注意事项

- jsonlint是Node.js脚本应用，ELF签名不适用（非ELF二进制）
- 需要Node.js运行时环境
- npm依赖已包含在预编译包中
---

**编译结束**: 2026-06-11 08:31
**最终状态**: published
