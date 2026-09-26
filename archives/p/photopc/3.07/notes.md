# photopc 3.07 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.13 时代极简包，tarball 自带 configure）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS SDK aarch64）
- 状态: built

## 编译步骤
1. W0：零依赖（无外部库，仅 libc/termios）。
2. 语言预检 lang-preflight：detected=c（任务声明 cpp，c↔cpp 兼容族不迁移，R47）PASS。
3. 探索构建（真机 -j1）：configure → make → install DESTDIR 全过；
   photopc/epinfo 二进制可直接执行。
4. 配方：conan-init 骨架 + 手工改写（application 型 + commands.json +
   行为断言式消费者测试）；conan-verify 8 门禁全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 临时目录 Permission denied | configure `umask 077 && mktemp -d` 在 HMDFS 不可写（E011 家族，同症状同解法） | 补丁把两处 umask 077→022（0001-configure.patch，2 行） |

## 源码修改

- `patches/0001-configure.patch`：configure 临时目录 umask 077→022（HMDFS 兼容）。
- 无 `__OHOS__` 平台宏，无源码文件改动。

## 依赖版本

- 无外部依赖（零依赖单工具包）。

## 上游测试五维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static | 0 | 上游无任何测试套件：Makefile.am 无 TESTS/check_PROGRAMS，树内无测试目录/框架（清点证据：Makefile.am 全文 + 树内 grep） |
| N_registered | 0 | 同上 |
| N_executed | 0 | 上游无测试可执行；行为验证由消费者测试承担 |
| 未执行分类 | 0 | 无（上游本来就没有测试） |
| N_consumer | 1 | consumer_test：对打包后的 photopc/epinfo 二进制做 4 组行为断言（ELF 签名后真机执行）——①epinfo -V 版本横幅含 "version 3.07"；②epinfo 对非 EPSON 文件走解析路径并报 "No camera-specific information"；③epinfo 无参数输出 usage；④photopc 无参数走设备 open/termios 错误路径（"open ... /dev/photopc" + "eph_open failed"） |

## 验证结果

```bash
# 探索构建（真机）
./configure --prefix=...    # CONFIGURE_RC=0（umask 补丁后）
make -j1 && make install DESTDIR=...   # MAKE_RC=0 / INSTALL_RC=0

# conan 门禁（ohc-run.py conan-verify photopc 3.07）
# G0-G4 + L2/L4/L5 全 PASS；consumer_test: photopc/epinfo behavior assertions OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/photopc | 串口相机控制 CLI |
| bin/epinfo | EPSON 照片文件信息提取 CLI |

## 注意事项
- photopc 依赖串口设备（/dev/photopc 默认）；本适配验证到设备 open/termios
  错误路径，无真实串口相机可做端到端（OHOS PC 无串口硬件，正文已说明）。
- termios 代码路径已编译进二进制并在错误分支得到执行覆盖。
---

**编译结束**: 2026-09-21 16:50
**最终状态**: built
