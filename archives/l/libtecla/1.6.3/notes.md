# libtecla 1.6.3 适配笔记

## 编译环境
- 构建系统: custom（configure + Makefile，纯 C 静态库）
- 编译日期: 2026-08-11
- 编译器: clang 15（OHOS 工具链）
- 状态: built

## 编译步骤

1. `autoconf` — 用现代 autoconf（2.72）重新生成 configure（旧 2003 版 configure 生成的 config.status 在 OHOS 上临时目录 Permission denied）
2. 替换 config.guess/config.sub 为现代版（automake-1.17，识别 OHOS）
3. `sed umask 077→022`（E046：HMDFS 拒绝 700 权限 mktemp 目录）
4. `./configure --prefix=/usr --build=aarch64-linux-ohos --host=aarch64-linux-ohos`
5. `sed Makefile 在 -lc 前插入 sysroot -L`（.so 链接用 ld.lld 直接 -lc，绕过 clang 驱动找不到 OHOS libc）
6. `make -j2` — 产出 libtecla.a / libtecla_r.a

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码在 source_folder/libtecla/ 子目录 | tarball 条目带 ./ 前缀，conan strip_root 只剥 . | 配方 _src_root() 动态定位 configure 目录 |
| 2 | config.guess 不识别 OHOS + 临时目录 Permission denied | 2003 版 config.guess/config.sub + OHOS temp 怪癖 | 替换现代版 + 固定 --build/--host 三元组 |
| 3 | config.status 临时目录 Permission denied | 旧 configure 生成机制的 OHOS 不兼容 | 现代 autoconf 重新生成 configure |
| 4 | configure 内部 umask 077 | HMDFS 拒绝 700 权限 mktemp（E046） | sed umask 077→022 |
| 5 | ld.lld 找不到 -lc | make 的 .so 链接直接用 ld.lld（绕过 clang 驱动） | sed Makefile 在 -lc 前插 sysroot -L |

## 源码修改

无（构建期脚本替换/修正，非源码补丁）

## 依赖版本

无（自包含 C 库）

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # G2 PASS
conan-verify: G0-G4 + L2/L4/L5 PASS
build_and_test.sh libtecla/1.6.3（清缓存独立运行，CI 等价）  # L0/L1 PASS，L1e 确认真实依赖
test_libtecla.sh: PASS=3 FAIL=0（头文件 + libtecla.a + 编译链接调用 libtecla_version() 断言 1.6.3）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/libtecla-1.6.3.tar.gz | 531KB | 上游 caltech tarball（与 conandata.yml 一致） |

## 注意事项

- 本地 ohc-run finish 的 W3 L1e 有 harness 假阳性（conan-verify 创建 @ohpcd/stable 条目 + W3 plain create 双条目，L1e 复跑解析到未破坏条目）；CI 独立运行 build_and_test 无此问题（已验证 exit=0），见 manifest knowledge_gained
---

**编译结束**: 2026-08-11
**最终状态**: built
