# fakeroot 1.37.1.2 适配笔记

## 编译环境
- 构建系统: autotools（configure/make）
- 编译日期: 2026-08-18
- 编译器: clang/clang++
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: built

## 编译步骤

```bash
# 下载源码（Debian 官方 orig tarball）
wget https://deb.debian.org/debian/pool/main/f/fakeroot/fakeroot_1.37.1.2.orig.tar.gz

# 应用补丁（config.guess/config.sub 增加 OHOS/HarmonyOS 支持，configure 修复 mktemp/umask）
# 参照 archives/f/fakeroot/1.37.1.2/patches/

# autotools 构建（OHOS 交叉编译）
./configure --prefix=<prefix> --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-ohos --disable-libcap --disable-acl --without-ipc-tcp
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | uname -s 返回 HarmonyOS，config.guess 无对应分支 | 补丁 0001：增加 `*:HarmonyOS:*:*` 分支与 `__OHOS__` 宏 |
| 2 | config.sub 无法识别 ohos-linux | config.sub 无 ohos 平台 | 补丁 0002：增加 `ohos-linux` 分支，basic_os=linux-ohos |
| 3 | configure 创建临时目录失败 | OHOS 无 umask 077 权限约束 | 补丁 0003：mktemp 去掉 umask 077，mkdir 用 umask 022 |
| 4 | 可选依赖缺失 | libcap/ACL/IPC-tcp 在 OHOS 不可用 | configure 用 --disable-libcap --disable-acl --without-ipc-tcp 关闭 |

## 注意事项
- fakeroot 通过 LD_PRELOAD 拦截系统调用模拟 root 环境（打包构建用）
- Debian orig tarball 自带 configure（无需 autoreconf）
- 参照主仓 fakeroot/1.37.2（published）的补丁做法

---

**编译结束**: 2026-08-18
**最终状态**: built
