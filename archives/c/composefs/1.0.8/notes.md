# composefs 1.0.8 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 状态: built（conan-verify 八道门禁通过，待 release 上传）

## 编译步骤

1. 官方源码: https://github.com/containers/composefs/archive/refs/tags/v1.0.8.tar.gz
   sha256=2b2b11f9a25744c82e9e12b098eefd0ab42d56ae6322634c15f966b3a64926ef
2. meson setup builddir -Dfuse=disabled -Dman=disabled --prefix=<prefix>（libcrypto 来自
   ohpcd openssl/4.0.1，通过 libcrypto.pc 垫片提供给 pkg-config）
3. ninja -j2 构建 libcomposefs(.a/.so) + 工具 mkcomposefs/mount.composefs/composefs-info/composefs-dump
4. conan create（ohos-aarch64 profile, --build=missing）干净构建验证 + test_package 消费者用例

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | mkcomposefs "error accessing ...: Invalid argument" | HMFS 对 FS_IOC_MEASURE_VERITY 返回 EACCES/EINVAL（Linux 为 ENODATA/ENOTTY/EOPNOTSUPP），composefs 视为致命 | 补丁 0001: lcfs_fd_measure_fsverity 将 EACCES 归一化为 ENOVERITY，回退进程内摘要计算 |
| 2 | mkcomposefs 读目录失败 | HMFS listxattr 暴露 security.hmmac 但非特权 getxattr 失败，read_xattrs 中止 | 补丁 0001: 跳过不可读的 security.* xattr（EACCES/EINVAL/EPERM） |
| 3 | test-lcfs 硬编码 /tmp 崩溃（tmpfd>0 断言失败） | OHOS PC /tmp 为 erofs 只读 | 补丁 0003: mkstemp 改读 TMPDIR |
| 4 | test-lcfs open_memstream 路径确定性 SIGSEGV/SIGILL（clang15 各 -O 级别均复现） | 工具链/libc 在 memstream 写 EROFS 时的实现缺陷；等价真实文件写入稳定通过 | 补丁 0003: testwrite_node 改用真实临时文件 |
| 5 | gendir "/usr/bin/python3: bad interpreter" | 设备无 /usr/bin/python3 | 补丁 0002: shebang 改 /usr/bin/env python3 |
| 6 | conan create 找不到 libcrypto | openssl 的 PkgConfigDeps 只生成 openssl-crypto.pc，无 libcrypto.pc | conanfile.py generate() 生成 libcrypto.pc 垫片指向 openssl 包 |
| 7 | test_package 消费者运行时找不到 libcomposefs.so.1 | composefs both_libraries 无条件构建共享库，消费者 DT_NEEDED 该 .so | conanfile.py package_info 声明 runenv_info LD_LIBRARY_PATH |

## 源码修改

- patches/0001-libcomposefs-lcfs-writer.c.patch: HMFS xattr/fsverity 语义适配
- patches/0002-tests-gendir.patch: python3 shebang 兼容
- patches/0003-tests-test-lcfs.c.patch: /tmp 只读 + open_memstream 崩溃适配

## 依赖版本

- openssl/4.0.1（ohpcd registry，libcrypto 必需；fuse3 未发布故 -Dfuse=disabled）

## 验证结果

```bash
# 上游测试（双口径: 5/6 通过，1 项 fuse 平台硬阻塞）
meson test --list  # 6 项注册
check-units / check-checksums / check-dump-filtered / check-should-fail / test-lcfs: PASS
check-random-fuse: 平台阻塞（沙箱无 CAP_MKNOD/fuse 内核）

# 鸿蒙专项测试（ohos-test/ohos_fsverity_test.c）
./ohos_fsverity_test   # 4 项断言全过: measure EACCES 归一化、摘要确定性/敏感性、公共 API 往返

# 消费者用例（test_package/test.c）
./test_composefs       # CONSUMER OK: EROFS 镜像 16384 字节, app.txt 内容往返校验一致
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方（openssl/4.0.1 + fuse/man 禁用 + libcrypto.pc 垫片） |
| conandata.yml | 官方 tag URL + sha256 + 3 补丁 |
| test_package/ | 消费者用例（CMake + test.c） |
| patches/ | 3 个 OHOS 适配补丁 |
| ohos-test/ohos_fsverity_test.c | 鸿蒙专项测试 |
| commands.json | R38 CLI 声明（mkcomposefs/composefs-info/mount.composefs） |

## 注意事项

- fuse 支持未启用（fuse3 未发布到 ohpcd）；check-random-fuse 需在具备 fuse 内核+CAP_MKNOD 环境运行
- 上游测试以注册命令直接执行记录（meson 运行器在本平台挂起），台账见最终回报
---

**编译结束**: 2026-09-25 17:17
**最终状态**: built
