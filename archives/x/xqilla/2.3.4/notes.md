# xqilla 2.3.4 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15 (HarmonyOS PC aarch64, libc++)
- 状态: built (配方与测试已完成，真机预检尚未执行，HMBS 通过后更新为 published)

## 编译步骤

用户名：gcw_uQ09W7jl，队伍名称：干。

```bash
git checkout -b feat/xqilla-2.3.4 upstream/main
cd archives/x/xqilla/2.3.4
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

关键 configure 参数（由 conanfile.py generate() 注入）：

```bash
--with-xerces=<xerces-c package_folder> --disable-rpath --enable-static --disable-shared
CXXFLAGS=-std=c++14 CFLAGS=-std=c11
--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos (OHOS 下)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游使用 `register` 存储类，clang 15 默认 C++17 报错 | C++17 删除 `register` 关键字 | `tc.extra_cxxflags.append("-std=c++14")` （nixpkgs/Homebrew 同款要求） |
| 2 | configure 找不到 Xerces | 默认在 /usr/local 查找 | `--with-xerces=<package_folder>` 指向 Conan 依赖包 |
| 3 | /tmp 只读导致 configure/compilers 临时文件失败 | HMDFS /tmp 只读挂载 | `_pick_writable_tmp` 真实写入探测，回退到 build_folder/tmp |
| 4 | configure re-exec 找不到 shell | CI profile 指向 HNP bash，沙箱不可用 | CONFIG_SHELL/SHELL 覆盖为 /bin/sh |
| 5 | 上游测试套件判定 | tests/ 为需外部数据集的手动 runner，无 make check | no_tests 审计 + build() 防腐败守卫 + test_package 真实验证 |
| 7 | 真机 configure 报 C++ compiler cannot create executables（2026-09-20 预检 compile 阶段，C++ 默认输出文件名检查为空） | AutotoolsToolchain 未显式固定 conf 编译器且缺 -stdlib=libc++：OHOS musl 无 libstdc++，C 检查可过而 C++ 链接测试失败；且 clang 内部 ld.lld 走 PATH 解析 | generate() 单源读取 tools.build:compiler_executables 经 buildenv 固定 CC/CXX/CPP/CXXCPP，OHOS 追加 -stdlib=libc++ 到 cxxflags/ldflags，build() 由 conf 编译器目录前置 PATH 并在 configure 失败时转储 config.log 末 80 行 |
| 6 | 真机 configure 报 `config.sub aarch64-unknown-linux-ohos failed`（2026-09-20 预检 compile 阶段） | 随包 config.sub 太旧（E072），不认 linux-ohos 三元组 | build() 新增 `_patch_autotools_for_ohos()`：source/build 树内所有 config.sub 在 shebang 后插入 OHOS fast-path（任意 *ohos* 输入规范化为 `<machine>-unknown-linux-ohos`，版本无关），config.guess 有 NetBSD 锚点时补 HarmonyOS 分支；幂等，可重入 |

## 源码修改

无补丁（patches: {}）。上游在 -std=c++14 下可直接编译，无需 gcc11/register 补丁；若真机预检暴露新的现代编译器问题再追加。

## 依赖版本

- xerces-c/3.2.5#9086fe3ffea711440f8f71d66d6ca6d0（ohpcd 内建硬化配方，RREV 锁定避免落到 CCI）
- 无其他 Conan 依赖；math/pthread 来自 libc（system_libs m/pthread）

## 验证结果

```bash
# 真机预检由 HMBS 后台执行，本轮仅完成未提交工作树
# 预期 conan create 日志中出现：
# HMBS_TEST_PACKAGE_RESULT={"executed":true,...,"discovered":4,"passedCount":4}
# HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...,"discovered":0,...}
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libxqilla.a (默认静态) | XQuery/XPath 库 |
| bin/xqilla | 命令行工具（OHOS 下需签名） |
| include/xqilla/ | 公共头文件 |

## 注意事项

- 本配方默认静态库；shared=True 时保留 .so（xqilla 非系统同名库，R26 不适用）。
- 命令行工具已在 archives/x/xqilla/commands.json 声明（R38）。
- test_package 消费者测试必须真实调用 API/二进制（R34），禁止空壳打印。
| 8 | 上轮 buildenv/os.environ 固定后仍报 C++ cannot create executables，且 config.log 只转储了尾部变量区（ac_ct_CC/CXX 为空，中段探针细节缺失） | env 经 conanbuild 聚合未到达 configure 进程；尾部转储遮蔽了真实 clang 报错 | build() 改直调 configure（xapian-core 模式）：CC/CXX/CPP/CXXCPP+AR/RANLIB/NM/LD 内联固定，make 复用 CC/CXX 覆盖；_dump_config_log 改按 CC/CXX/probe/error 正则摘诊断段 |
| 9 | 本轮 package() 在 install-nobase_includeHEADERS 报 Error 64（2026-09-21 预检 compile 阶段；build/make 已通过，install 头文件安装失败） | 前三轮均假设根因为编译器固定/configure 探针，package() 始终保留 autotools.install()；但失败点已后移到 install 阶段，direct-configure 路线无法修复 install(1) 本身在 HMBS 沙箱被屏蔽/HMBS_CAP_CHMOD=0 的问题（xlslib 同类结论） | package() 改手动安装（xlslib precedent）：shutil.copyfile 直拷 source/include 下 ~393 个 .h/.hpp、build 树 .libs/libxqilla.a（+shared 如有）与最大非脚本 xqilla ELF（跳过 libtool wrapper），全程不用 install(1)/chmod；header<300 即失败防残缺；chmod/sign 均容错 |
