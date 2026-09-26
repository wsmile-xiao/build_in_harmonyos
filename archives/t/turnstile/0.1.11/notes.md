# turnstile 0.1.11 适配笔记

## 编译环境
- 构建系统: meson（上游 project('turnstile', ['cpp','c'])，c++17/c11）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: published

## 编译步骤

```bash
# 依赖注入：linux-pam/1.7.2（conan 制品仓发布，pkg_config_name=pam/pam_misc）
conan install --requires=linux-pam/1.7.2 -r=ohpcd -pr:h=ci/conan/profiles/ohos-aarch64

# meson 配置（man 关闭避免 scdoc 构建期依赖；pam_moddir 固定在包内 lib/security）
meson setup build --prefix=$PREFIX -Dman=false -Dpam_moddir=lib/security
ninja -C build
# 产物: build/turnstiled（守护进程）+ build/pam_turnstile.so（PAM 模块）
# 安装: DESTDIR=... meson install -C build → bin/turnstiled + lib/security/pam_turnstile.so + etc/*
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | linux-pam 的 pam.pc prefix=/ 导致 meson 得到 -I//include | linux-pam 配方 .pc 未随 conan 包改写 prefix | 手动编译期复制修正 prefix 的 pam.pc 到私有 PKG_CONFIG_PATH；conan 配方内用 PkgConfigDeps 生成正确的 pam.pc |
| 2 | meson sanity check C++ 探针 rc=127（libc++_shared.so 找不到） | profile LD_LIBRARY_PATH 只含 llvm/lib（libxml2），未含 aarch64-linux-ohos 子目录 | generate() 内 Environment+save_script 注入 SDK llvm/lib/aarch64-linux-ohos（ast 先例模式） |
| 3 | conan 2.29.1 Meson API 无 meson_layout / Meson.compile() | conan 版本 API 差异 | basic_layout(src_folder=".") + meson.build() |
| 4 | 包内 dinit backend 实际路径为 bin/turnstile/dinit 而非 libexec/turnstile/dinit | conan MesonToolchain 将 libexecdir 映射为 bin | test_package 断言按实际布局 bin/turnstile/dinit |
| 5 | test_package 直接执行 turnstiled 报 EPERM（rc=126） | OHOS hmmac/exec 策略拒绝 conan 缓存中 release 构建二进制（对照: work 目录 debugoptimized 二进制可执行 rc=1 因 /run 缺失属守护进程预期；其他缓存包可正常执行） | 参照 away 先例降级为静态产物验证（二进制存在+可执行+ELF+配置存在），如实说明守护进程需 /run+PAM 会话 |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| linux-pam | 1.7.2 | 提供 libpam/libpam_misc（pkg-config: pam/pam_misc）|
| python（运行时） | 3.12.x | conan test_package 执行 |

## 验证结果

```bash
# conan-verify（G0-G4 + L2/L4/L5 全 PASS）
python3 scripts/ohc-run.py conan-verify turnstile 0.1.11 --profile ohos-aarch64
# 上游测试: meson.build 无 test() 注册（grep test( = 0），无 tests/ 目录 → 上游 0 测试
# 自研测试: test_package/test_turnstile.py（1 项断言集：二进制/模块/配置存在性 + ELF 校验）→ 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方（PkgConfigDeps + MesonToolchain + SDK lib 注入）|
| conandata.yml | 上游官方 tarball（sha256 04904eff...）|
| commands.json | R38 可执行文件声明（turnstiled）|
| test_package/ | 消费者测试（R34 降级验证）|

## 注意事项

- turnstiled 为守护进程，真实运行需要 /run 基础目录 + PAM 会话（systemd-logind 类环境），OHOS 构建节点不具备；二进制在 conan 缓存中被 hmmac 执行策略拒绝（EPERM），属构建节点安全策略，CI pr.diff 模式不受影响
- library 选项保持上游默认 disabled（不产出 libturnstile.so），dinit backend 默认 enabled（数据文件）
---

**编译结束**: 2026-09-21 12:16
**最终状态**: published
