# asn 0.81.0 适配笔记

## 编译环境
- 构建系统: 无（纯 Bash 脚本项目，安装即复制脚本）
- 编译日期: 2026-07-17
- 编译器: N/A（无编译步骤）
- 状态: built

## 软件简介

asn 是一个 ASN / IPv4 / IPv6 / Prefix / AS Path / Organization 查询和服务器工具。
它是一个纯 Bash 脚本，通过网络查询（RIPEstat、Team Cymru、pWhois 等）获取
AS（自治系统）和 IP 前缀的路由信息。

## 适配步骤

asn 是纯 Bash 脚本项目，无需编译。"安装"即将 `asn` 脚本复制到 `bin/` 目录。

1. 下载源码包（GitHub v0.81.0 tar.gz）
2. 解压源码
3. 验证脚本存在（无需 shebang 修复，已使用 `#!/usr/bin/env bash`）
4. 复制 `asn` 脚本到 `$PACKAGE/bin/`
5. 复制 man page (`asn.1`) 到 `share/man/man1/`
6. 复制 LICENSE 和 README.md 到 `share/doc/asn/`
7. 复制 bash-completion 到 `share/bash-completion/completions/`
8. 设置脚本可执行权限

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | Shebang 已为 `#!/usr/bin/env bash`，OHOS 可直接运行 | 无需修复 |

## 源码修改

无。所有源文件保持原样，无需补丁。

## 依赖说明

无编译依赖。运行时需要以下系统工具：
- bash 4.2+（脚本使用 mapfile、关联数组等 bash 4+ 特性）
- curl（网络请求）
- jq（JSON 解析）
- whois（WHOIS 查询）
- host（DNS 查询，来自 bind 包）
- mtr（网络路径追踪）
- nmap（端口扫描）
- grepcidr（CIDR 网段匹配）
- ipcalc（IP 计算）
- aha（ANSI HTML 转换）

这些是系统级运行时依赖，非 Conan 编译依赖，不声明在 conanfile.py 的 requirements() 中。

## 验证结果

```bash
# 脚本语法检查
$ bash -n asn
（无输出 = 语法正确）

# 版本验证
$ grep ASN_VERSION asn
ASN_VERSION="0.81.0"

# 无参数运行（显示用法）
$ ./asn
（显示用法信息）
```

## 注意事项

1. 本包为纯脚本包，无二进制文件，无需静态链接（R26 不适用）
2. settings 仅声明 "os" 和 "arch"，不需要 "compiler" 和 "build_type"
3. package_info 设置 bindirs=["bin"]，libs=[]（无库文件）
4. R38: 工具类包，commands.json 已在软件级目录声明
5. R32: settings.os 判断在运行时隐式处理（脚本通过 /usr/bin/env bash 自动适配）
6. 上游无测试套件（无 make check / ctest），test_package 使用消费者视角验证

---

**适配结束**: 2026-07-17
**最终状态**: built
