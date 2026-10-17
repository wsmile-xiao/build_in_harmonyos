# ndisc6 1.0.8 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤

```bash
# 1. Patch config.guess/config.sub for OHOS (E007, E122)
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl admin/config.guess admin/config.sub
sed -i 's/| linux-uclibc\* )/| linux-uclibc* | linux-ohos* )/' admin/config.sub

# 2. Fix umask 077 -> 022 in configure (E011)
sed -i 's/umask 077/umask 022/g' configure

# 3. Fix netlink.c sockaddr_storage redefinition + strverscmp (E119)
# Applied via patch 0005-rdnss-netlink.c.patch

# 4. Configure
./configure --prefix=$DEFAULT_PREFIX

# 5. Build
make -j1 ACLOCAL=true AUTOCONF=true AUTOMAKE=true

# 6. Install
make install DESTDIR=$TEST_PREFIX

# 7. Test
make check
ndisc6 --version  # smoke test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | HarmonyOS 未在 config.guess 中 (E007) | patch-autotools-ohos.pl 补丁 |
| 2 | config.sub 拒绝 linux-ohos | linux-ohos 未在 kernel-os 验证列表 (E122) | 添加 linux-ohos* 到验证列表 |
| 3 | config.status Permission denied | HMDFS umask 077 创建不可写临时目录 (E011) | 修改 umask 077 为 022 |
| 4 | sockaddr_storage 重定义 | linux/socket.h 与 sys/socket.h 冲突 (E119) | 定义 _UAPI_LINUX_SOCKET_H 跳过 |
| 5 | strverscmp 未声明 | bionic libc 无此 GNU 扩展 | OHOS 下用 strcmp 替代 |
| 6 | aclocal-1.16 未找到 | automake 未安装 | make 时 ACLOCAL=true 覆盖 |

## 源码修改

| 文件 | 修改内容 |
|------|---------|
| admin/config.guess | 添加 HarmonyOS 检测分支 |
| admin/config.sub | 添加 ohos-linux 三元组和 linux-ohos 验证 |
| configure | umask 077 → 022 |
| rdnss/netlink.c | _UAPI_LINUX_SOCKET_H 守卫 + strcmp 替代 strverscmp |

## 依赖版本

无外部依赖（仅系统 libc 和内核头文件）

## 验证结果

```bash
$ ndisc6 --version
ndisc6: IPv6 Neighbor/Router Discovery userland tool 1.0.8 ($Rev$)
 built Aug  7 2026 on localhost
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/ndisc6 | IPv6 Neighbor Discovery 工具 |
| bin/rdisc6 | IPv6 Router Discovery 工具 |
| bin/rltraceroute6 | IPv6 traceroute 工具 |
| bin/tcpspray | TCP 吞吐量测试工具 |
| bin/name2addr | 地址解析工具 |
| bin/dnssort | DNS 排序脚本 |
| sbin/rdnssd | RDNSS 守护进程 |

## 注意事项

- ndisc6 是命令行工具集，非库文件
- 构建时需要 automake 覆盖（ACLOCAL=true）
- rdnssd 需要网络权限才能运行

## 结束

COMPLETED
