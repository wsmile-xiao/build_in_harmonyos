# nmrpflash 0.9.27 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang 15
- 状态: built

## 编译步骤
```bash
conan create archives/n/nmrpflash/0.9.27 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络环境受限 | conandata.yml 指向官方 URL，CI 自动处理镜像 fallback |
| 2 | OHOS 内核头文件与 libnl 的 linux/netlink.h 冲突 | OHOS sysroot 的 linux/socket.h 和 sys/socket.h 都定义了 sockaddr_storage | 编译 nmrpflash 时添加 -D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=ushort |
| 3 | libnl include 路径缺少 /libnl3 子目录 | libnl cpp_info.includedirs 返回 "include" 而非 "include/libnl3" | build() 中优先使用 package_folder/include/libnl3 标准路径 |

## 依赖版本
- libnl/3.7.0（已可用）
- libpcap/1.10.6（已可用）

## 验证结果
```bash
$ nmrpflash -V
nmrpflash 0.9.27
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 构建） |
| conandata.yml | 源码下载配置 |
| manifest.yaml | 归档元数据 |
| test_package/conanfile.py | 消费者测试 |

## 注意事项
- nmrpflash 是命令行工具，无上游测试套件
- 依赖 libnl/3.7.0 和 libpcap/1.10.6
---

**编译结束**: 2026-07-24 16:47
**最终状态**: built
