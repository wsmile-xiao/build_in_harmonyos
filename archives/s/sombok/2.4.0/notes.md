# sombok 2.4.0 适配笔记

## 编译环境
- 构建系统: autotools（tarball 无 configure，autoreconf -fi 引导）
- 编译日期: 2026-09-20
- 编译器: /data/service/hnp/bin/clang (15.0.4)
- 状态: built
- 设备: HarmonyOS PC（新机 frp-bar:32382），CONAN_HOME=~/tmp/ch/home-glm66-sombok
- Profile: ci/conan/profiles/ohos-aarch64（os=OHOS arch=armv8 clang 15 libc++ Release）

## 编译步骤

1. `conan create archives/s/sombok/2.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
2. 配方 source(): 下载官方 tag tarball + test-data 子模块语料（sombok-2.4.0 tag 钉住的 commit dd46a739，github archive 不含子模块内容），destination=test-data 保持 tests/*.t 的相对路径
3. build(): `env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi` → 去 umask 077（E114）→ `sh ./configure --prefix=/ --build/--host=aarch64-unknown-linux-gnu --disable-libthai` → `make -j1` → `make -j1 check`（上游 9 个 .t 真实执行）
4. package(): `make install DESTDIR=<package_folder>`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ohc-run build` 判定 makefile 项目后在残缺源码目录直接 make | init-build 的解压在 HMDFS 上丢文件（106→41，data/ 拍平），构建系统误判 | 绕开 work 目录，配方 source() 让 conan 自行下载解压（conan 解压完整） |
| 2 | configure 死于 "working directory cannot be determined" | profile CONFIG_SHELL=hnp bash 在 HMDFS 构建目录 getcwd 挂（E386/§12.38①） | `env -u CONFIG_SHELL SHELL=/bin/sh` 路由全部 configure/make（direvent 先例） |
| 3 | `make check` 报 "failed to create tests/*.t.trs" | automake≥1.16 对未声明后缀的 TESTS 不生成 .t.log 规则；且 glob 形式 `TESTS=tests/*.t` 首轮展开退化（shell 展开成 tests/* 把 lb.sh 也裹入，目标名变 .t.log 双后缀，pattern %.log:%.t 无法匹配） | 补丁 0001：Makefile.am 声明 `TEST_EXTENSIONS=.t`+`T_LOG_COMPILER=$(SHELL)`，TESTS 由 glob 改显式 9 文件列表 |
| 4 | test_package 运行报 "Error relocating test_sombok: symbol not found" | OHOS musl 忽略 DT_RUNPATH 且 conan 不注入 rpath，libsombok.so 未被加载（§12.38③）；另 conan self.run(env=[...]) 收 env 脚本文件名而非 KEY=VALUE | test() 里取依赖绝对 libdir，以命令行前缀 `LD_LIBRARY_PATH=...` 方式运行 |
| 5 | conan-verify G2 下载失败 | E017 ghfast 注入 URL 与 dlcache sidecar 登记的官方 URL 不匹配→缓存判 dirty 强制重下→ghfast 超时 | sidecar 同时登记官方+ghfast 双 URL（§12.39），缓存文件用已验证原件补齐 |

## 源码修改

- `patches/0001-Makefile.am-declare-.t-test-extension.patch`（+2 行声明 +TESTS 显式列表）：仅修测试调度基础设施，测试本体（tests/*.t、tests/lb.sh、test-data/）零改动。测试仍由 `make check`（automake 并行 harness）真实执行。

## 依赖版本

- automake/1.18、libtool/2.5.4（tool_requires，构建期）
- 无运行时依赖（libthai 可选支持显式禁用：--disable-libthai，OHOS 未发布 libthai）

## 上游测试统计（五维账本）

- N_static = 35（9 个 .t 的 TAP plan 之和：13+2+3+5+2+1+2+6+1）
- N_registered = 9（automake TESTS 注册）
- N_executed = 9（设备真实执行：8 PASS + 1 SKIP）
- 未执行：0；跳过 1：tests/07sea.t（上游 libthai 条件跳过——配方禁用 libthai，上游脚本主动 SKIP；同族 14sea_al.t 在无 libthai 路径下 PASS）
- N_consumer = 1（test_package/test_sombok.c：真实调用 linebreak_new/set_format/set_sizing/break/gcstring_destroy/destroy，断言 42 字符全部保留）

### 逐脚本结果（2026-09-20 设备实测）

| 脚本 | plan | 结果 |
|---|---|---|
| 01break.t | 13 | PASS 13/13 |
| 02hangul.t | 2 | PASS 2/2 |
| 03ns.t | 3 | PASS 3/3 |
| 05urgent.t | 5 | PASS 5/5 |
| 06context.t | 2 | PASS 2/2 |
| 07sea.t | 1 | SKIP（libthai 禁用，上游条件跳过） |
| 09uri.t | 2 | PASS 2/2 |
| 11format.t | 6 | PASS 6/6 |
| 14sea_al.t | 1 | PASS 1/1 |

合计：执行 9/9；通过 8；跳过 1（34/35 subtests 通过，1 subtest 随 07sea.t 条件跳过）

## 验证结果

```bash
# 设备（HarmonyOS PC aarch64）:
$ conan create ... --build=missing
...
PASS: tests/01break.t ... PASS: tests/14sea_al.t
# PASS: 8 | SKIP: 1 | FAIL: 0 | ERROR: 0
sombok/2.4.0: Package '6b129b068851896169fae42d399fa922d239ce8a' created
$ conan-verify sombok 2.4.0 → G0/G1/G2/G3/G4 全 PASS
# test_package: OK: 1 line(s), 42 chars preserved（exit 0）
```

## 路径 B 判断

- 有跨仓库复用价值的候选知识：automake≥1.16 对 legacy glob-TESTS 项目的 check 失效模式（TEST_EXTENSIONS 缺失 + glob 退化双坑）——与 §12.38①（CONFIG_SHELL 路由）组合覆盖了"新 automake×HMDFS×老 autotools 项目"的完整修复链。
- 查重结论：知识库已有 E386/§12.38①（CONFIG_SHELL）、E114（umask）条目；"TEST_EXTENSIONS 缺失导致 make check 无规则"与"glob TESTS 首轮展开退化"未检索到既有条目（knowledge/graph grep 无 automake TEST_EXTENSIONS 相关）。
- 判定：单条知识（补丁两行）+ 本 notes 记录已覆盖；不足以独立成跨仓库知识草稿（适用面窄：仅 legacy glob-TESTS 项目，且修复是标准 automake 声明）。按纯路径 A 申报，问题表已完整留痕可后续升格。

## 交付物

（打包产物见 packaging/，由 finish 生成）

## 注意事项

- test-data 语料必须随 conandata 第二 source 一起下发（子模块 commit dd46a7397228303b44b8a569a80fe9bf0131540c）；CI worker 网络受限时依赖 dlcache 预置（sidecar 需双 URL，见问题表 #5）
- HMDFS 上 init-build 解压丢文件——新任务源码探查一律用 conan 的解压或手工 tar（问题表 #1）
---

**编译结束**: 2026-09-20 03:20
**最终状态**: built
