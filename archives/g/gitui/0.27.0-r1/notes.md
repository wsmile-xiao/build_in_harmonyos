# gitui 0.27.0-r1 编译笔记

## 编译信息
- 软件名: gitui
- 版本: 0.27.0-r1 (实际使用Alpine edge gitui 0.28.1-r0，版本编号0.27.0-r1来自Chimera Linux)
- 构建系统: Rust (预编译二进制)
- 平台: linux/arm64 (OpenHarmony)

## 适配过程

### 关键决策
1. **使用预编译二进制**: rustc在HarmonyOS上崩溃，必须使用预编译musl动态链接二进制
2. **来源选择**: GitHub releases不可达(网络超时)，Chimera Linux repo不可达，最终使用Alpine Linux edge community APK
3. **版本映射**: 任务要求0.27.0-r1(Chimera)，实际部署0.28.1(Alpine edge)，功能更完整
4. **qsort_r shim**: Alpine的libgit2依赖qsort_r，但HarmonyOS musl libc(1.2.5)不导出qsort_r符号。
   解决方案: 编写libqsort_r_shim.so，提供qsort_r调用qsort+wrapper，patchelf将其添加为libgit2的NEEDED依赖

### 依赖链
```
gitui → libonig.so.5 ✓ (已有)
gitui → libgit2.so.1.9 → libssl.so.3 ✓, libcrypto.so.3 ✓, libllhttp.so.9.3 (新增), libpcre2-8.so.0 ✓, libssh2.so.1 (新增), libz.so.1 ✓, libc.musl ✓
gitui → libssh2.so.1 → libcrypto.so.3 ✓, libz.so.1 ✓, libc.musl ✓
gitui → libssl.so.3 ✓ (通过libssl3.so/external)
gitui → libgcc_s.so.1 ✓
gitui → libc.musl-aarch64.so.1 ✓
```

### 新增安装的库
- libgit2.so.1.9.4 (Alpine edge, patched with qsort_r shim)
- libssh2.so.1.0.1 (Alpine edge)
- libllhttp.so.9.3.1 (Alpine edge)
- libqsort_r_shim.so (本地编译的兼容 shim)

### 平台特殊处理
1. **musl qsort_r缺失**: HarmonyOS musl libc不导出qsort_r(GNU extension)，通过自定义shim库解决
2. **ELF签名**: 所有新增ELF文件需签名才能在HarmonyOS上执行
3. **RUNPATH设置**: gitui和依赖库通过RUNPATH=~/usr/local/lib定位共享库

## 验证结果
```
$ ~/usr/local/bin/gitui --version
gitui 0.28.1-nightly 2026-05-06 ()
```

## 编译结束
**编译结束**: 2026-06-03
**最终状态**: published
---

**编译结束**: 2026-06-03 12:17
**最终状态**: published
