# net-tools latest 适配笔记

## 编译环境
- 构建系统: custom (configure.sh交互式配置 + Makefile)
- 编译日期: 2026-06-18
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build net-tools latest --url=https://github.com/ecki/net-tools/archive/refs/heads/master.tar.gz`
2. 交互式配置: `yes "" | bash configure.sh config.in` (生成config.h/config.make)
3. 修改配置: 緻加 `__kernel_sa_family_t` typedef, 禁用 I18N/SELinux/多个协议族/硬件类型
4. 编译: `make -j1 CPPFLAGS+="-D_UAPI_LINUX_SOCKET_H -Drindex=strrchr"`
5. 安装: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | linux/socket.h与sys/socket.h冲突 | OHOS内核头文件重复定义sockaddr_storage | 添加typedef __kernel_sa_family_t到config.h + -D_UAPI_LINUX_SOCKET_H |
| 2 | rindex()函数不可用 | OHOS musC库未提供BSD遗留函数 | -Drindex=strrchr全局宏替换 |
| 3 | 多个协议族头文件缺失 | OHOS系统不支持IPX/AX25/NETROM等旧协议 | 在config.h/config.make中禁用对应协议族 |

## 源码修改

- config.h: 添加 __kernel_sa_family_t typedef, 禁用 I18N/SELinux等
- config.make: 对应配置变更

## 依赖版本
- clang 15.0.4
- GNU Make 4.4.1
- bash 5.3.0

## 验证结果
```bash
$DEFAULT_PREFIX/bin/ifconfig --version  # (输出net-tools版本信息)
$DEFAULT_PREFIX/bin/route --version
$DEFAULT_PREFIX/bin/netstat --version
```

## 交付物
| 文件 | 说明 |
|------|------|
| ifconfig | 网络接口配置 |
| route | 路由由表配置 |
| netstat | 网络状态统计 |
| hostname | 主机名管理 |
| arp/rarp | ARP/RARP管理 |
| nameif | 网络接口命名 |
| iptunnel/ipmaddr | IP隧道/多地址 |
| mii-tool | MII工具 |

## 注意事项
- net-tools使用交互式configure.sh（需bash），需手动输入配置
- OHOS平台不支持部分旧协议族（Token Ring,等），已在配置中禁用
- 编译产物无autotools标准configure --prefix支持，需手动处理DESTDIR安装路径
---

**编译结束**: 2026-06-18 01:55
**最终状态**: built
