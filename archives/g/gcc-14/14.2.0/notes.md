# gcc-14 14.2.0 适配笔记

## 软件信息
- 上游: https://ftp.gnu.org/gnu/gcc/gcc-14.2.0/gcc-14.2.0.tar.xz
- 构建系统: autotools（自研 conanfile 驱动，非模板生成）
- 类型: application（原生 GCC 14 C 编译器 + 静态 libgcc）
- 参考: archives/g/gcc/9.5.0 配方改编

## 依赖
GCC 14.2.0 官方 `contrib/download_prerequisites` 选定的 in-tree 版本
（已从 tarball 内核实）: gmp-6.2.1 / mpfr-4.1.0 / mpc-1.2.1，
全部在源码树内构建，无外部 conan requires。

## 关键适配（详见 conanfile.py 与 manifest.yaml）
- `aarch64-linux-ohos` 映射到 GCC musl 目标（config.gcc/ohos.h）
- config.sub / configfsf.sub 注入 `*-linux-ohos` 三元组
- Autoconf `umask 077` → `umask 022`（HMDFS）
- ELF 签名: 编译器包装脚本（clang-sign/xgcc-sign）+ 构建后全树签名
- 无限栈 bash 运行 configure/make（HMDFS shell 栈溢出）
- SIGSEGV 单次重试（HMDFS 瞬态）
- `--disable-threads`（OHOS libc 无 pthread_cancel）
- GNU as/ld 覆盖 OpenDesk 的 llvm-as（见 conanfile generate()）

## 历史踩坑记录（勿重复）
1. **2026-09 CI 失败（PR #8101 第一轮）**: conandata.yml 中
   gcc-14.2.0.tar.xz 的 sha256 错误（077ca9ff... ≠ 官方 a7b39bc6...），
   conan create 在 source() 阶段 sha256 校验失败，4 个镜像全部下载成功
   但哈希不匹配。修复: 使用官方哈希 a7b39bc69cbf9e25826c5a60ab264770
   01f7c08d85cec04bc0e29cabed6f3cc9（tuna/ustc/aliyun/ftp.gnu.org 一致
   计算 + 本地下载复核）。gmp/mpfr/mpc 三个哈希经本地下载核实均正确。
2. **构建时长**: 原生 GCC 全量构建超出默认 3600s 预算，
   build_timeouts.txt 已配置 gcc-14/14.2.0 14400（与 CI worker 步骤
   预算一致）。配方内 make 限 -j2（HMDFS FIFO jobserver 不可靠，
   pipe jobserver + 2 路保守并行）。
3. **manifest knowledge_gained 曾误记前置版本**（写成 gcc9 时代的
   gmp-6.1.0/mpfr-3.1.4/mpc-1.0.3），已修正为 14.2.0 官方选定的
   6.2.1/4.1.0/1.2.1。

## 本地复验记录
- 2026-09-17: `conan create ... --user=ohpcd --channel=stable`
  （G2 同源命令），源码下载命中本地缓存，包 ID
  6b129b068851896169fae42d399fa922d239ce8a，与 CI 失败日志中的
  包 ID 一致。结果见 reports/test-report.md。
- 2026-09-17: W3（build_and_test.sh 本地模拟，--build=gcc-14/* 强制
  重建 plain 引用）通过；conan-verify G1 的"补丁应用调用"检查为
  grep 误报（本配方无 patches/，源码变换在 source() 内完成，与已合入
  main 的 gcc/9.5.0 同构，该检查不阻塞 finish/submit/CI 门禁）。
- W4 Pre-PR 审计 verdict=pass（P0=0 P1=0，1×P2 已修复：commands.json
  binary→false；P3 文档项已修复）。
---

**编译结束**: 2026-09-17 13:00
**最终状态**: built
