# identity4c 1.0 适配笔记

## 编译环境
- 构建系统: manual Makefile (upstream 使用 autotools，但 CI runner 缺少 automake/libtool)
- 编译日期: 2026-07-28
- 编译器: clang (aarch64-linux-ohos)
- 状态: built
- 许可证: GPL-2.0+ with OpenSSL exception

## 编译步骤

1. **源码下载**: 使用 `conan source` 从 GitHub 下载 identity4c 1.0
   - 源码: https://github.com/ufpidentity/identity4c
   - Tag: 1.0
   
2. **手动编译** (替代 autotools autogen.sh → configure → make):
   - 直接调用 clang 编译 6 个 .c 源文件为 .o
   - ar rcs 打包为 libufpidentity.a
   - 安装头文件 identity.h 和 strmap.h
   
3. **依赖**:
   - openssl/3.5.6 (SSL/TLS)
   - libxml2/2.15.3 (XML 解析)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | openssl/libxml2 未发布到远程制品库 | 依赖包仅 built 未 published | 将依赖包提交 PR → CI upload → 发布后构建下游 |
| 2 | automake/libtool 构建环境中缺失 | 环境未安装完整 autotools 工具链 | 使用手动 Makefile 替代 autogen.sh |
| 3 | chmod 不生效 | HMDFS SELinux 限制 (E046) | 使用 `/data/service/hnp/bin/bash` 显式调用脚本 |
| 4 | openssl::openssl CMake target include 为空 | openssl package_info 未设 cmake 属性 | test_package 手动添加 openssl include 路径 |

## 补丁
- 无补丁。构建使用手动 Makefile 直接编译源码，无需修改上游文件。

## 依赖版本
- openssl/3.5.6
- libxml2/2.15.3

## 交付物

| 文件 | 说明 |
|------|------|
| libufpidentity.a | 静态库 |
| include/identity.h | 公共头文件 |
| include/strmap.h | strmap 头文件 (bundled) |

## 验证结果

```bash
conan create archives/i/identity4c/1.0 -pr=ci/conan/profiles/ohos-aarch64 --build=missing
# 输出:
# PASS: strmap put/get/exists round-trip OK
# PASS: identity_context_t type accessible
# PASS: library API symbols resolved (link OK)
# Results: 3/3 tests passed
```

## 注意事项
- 使用 manual Makefile 替代 autotools (R33 合规: 编译器从 profile conf 获取)
- test_package 调用 strmap API (sm_new/sm_put/sm_get/sm_delete) 和 identity4c 符号验证 (R34 合规)
- 平台检查使用 `os in ("Linux", "OHOS")` (R32 合规)
- 无补丁 (R3: 无需修改源码)
- openssl::openssl INTERFACE_INCLUDE_DIRECTORIES 为空，test_package 需手动添加 include 路径
