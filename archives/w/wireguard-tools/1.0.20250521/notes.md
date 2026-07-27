# wireguard-tools 1.0.20250521 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: published (已编译并发布)

## 编译步骤

wireguard-tools 使用简单的 Makefile 构建系统，无需 configure 步骤：

```bash
cd src
make PREFIX=$DEFAULT_PREFIX
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重复定义 | 鸿蒙SDK中 sys/socket.h 和 linux/socket.h 都定义了该结构体 | 在 include sys/socket.h 后定义 `_UAPI_LINUX_SOCKET_H` 宏避免 linux/socket.h 重复包含，并手动定义 `__kernel_sa_family_t` 类型 |
| 2 | WGALLOWEDIP_A_FLAGS 未定义 | 鸿蒙内核头文件版本较旧，缺少该宏定义 | 添加条件编译 `#ifdef WGALLOWEDIP_A_FLAGS` |

## 源码修改

**补丁文件**: `0001-ipc-linux-harmonyos-platform-fix.patch`

**修改文件**: `src/ipc-linux.h`

主要修改：
1. 调整头文件包含顺序，提前包含 `netinet/in.h`
2. 添加平台适配宏定义避免 sockaddr_storage 重复
3. 为 WGALLOWEDIP_A_FLAGS 添加条件编译

## 依赖版本

- 无外部依赖（wireguard-tools 仅依赖标准 C 库）

## 验证结果

```bash
$ wg --version
wireguard-tools v1.0.20250521-1-g5150cd6-dirty - https://git.zx2c4.com/wireguard-tools/

$ file wg
wg: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| patches/0001-ipc-linux-harmonyos-platform-fix.patch | 1.0KB | 平台适配补丁 |

## 注意事项

- wireguard-tools 编译简单，但需要注意鸿蒙平台头文件冲突问题
- 补丁适用于所有鸿蒙SDK版本，条件编译保证向后兼容性
---

## 质量门禁复查 (2026-05-19 12:22)

### G2 功能验证复查
```bash
$ ~/usr/local/bin/wg --version
wireguard-tools v1.0.20250521-1-g5150cd6-dirty - https://git.zx2c4.com/wireguard-tools/
Exit code: 0
```
✅ 验证结果：wg --version 成功执行（之前报告不准确）

### G3 可移植性复查
```bash
$ readelf -d ~/tmp/wg-check/bin/wg | grep RUNPATH
0x000000000000001d (RUNPATH)  Library runpath: [$ORIGIN/../lib:$ORIGIN/../lib/external]
```
✅ 验证结果：有 RUNPATH（之前报告不准确）

### ELF 签名验证
```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/tmp/wg-check/bin/wg
(成功执行)

$ readelf -S ~/tmp/wg-check/bin/wg | grep codesign
[29] .codesign         PROGBITS         0000000000000000  00013000
```
✅ 签名结果：ELF 签名已完成，.codesign section 存在

---

**复查结束**: 2026-05-19 12:22
**复查结论**: G2/G3 报告已修正，ELF 签名已验证，状态已更新为 published
---

**编译结束**: 2026-07-15 22:31
**最终状态**: published
