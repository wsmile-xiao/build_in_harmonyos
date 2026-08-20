# authbind 2.2.0 适配记录

## 概述
authbind 允许非 root 程序 bind() 到低端口（<1024）。机制：
- `authbind` CLI 包装程序（设置 LD_PRELOAD 指向 libauthbind.so）
- `libauthbind.so`（LD_PRELOAD 拦截库）：通过 dlsym(RTLD_NEXT, "bind") 拦截 bind()，
  与 setuid helper 通信完成权限检查
- `helper`：setuid 助手（安装时 chmod u+s），读写 /etc/authbind/byport、byaddr、byuid 权限文件
- 依赖仅系统库 libc/libdl（Makefile LIBS=-ldl -lc），无任何第三方依赖

## 构建要点（r02 本地适配闭环）
- 上游：Debian source package authbind_2.2.0（Ian Jackson 维护，2024-11-11 发布）
  - 官方 pool: http://deb.debian.org/debian/pool/main/a/authbind/authbind_2.2.0.tar.gz
  - SHA-256: 8d265ee08e66fbda2e6c2b348624cd4552ff2c8fe72247d8904b06500c476adf（15881 字节，与官方一致）
  - 解压根目录 `work/`（conanfile source() 用 strip_root=True）
- 构建系统：纯 Makefile，无 configure；无 test target
- 编译：clang 15（OHOS aarch64 profile），CC/AR/RANLIB/LD 从 conan conf 注入（R33），-j1（R9）
- LD=clang 驱动 `$(LD) -shared -soname libauthbind.so.1` 生成 .so（保证 OHOS sysroot 一致）
- 打包：bin/authbind、lib/authbind/helper（setuid）、lib/authbind/libauthbind.so.1.0（+soname 软链）、
  share/man/man1/authbind.1、share/man/man8/authbind-helper.8

## 运行闭包待核验点（r02 阶段7）
- libauthbind.so 经 LD_PRELOAD 拦截 bind() 在 OHOS 的行为（无 setuid 环境下只能验证拦截/回退路径）
- helper setuid（chmod u+s）在 OHOS/HMDFS 文件系统的可用性；/etc/authbind 权限模型
- 上游 autopkgtest（debian/tests/socat，needs-root + socat + chiark-really）为 Debian 环境用例，
  本轮以 test_package 编译链接冒烟 + 仅读替代验证为准（任务禁止创建伪造产物）

## 测试
- 上游 Makefile 无 test target
- 唯一测试入口 debian/tests/ autopkgtest（需 root + socat + chiark-really），非本环境直接可运行
- test_package：编译链接 test probe + 运行 `authbind --version`/`--help` 冒烟（只读替代验证）

## A/B/C 初判（r01）→ 终判（r02）
- 无第三方依赖、657 行 C、纯 Makefile：路径 A（普通基础适配）
- 无具体系统接口/私有工具链/汇编/闭源/特殊架构/超大依赖/高成本测试证据 → B/C 不成立
- 终判：路径 A
---

**编译结束**: 2026-08-20 15:35
**最终状态**: built
