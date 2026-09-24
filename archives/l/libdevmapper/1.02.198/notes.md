# libdevmapper 1.02.198 适配笔记

## 编译环境
- 构建系统: autotools（LVM2 2.03.24 源码树内 device-mapper 组件 libdm/）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built（conan create 验证后置 published）

## 编译步骤

1. 官方源码: `https://sourceware.org/pub/lvm2/LVM2.2.03.24.tgz`
   - SHA-256: `593c5503ba00faab1c6e0b4a597b9605ec7b5881845c04bf412ebf9d1bbfa13c`
   - 版本标识: VERSION=2.03.24(2), VERSION_DM=1.02.198（本包版本唯一来源）
   - 签名文件 `.asc` 已下载（本机无 gpg 未验签，SHA-256 已实测核验）
2. 交叉 configure（仅 device-mapper 组件）:
   ```bash
   CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
   AR=llvm-ar RANLIB=llvm-ranlib \
   ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes \
   ./configure --host=aarch64-linux-ohos --build=x86_64-linux-gnu \
     --disable-udev_sync --disable-selinux --disable-lvmlockd --disable-lvmpolld \
     --disable-dmeventd --disable-cmirrord --disable-cmdlib --disable-blkid_wiping \
     --disable-thin_check_needs_check --disable-cache_check_needs_check
   ```
3. `make device-mapper -j1` → 产物 `libdm/ioctl/libdevmapper.so.1.02`（445 个导出符号）
4. `make install_device-mapper DESTDIR=<staging>` → libdevmapper.h + libdevmapper.so + dmsetup/dmstats
5. 上游测试: `make test/unit/unit-test` + 运行 → **125/125 tests passed**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub: Invalid configuration 'aarch64-linux-ohos': OS 'ohos' not recognized` | GNU config.sub 不含 ohos 三元组（E007/E072） | config.sub 三处修改：basic_os 映射 + OS 白名单 + kernel-os 白名单 |
| 2 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | config.status 以 umask 077 建 0700 临时目录，共享文件系统下非属主进程不可写 | configure 脚本内 `umask 077` → `umask 022` |
| 3 | `ld.lld: undefined reference to rpl_realloc`（dmsetup 链接） | 交叉编译下 autoconf AC_FUNC 运行检测不可行，误判 malloc/realloc 需替换 | `ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes` |
| 4 | `fatal error: 'libaio.h' file not found`（unit-test 构建） | 上游 bcache.c 无条件 include libaio.h，OHOS sysroot 无此头 | libaio/0.3.112 已发布 ohpcd 制品仓，conan download 取头文件加入 -I/-L（仅测试用，非运行依赖） |

## 源码修改

无（配方内 build() 处理 umask 022 + uname-shim；config.sub 为构建期临时补丁，不进入归档 patches/）

## 依赖版本

- 无 conan requires（libdevmapper 为纯 libc/pthread 用户态库）
- 构建期辅助（测试）：libaio/0.3.112（ohpcd 已发布）

## 验证结果

```bash
# 上游单元测试（本机 aarch64 实测）
./test/unit/unit-test → 125/125 tests passed
# 消费者契约（父库 cryptmount 6.4.0 消费方式）
# AC_CHECK_HEADER([libdevmapper.h]) ✓
# AC_SEARCH_LIBS(dm_task_create, devmapper) ✓（-ldevmapper 链接 libdevmapper.so）
```

## 注意事项

- 版本陷阱：不得写 1.02.196（陈旧镜像条目）或 2.03.24（LVM2 自身版本）；本包版本 = VERSION_DM = 1.02.198。
- 上游 test/shell 428 个集成测试依赖内核 device-mapper ioctl 与 root/块设备环境，交叉沙箱无法运行（已如实申报，不阻塞）。
- libdevmapper 属系统同名库，配方默认静态（R26），避免污染 /lib、/lib64。
---

**编译结束**: 2026-09-22 17:29
**最终状态**: built
