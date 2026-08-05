# accrete 1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4 (/data/service/hnp/bin/clang，OHOS aarch64 工具链)
- 状态: published

## 源码获取
- 最终 URL: `https://downloads.sourceforge.net/project/accrete/accrete/1.0/accrete-1.0.tar.gz`
  （SourceForge 项目 "accrete"；FreeBSD astro/accrete port 与 Gentoo 均引用同一 distfile）
- SHA256: `487c740a96ee05ce5ca8074e1713367eb92beb551d63c0ad1772b72e53ceee8c`（与 FreeBSD
  ports astro/accrete/distinfo 完全一致），大小 17212 字节
- 注意：SourceForge 主站 `sourceforge.net` 在部分网络环境被 Cloudflare 拦截，镜像站
  `downloads.sourceforge.net/project/accrete/accrete/1.0/` 可用（初探 URL 不存在的路径会
  301 跳转到真实路径 `/project/accrete/accrete/1.0/accrete-1.0.tar.gz`）

## 编译步骤
1. `bash ci/scripts/preflight_check.sh accrete/1.0 --deps ""` → 通过（无依赖）
2. `python3 scripts/ohc-run.py init-build accrete 1.0 --url=https://downloads.sourceforge.net/project/accrete/accrete/1.0/accrete-1.0.tar.gz`
   - 注意：check_env 步骤依赖可用的 automake（`$HOME/usr/local/bin/automake` 1.17 损坏），
     通过在 PATH 前置 shims/automake → automake-1.16 解决（环境问题，非本软件问题）
3. 编译（探索阶段，手动）：
   ```
   source .build-context-accrete-1.0
   cd $BUILD_SRC_DIR
   make CC=/data/service/hnp/bin/clang CFLAGS="-O2" LDFLAGS="" PREFIX=$DEFAULT_PREFIX
   ```
   → 生成 `accrete`，仅有无害的 `-Wparentheses-equality` 警告
4. 运行验证：`./accrete` 输出吸积过程，生成 `New.System`（含 SYSTEM CHARACTERISTICS 头 +
   若干 Planet # 条目，本次 13 颗行星）
5. `make check`：上游 Makefile 无 check 目标（记录为平台/上游限制），改以直接运行二进制验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SourceForge 下载被 Cloudflare 403 拦截 | 网络环境限制 | 用 `downloads.sourceforge.net/project/accrete/accrete/1.0/accrete-1.0.tar.gz`（HTTP/HTTPS 均可），SHA256 与 FreeBSD distinfo 一致 |
| 2 | Makefile 默认 `INSTALL=/usr/bin/install -s` 不存在 | OHOS 无 GNU coreutils install | conanfile.py 不调用 make install，package() 直接 copy 二进制到 bin/ |
| 3 | 本地 automake 1.17 损坏导致 init-build check_env 崩溃 | 环境残留 | PATH 前置 shims/automake → automake-1.16（脚本 bug `str(e)` 无法修改，用环境绕过） |

## 源码修改
- 无（原生编译通过，零补丁）。conandata.yml `patches: {}`。

## Conan 配方要点
- package_type = "application"（命令行工具，R38 → 软件级 commands.json）
- build(): `make -j1 CC=<conf 编译器> CFLAGS="-O2" LDFLAGS=""`（R33 取 Conan conf，R9 用 -j1）
- package(): 只复制 `accrete` 到 bin/（规避 /usr/bin/install 缺失）
- package_info(): 纯可执行包，cpp_info.libs 为空，bindirs=["bin"]
- validate(): `settings.os in ("Linux", "OHOS")`（R32）
- test_package: test.sh 真实运行 accrete 模拟并校验 New.System 内容（R34，非空壳）
- 数学库：链接无需 -lm（OHOS libc 直接提供 pow/sqrt 等）

## 验证结果
- conan create（-pr:h=ohos-aarch64 -pr:b=ohos-aarch64）: PASS，test_package 运行成功
  （生成 13 颗行星）
- conan-verify: G0/G1/G2/G3/G4 全 PASS，L2/L4/L5 门禁经手工验证：
  - L2 smoke: `accrete --version` exit=0
  - L4 安全: PIE(DYN) + NX(RW stack) + FULL RELRO(BIND_NOW)
  - L5 基线: SHA256=bc573ff7dbf99e508a6e7fa89f18ff6ed9217dd269ee01f3e070155292dcccfc
- W3 本地 CI 模拟: 通过（见 .ci-result.json）
---

**编译结束**: 2026-08-05 11:20
**最终状态**: published
