# siscone 3.0.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (HarmonyOS aarch64)
- 状态: built（待真机预检）

## 编译步骤

上游为经典 Autotools C++ 库（configure + make + make install），无依赖：

```bash
./configure --prefix=/ --enable-static --disable-shared
make -j1
make check   # 上游无测试套件，no-op，仅留构建日志痕迹
make install DESTDIR=<package_folder>
```

Conan 配方（archives/s/siscone/3.0.5/conanfile.py）等价执行上述流程，
shared=True 时切换为 --disable-static --enable-shared。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码 URL 与 sha256 待确认 | 任务未提供上游仓库，需自行检索官方源 | 官方主页 https://siscone.hepforge.org/，下载 https://siscone.hepforge.org/downloads/siscone-3.0.5.tar.gz；sha256 取 Debian orig 包记录 08c63ad96516970c0ef5c030de2e626d6760efda8ece20dee410a515b7acf1e8（与 Gentoo DIST 大小 544738 一致），待真机 conan create 下载校验 |
| 2 | 2018 年 config.guess/config.sub 不识别 HarmonyOS（首轮正则补丁未命中仍报 cannot guess build type） | uname 返回 HarmonyOS，旧脚本无对应分支；针对 NetBSD 锚点的正则在 2018 版结构上未匹配，补丁静默落空 | _patch_ohos_autotools() 改为全树覆写最小 OHOS-aware shim（dap/3.9 + dcfldd/1.9.3 同构：guess 映射 HarmonyOS\|OHOS→<machine>-unknown-linux-ohos，sub 直通），chmod 0755；build() 在 OHOS 下显式追加 --build/--host=<machine>-unknown-linux-ohos（e2fsprogs/1.47.4 同构），彻底跳过 guess |
| 3 | config.status 临时目录在 HMDFS 上可能失败 | configure 生成的 config.status 用 umask 077 建临时目录，HMDFS 权限语义下失败（scamp/mcfly 已踩坑） | build() 开头 os.umask(0)，并把源码树内所有 configure 文件的 umask 077 替换为 umask 000 |
| 4 | 上游仅 1 个测试程序，HMBS 门禁要求显式审计接入（rule4 实测 N=1） | tarball 内 examples/test.cpp 为唯一测试程序（构建产物 examples/test）；顶层无 TESTS/check_PROGRAMS，make check 为 no-op，曾误判为 N=0 致 rule4 少报 FAIL | MANIFEST.yml 改 upstream_tests_exist:true + upstream_test_total:1（auto 口径，来源 examples/test.cpp）；主包 ship 该源码到 share/siscone_upstream_test，test_package 重编译执行并输出 discovered=1 真实标记；build() 显式运行构建产物 |
| 5 | Autotools 库无 CMake config，test_package 无法 find_package | siscone 只安装 headers/libs/.pc，无 CMake 配置文件 | test_package 用直接 clang++ 编译（-I/-L/-lsiscone -lsiscone_spherical -lm），不调用 CMake project()，规避 OHOS 下 compiler identification unknown 失败模式 |
| 6 | OHOS ELF 需签名否则 Operation not permitted | 未签名二进制在真机无法执行（sdl2-mixer 先例） | test_package build() 后调用 binary-sign-tool 自签名（存在才执行），恢复 0755 权限 |
| 7 | 真机 configure[157] 报 /data/service/hnp/bin/bash inaccessible，Error 127 | 仓库 profile 把 SHELL/CONFIG_SHELL 钉死到 HNP bash，该路径在当前 HMBS 宿主不可执行；Autotools helper 经 env=conanbuild 会重新导出该坏值，覆盖配方内联修改（bwm/0.6.3、classads DRAFT-6487 同类） | generate() 用 Environment.save_script 覆写 SHELL/CONFIG_SHELL=/bin/sh + 可写 TMPDIR（HMBS_TMPDIR 优先，不回退 /tmp）+ CC/CXX 回退；build()/package() 弃用 Autotools helper，改用显式 `"${shell}" ./configure` / make / make install，内联 export 在 conanbuild.sh source 之后生效 |
| 8 | 真机 make install 在 libtool 安装 .a 时掉文件：install -c .libs/libsiscone.a 后 chmod 644 报 No such file or directory | HMBS runtime install shim 无 mkdir -p 语义，在 HMDFS（HMBS_CAP_CHMOD=0/HARDLINK=0）下静默丢文件，libtool 后续 chmod 落空（cxxtools/3.0.0 同款报错原文） | build_folder 下写 cp/mkdir 语义 install shim（chmod \|\| true，多源+单源，os.open 0o755 免 chmod 能力），configure 后（build）与 make install 前（package）两次重定向生成 Makefile 的 INSTALL 变量；siscone 系 in-source 构建，重定向同时覆盖 source_folder 与 build_folder |
| 9 | 真机 package() 在 make install 成功后报 copy() src/dst must have different values | package() 内一段 lib→lib 自拷贝为无操作笔误（conan2 直接抛错），且通配符 isfile 永假导致 .la 清理无效 | 删除自拷贝，改用 glob 展开后 unlink，仅清理 *.la |

## 源码修改

无 patches/（纯配方适配，未改上游源码）。

## 依赖版本

无运行时依赖。构建仅需系统 autotools 工具链（configure 预生成，无需 autoreconf）。

## 验证结果

待 HMBS 真机预检（conan create + test_package + 上游 N=1 真实标记）。预检日志中的
conan create 输出将作为 PR 正文「上游测试用例通过率 / 新增测试用例通过率」的唯一依据，
本轮不预填数字。

```bash
# 真机将执行（示意）：
# conan create archives/s/siscone/3.0.5 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 ...
# 预期：make 后显式运行 examples/test 通过；./test_siscone 输出 4 行 CHECK-OK；
# HMBS_TEST_PACKAGE_RESULT discovered=4 passedCount=4；
# HMBS_UPSTREAM_TEST_RESULT status=passed discovered=1 executed=1
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/s/siscone/3.0.5/conanfile.py | Autotools 主配方（双库 libsiscone + libsiscone_spherical） |
| archives/s/siscone/3.0.5/conandata.yml | 官方源码 URL + sha256 |
| archives/s/siscone/3.0.5/manifest.yaml | 版本级 manifest（built，待预检后更新） |
| archives/s/siscone/3.0.5/test_package/test_siscone.cpp | 真实调用双库 API 的消费者测试（4 断言） |
| archives/s/siscone/3.0.5/test_package/conanfile.py | 直接编译 + 签名 + 双 HMBS 标记 |
| archives/s/siscone/3.0.5/test_package/MANIFEST.yml | 上游无测试审计 + 消费者测试声明 |

## 注意事项

- 本机为 Windows，无 Python/Conan，未在本机运行 conan；一切编译验证交由 HMBS 真机预检。
- 稀疏检出工作区（SKILL.md/docs/templates/knowledge/.gitcode/ci/archives/s），完整 fetch 未做全量检出以规避 Windows 非法文件名；不影响本 PR（单库原子）。
- PR 正文草稿见 .hmbs/pr-body.md，测试数字留待真机 evidence 轮填写。
