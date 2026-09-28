# libbfio 20260623 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin/clang，目标 aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# init + lang-preflight
python3 scripts/ohc-run.py init-build libbfio 20260623 --url=https://github.com/libyal/libbfio/releases/download/20260623/libbfio-alpha-20260623.tar.gz
python3 scripts/ohc-run.py lang-preflight libbfio 20260623   # task=cpp / detected=c 兼容族通过

# 配方（conan create 内 autotools 构建，profile ohos-aarch64）
conan create archives/l/libbfio/20260623 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 关键参数：--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --disable-nls --enable-static --disable-shared
# 上游测试：make -j1 check LOG_COMPILER=/data/service/hnp/bin/bash
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法猜测 HarmonyOS | config.guess 无 ohos 分支（E007） | 显式 `--build/--host=aarch64-unknown-linux-ohos`（20260623 版 config.sub 已收录 ohos，无需 config.sub 补丁） |
| 2 | configure 内嵌 umask 077 临时目录创建与 HMDFS 冲突 | 平台 umask 映射（E011） | build() 内联将 configure 中 `umask 077` 改写为 `umask 022` |
| 3 | 默认启用 NLS 依赖 gettext/libintl | autotools 默认 NLS（E027） | `--disable-nls` |
| 4 | 设备 bash 缺启动交互 | LOG_COMPILER 需指向设备 bash | `make -j1 check LOG_COMPILER=/data/service/hnp/bin/bash` |
| 5 | conan create `make -j4` 触发 fork OOM | 内存受限构建机并行 fork 过大 | 构建并行度降为 `make -j2`（OOM 防护，非源码/配方缺陷） |

## 源码修改

无补丁修改源码逻辑；`patches/` 为配方结构类（config.h/common config/dpkg changelog/spec），并在配方 `build()` 内联处理 umask 与 triplet。

## 依赖版本

- 无外部 Conan requires：libyal 内部依赖（libcerror/libcthreads/libcdata/libcfile/libcpath/libcsplit/libclocale/libcnotify/libuna）均捆绑于官方 release tarball，configure 无外部探测（W0 结论：deps ""）。

## 验证结果

```bash
# conan create（含上游测试 + test_package）exit 0
# 上游 autotest 3/3（error/support/system_string），test_manpages 按上游设计 skip
# 上游 input 驱动 9 个 check_PROGRAMS，9/9 rc=0
# test_package 消费者 14 项断言全过
# W3 本地 CI 模拟：Pass rate 100%（1/1），L0/L1/L4/L5 pass，L2 skip（无 bin/）
# .ci-result.json exit_code=0，log_sha256=91c2796c22c1eeb325c3a7006cf305f4e416c14ddad9d19e191b5bc7a83ba633
```

## 交付物

| 文件 | 说明 |
|------|------|
| libbfio.a | 静态库（--enable-static --disable-shared） |
| include/libbfio.h + libbfio/*.h | 公开头文件 |
| libbfio.pc | pkgconfig |

库类型包，无可执行文件，不需要 commands.json。

## 注意事项

- G0 clean-verify 的 configure 步骤在平台级临时目录 getcwd 不可判定时失败（SKILL 表列「非阻塞」平台限制项），不影响配方/测试结论；W3 正式门禁（conan create + build_and_test.sh）已通过。
- conandata sources.url 列 gh-proxy 镜像兜底 + 官方 URL，sha256 与官方一致（95ba2ee1a6365000b454f810e92709fd02bfcac0bba8a9b36512a0e71cc1bf32）。

---

**编译结束**: 2026-09-27 19:39
**最终状态**: built