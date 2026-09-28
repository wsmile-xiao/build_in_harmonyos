# libsir 2.2.6 适配笔记

## 编译环境
- 构建系统: 自定义 Makefile（sircommon.mk / sirplatform.mk，非 autotools）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / llvm-ar / GNU Make 4.4.1
- 状态: published
- 目标平台: OHOS armv8-aarch64（ohos-aarch64 profile, Release）

## 编译步骤

```bash
# 上游源码核验：v2.2.6 标签 = 80279377e5b33353fbefbc69333b8d26a015eef3（gitclone/ghfast 双镜像一致）
# Bootstrap + 探索性编译（work 目录）
make -j1 SHELL=/bin/sh all
# 上游测试（R02 普查实测：45 个可运行入口，全部实际运行通过）
LD_LIBRARY_PATH=./build/lib ./build/bin/sirtests          # 36/36 默认运行 PASS
LD_LIBRARY_PATH=./build/lib ./build/bin/sirtests --perf   # 1/1 performance PASS
LD_LIBRARY_PATH=./build/lib ./build/bin/sirtests++        # 8/8 C++ 入口 PASS
# conan 配方验证（conan create with ohos-aarch64 profile）
ohc-run.py conan-verify libsir 2.2.6               # G1-G4 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make -j2` 报 jobserver mkfifo: Operation not permitted | HMDFS 不支持 fifo，GNU make jobserver 无法建立 | 单任务构建 `-j1` |
| 2 | 每条 recipe 报 `/bin/sh: alias: -c: invalid alias name` | 上游 Makefile `SHELL := $(shell ... command -v sh)` 在本机解析成 `alias sh=sh`，shell 前缀非法 | 构建显式传 `SHELL=/bin/sh` |
| 3 | sanity-thread-ids 失败：`_sir_setthreadname("")` 返回 EINVAL | OHOS/musl libc 的 `pthread_setname_np` 拒绝空字符串（glibc 允许） | 补丁 0001：空线程名视为 no-op 成功 |
| 4 | conan create 报 No rule to make target 'all' | libsir 是 in-source 构建，basic_layout 把工作目录放在 build-release | 配方 build()/package() 用 `chdir` 到 source_folder 执行 make |
| 5 | 语言预检误报 mixed | 155 个 .js 全是 docs/ Doxygen 生成文档，setup.py 属 bindings/python，sh/cpp 属 .gitlab-ci CI——均非主体 | 主体为 C/C++（src/*.c + include/sir/*.h + sir.hh），属 c/cpp 兼容族，正常适配 |

## 源码修改

- `patches/0001-src-sirinternal.c.patch`：`_sir_setthreadname` 空名 no-op 守卫（无平台宏，glibc/musl 兼容）

## 依赖版本

- 无第三方强制依赖（W0 预检通过）

## 验证结果

```bash
# 上游 36 项测试全过
done: all 36 libsir tests passed in 3.316sec!
# conan-verify G1-G4 PASS
✅ 配方验证通过: libsir 2.2.6
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 自定义 Makefile 配方（in-source build, SHELL=/bin/sh, -j1） |
| conandata.yml | 官方 v2.2.6 tarball + SHA-256 |
| test_package/ | 消费者测试（R34：实质调用 sir_init/sir_debug/sir_getversionstring 等 API） |
| patches/0001-src-sirinternal.c.patch | 空线程名 no-op 修复 |

## 注意事项

- 构建必须 `-j1`（HMDFS 无 fifo）且 `SHELL=/bin/sh`（绕过 alias sh=sh 解析）
- libsir 静态库名 libsir_s.a，动态库名 libsir.so；配方 cpp_info 相应映射
- 上游测试命令 `make check` 不存在，实际测试入口为 `./build/bin/sirtests`（36 项）
---

**编译结束**: 2026-09-27 18:06
**最终状态**: built
