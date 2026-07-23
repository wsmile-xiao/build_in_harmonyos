# libnl 3.7.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-23
- 编译器: clang 15
- 状态: built

## 编译步骤
```bash
conan create archives/l/libnl/3.7.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure umask 077 导致 HMDFS 临时文件创建失败 | HMDFS 文件系统 umask 限制 | conanfile.py build() 中 inline replace_in_file: umask 077 → 022 |
| 2 | 构建主机缺少 aclocal/automake | 工具链环境限制 | 跳过 autoreconf；tarball 已预生成 configure |
| 3 | config.guess 无法识别 OHOS 系统 | 旧版 config.guess | 使用 --build=aarch64-unknown-linux-gnu 绕过 guess 步骤 |
| 4 | configure 在 /tmp 只读下创建临时目录失败 | /tmp 为 erofs 只读文件系统 | 设置 --prefix=/ 避免写 /tmp；configure 使用当前目录的 confXXXXXX 临时目录 |

## 构建依赖
- flex（代码生成）
- bison（代码生成）

## 运行时依赖
- 无（纯 C 库，netlink 协议）

## 依赖版本
- 无其他 Conan 依赖

## 验证结果
```bash
### test_package（consumer 验证）
- 编译链接：libnl-3, libnl-route-3, libnl-genl-3, libnl-nf-3, libnl-idiag-3, libnl-xfrm-3
- 运行时：nl_socket_alloc 需要 netlink 内核模块，OHOS 中不可用（预期行为）
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools 构建，静态库） |
| conandata.yml | 源码下载配置 |
| manifest.yaml | 归档元数据 |
| patches/ | 1 个 OHOS 兼容性补丁 |
| test_package/conanfile.py | 消费者测试 |
| test_package/test_libnl.c | 编译链接验证 |

## 注意事项
- libnl 是 nmrpflash 的前置依赖（PR !2171）
- 当前仅构建静态库（--disable-shared）
- 禁用了 CLI 工具（--disable-cli）
- 本 PR 关联 issue #1362
---

**编译结束**: 2026-07-23 14:42
**最终状态**: built
