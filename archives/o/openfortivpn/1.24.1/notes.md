# openfortivpn 1.24.1 Conan 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am, git archive — no pre-generated configure)
- 编译日期: 2026-08-07
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos)
- 状态: built (conan adaptation complete)

## 源码
- URL: https://github.com/adrienverge/openfortivpn/archive/refs/tags/v1.24.1.tar.gz
- SHA256: c40d33acd97b89c2e943bfd839c19b69e5a7a5997052e2fc9a595602745c0465
- 注意: GitHub release tarball (releases/download/v1.24.1/...) 不可用，
  使用 git archive (archive/refs/tags/v1.24.1.tar.gz) 替代。两者内容
  相同但 archive 版本不含预生成的 configure 脚本，需要 autoreconf -fi。

## Conan 配方

### 依赖
- runtime: openssl/3.5.6 (libssl + libcrypto)
- build: automake/1.18, libtool/2.5.4 (autoreconf -fi)
- system: autoconf 2.72, pkg-config 0.29.2, m4 (from /data/service/hnp/bin)

### 平台适配

1. **E051: pthread_cancel 不可用**
   - 补丁 0001: configure.ac 移除 pthread_cancel 的 AC_CHECK_FUNCS 检查
   - 补丁 0002: src/io.c 用 #ifndef __OHOS__ 守卫包裹 5 个 pthread_cancel() 调用
   - 鸿蒙平台线程取消功能不可用，使用 sem 信号让线程自然退出

2. **OpenSSL .pc 文件路径问题**
   - conan openssl 包的 libssl.pc/libcrypto.pc 指向 build profile 路径 (/b/opens...)
   - 该路径在运行时不存在
   - 解决方案: 在 generate() 中设置 OPENSSL_CFLAGS/OPENSSL_LIBS 环境变量
   - configure 的 PKG_CHECK_MODULES 使用环境变量值，不调用 pkg-config

3. **E011: HMDFS umask 077**
   - autoconf 2.72 在 configure 脚本顶部设置 `umask 077`
   - HMDFS 上该权限模式导致 config.status 临时目录权限不足
   - 解决方案: _fix_configure_umask() 将 umask 077 改为 022
   - _fix_config_status() 移除 config.status 中的 umask 077 前缀

4. **OHOS triplet 识别**
   - autoreconf 生成的 config.sub/guess 可能不识别 ohos triplet
   - _patch_config_for_ohos() 添加 ohos-linux 映射

5. **ELF 签名**
   - OHOS XPM 要求可执行文件必须签名
   - _sign_binaries() 使用 binary-sign-tool 对 bin/ 下的 ELF 签名

## 验证结果

```bash
$ openfortivpn --version
1.24.1
```

- ELF: 64-bit arm64, dynamic (libc.so), PIE enabled
- make check: passed (no upstream test suite)
- conan create: passed

## 注意事项

- 源码使用 git archive (非 release tarball)，需 autoreconf -fi
- pthread_cancel 在鸿蒙平台不可用，线程取消功能已禁用
- pppd 默认路径 /usr/sbin/pppd 在鸿蒙上不存在，但编译不受影响
  (HAVE_USR_SBIN_PPPD=1, PPP_PATH=/usr/sbin/pppd)
- resolvconf 默认禁用 (RESOLVCONF_PATH=DISABLED)
- systemd 支持自动禁用 (无 systemd.pc)
---

**编译结束**: 2026-08-07 07:30
**最终状态**: built
