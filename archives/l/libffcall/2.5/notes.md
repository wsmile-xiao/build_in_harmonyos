# libffcall 2.5 适配笔记

## 编译环境
- 构建系统: autotools (configure + make + libtool)
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 profile: ohos-aarch64）
- 状态: built（conan-verify 全门禁通过，PR 交付后由 CI 发布）

## 编译步骤

```bash
# Bootstrap（init-build + lang-preflight，语言判定 cpp）
python3 scripts/ohc-run.py init-build libffcall 2.5 --url=https://ftp.gnu.org/gnu/libffcall/libffcall-2.5.tar.gz
python3 scripts/ohc-run.py lang-preflight libffcall 2.5 --src $BUILD_SRC_DIR

# Adapt（探索编译）
./configure --prefix=$DEFAULT_PREFIX --cache-file=config.cache
make -j1
make check   # 全部通过（exit 0）
make install DESTDIR=$TEST_PREFIX

# 配方固化
python3 scripts/ohc-run.py conan-init libffcall 2.5
python3 scripts/ohc-run.py conan-verify libffcall 2.5   # G0-G4+L2/L4/L5 全 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` | 本机 `uname -s=HarmonyOS`，GNU config.guess 无 HarmonyOS 检测分支（知识 E007） | `patch-autotools-ohos.pl` 打 config.guess/config.sub 补丁（__OHOS__ LIBC 检测 + HarmonyOS 系统识别 + ohos-linux triplet）→ 补丁固化 `patches/0001-build-aux-config.guess.patch` + `patches/0002-build-aux-config.sub.patch` |
| 2 | config.status 报 `can't create ./confXXXX/subs1.awk: Permission denied` | autoconf 2.72 生成的 config.status 用 `umask 077` 创建临时目录；本机 HMDFS chmod 无效（E046 平台限制），组权限被剥后目录不可写 | 本地环境层 mktemp shim（强制 umask 002）放入 conan profile PATH 前置目录；不进入源码/配方 |
| 3 | trampoline.c 报 `#error "Don't know how to make memory pages executable."` | 鸿蒙 aarch64 上 configure 检测 `mprotect can exec` 为 -1（SELinux at runtime 判定），且非 Android 分支不命中 | 在 `__ANDROID__` 分支基础上扩展 `__OHOS__`，走 `EXECUTABLE_VIA_MMAP_THEN_MPROTECT`（mmap RW → mprotect RX，已实测可执行 ret=42）；trampoline/ 与 callback/trampoline_r/ 两处副本 → 补丁固化 `patches/0004-trampoline-trampoline.c.patch` + `patches/0003-callback-trampoline_r-trampoline.c.patch` |
| 4 | conan-verify G2 补丁应用失败 `absolute paths are not allowed` | diff -u 生成的补丁头为绝对路径 | 用 `--label 'a/...' 'b/...'` 重新生成相对路径补丁头 |

## 源码修改

- `patches/0001-build-aux-config.guess.patch`：config.guess（__OHOS__ LIBC 检测 + HarmonyOS 系统 case 分支）
- `patches/0002-build-aux-config.sub.patch`：config.sub（ohos-linux triplet）
- `patches/0003-callback-trampoline_r-trampoline.c.patch`：callback/trampoline_r/trampoline.c 的 `__ANDROID__` 分支扩展为 `(__ANDROID__ || __OHOS__)`
- `patches/0004-trampoline-trampoline.c.patch`：trampoline/trampoline.c 的 `__ANDROID__` 分支扩展为 `(__ANDROID__ || __OHOS__)`（平台能力探针类，R8 例外，PR 说明理由）

## 依赖版本

- 无第三方 conan 依赖（纯 C 库，仅需 clang/make/autoconf 工具链）

## 上游测试（R51 申报与实测）

- 上游测试命令：`make check`（autotools 原生，无独立 tests/ 目录，测试程序位于各子目录 check 目标）
- 入口盘点（官方 2.5 tarball 逐子目录 check 目标，R03 复跑日志 r03-make-check.log exit 0）：
  - avcall/: minitests + minitests-c++ → 2 入口 PASS（uniq 无差异）
  - trampoline/: test1/test2/test2-c++ → 3 入口 PASS（test1/test2/test2-c++ 全部 passed）
  - callback/trampoline_r/: test1/test2 → 2 入口 PASS
  - callback/: test1/minitests/minitests-c++ → 3 入口 PASS
  - vacall/: minitests/minitests-c++ → 2 入口 PASS
- 实测结果：**12/12 实际执行测试程序 PASS**；**主测试组去重口径 = 8 入口**（avcall 2 + trampoline 3 + callback 3）
- 统计口径修正（R03）：R01 曾声明"上游合计 6"（口径偏小），审查实测 N=8 确认；已按逐入口盘点修正为 8 主入口 / 12 实际执行，PR 正文同步修正

## 验证结果

```bash
# conan-verify（8 门禁）：G0 PASS / G1 PASS / G2 conan create PASS / G3 系统同名库隔离 PASS
# G4 产物完整性 + L2 smoke + L4 checksec + L5 基线 → 全部 PASS，可标记 published
# test_package 消费者测试：调用 ffcall_get_version() 返回 2.5（>0），链接验证通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，静态库默认，R26 系统同名库隔离） |
| conandata.yml | 官方源 https://ftp.gnu.org/gnu/libffcall/libffcall-2.5.tar.gz + sha256 + 4 patches |
| test_package/ | 消费者测试（实质调用 ffcall_get_version API，R34 非空壳） |
| patches/ | 0001 config.guess / 0002 config.sub HarmonyOS 支持；0003/0004 trampoline __OHOS__ 可执行内存 |

## 注意事项

- 本机 HMDFS 的 config.status umask 077 临时目录权限问题（E046 平台限制）通过本地环境层 mktemp shim 解决，不进入交付物；CI 干净环境无此限制
- libffcall 同时安装兼容库 libavcall/libcallback/libtrampoline/libvacall（向后兼容 1.x），主库为 libffcall
---

**编译结束**: 2026-09-08 18:10
**最终状态**: built
