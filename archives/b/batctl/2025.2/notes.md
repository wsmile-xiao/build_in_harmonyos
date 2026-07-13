# batctl 2025.2 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure 脚本)
- 编译日期: 2026-07-10
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
# 设置 PKG_CONFIG_PATH 以找到 libnl
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

# 应用 E119 修复补丁（ohos_compat.h + Makefile -include）
# 补丁已在 conanfile.py 中通过 apply_conandata_patches() 自动应用

# 编译（CC 从 Conan profile 获取，不依赖 shell 环境变量）
make CC=/data/service/hnp/bin/clang PKG_CONFIG_PATH=$PKG_CONFIG_PATH -j1 PREFIX=/usr/local

# 安装到 staging 目录
make PKG_CONFIG_PATH=$PKG_CONFIG_PATH install SBINDIR=/bin MANDIR=/share/man DESTDIR=...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: redefinition of 'struct sockaddr_storage'` | E119: OHOS SDK 的 linux/socket.h 和 sys/socket.h 都定义了 sockaddr_storage 结构体 | 创建 ohos_compat.h，定义 _UAPI_LINUX_SOCKET_H 跳过 linux/socket.h，手动定义 __kernel_sa_family_t |
| 2 | `cc: inaccessible or not found` | Makefile 默认 `CC ?= gcc`，但 OHOS 无 gcc | conanfile.py 从 Conan conf 获取 CC 路径并传递给 make |
| 3 | `No libnl-3.0 development libraries found!` | Makefile 在解析阶段运行 pkg-config 检查，但 PKG_CONFIG_PATH 未设置 | conanfile.py 动态搜索 libnl .pc 文件路径并传递给 make |
| 4 | test_package 运行时 `Error 127` | batctl 动态链接 libnl-3.so.200 和 libnl-genl-3.so.200，运行时找不到 | test_package 设置 LD_LIBRARY_PATH 指向 libnl 共享库目录 |

## 源码修改

- **ohos_compat.h** (新增文件): E119 修复头文件，通过 _UAPI_LINUX_SOCKET_H 宏守卫跳过 linux/socket.h
- **Makefile**: 添加 `CFLAGS += -include ohos_compat.h`

## 依赖版本

- libnl 3.11.0 (系统预装，共享库 .so)
- libnl-genl 3.11.0 (系统预装，共享库 .so)
- clang 15.0.4 (OHOS SDK)

## 验证结果

```bash
$ batctl -v
batctl 2025.2 [batman-adv: module not loaded]

$ readelf -d batctl | grep NEEDED
 Shared library: [libnl-3.so.200]
 Shared library: [libnl-genl-3.so.200]
 Shared library: [libc.so]
# libnl 动态链接，运行时需设置 LD_LIBRARY_PATH 指向 libnl 共享库目录
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 构建系统，CC/PKG_CONFIG_PATH 从 Conan conf 获取） |
| conandata.yml | 源码 URL + SHA256 + 补丁声明 |
| test_package/conanfile.py | L1 测试（运行 batctl -v，设置 LD_LIBRARY_PATH） |
| test_package/test_batctl.sh | 测试脚本，验证 batctl -v 输出 |
| patches/0001-Makefile.patch | Makefile 添加 -include ohos_compat.h |
| patches/0002-ohos_compat.h.patch | E119 修复：创建 ohos_compat.h 头文件 |
| commands.json (软件级) | R38 命令行工具声明 |

## 注意事项

- batctl 是命令行工具（非库），R38 要求创建 commands.json
- libnl 作为系统依赖通过 pkg-config 发现，非 Conan 包
- libnl 以共享库 (.so) 形式安装，batctl 动态链接 libnl-3.so.200 和 libnl-genl-3.so.200
- test_package 需设置 LD_LIBRARY_PATH 以便 batctl 找到 libnl 共享库
- E119 是 OHOS 平台通用问题，影响所有同时包含 linux/socket.h 和 sys/socket.h 的软件
---

**编译结束**: 2026-07-10
**最终状态**: built
