# libtiger 0.3.4 适配笔记

## 编译环境

- 构建系统: autotools（configure + Makefile，预生成 configure，无需 autoreconf）
- 编译日期: 2026-09-18
- 编译器: clang
- 状态: built（待真机预检 evidence 回填后转 published 判定）

## 上游信息

- 上游项目：libtiger（Ogg Kate 字幕流渲染库，Pango + Cairo 后端）
- 上游归档主页：https://code.google.com/archive/p/libtiger/
- 源码包：libtiger-0.3.4.tar.gz，383685 字节
- 真实性：官方 Xiph 下载站当前 404，改用 Google Code Archive 官方归档镜像；
  包大小与 Gentoo Manifest 的 DIST 记录（383685）一致，SHA512 与 Gentoo
  同文件记录完全一致（`559e522b…802e6d`），可认定与官方发布包逐字节相同。

## 编译步骤

1. 下载上游源码包（sha256 见 conandata.yml）。
2. 打静态补丁 `patches/0001-misc-autotools-config-sub.patch`（aarch64 + linux-ohos 识别）。
3. `tool_requires`：无（使用预生成 configure；pkg-config 由 PkgConfigDeps 提供）。
4. `./configure --disable-doc --disable-shared --enable-static --host=<ohos-triplet>`；
   OHOS 本机构建时追加 `--build=<gnu-triplet>`（libkate 同款，避免 config.guess 探测）。
5. `make`，随后 `make check`（3 组 check-local 规范检查，见下）。
6. `make install`，打包 `lib/libtiger.a`、头文件与 `tiger.pc`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2013 版 config.sub 不识别 `--host=aarch64-linux-ohos` | 早于 aarch64 支持（E007 类）；且 `-linux*` 通配会把 `-linux-ohos` 改写成 `-linux-gnuohos` | 静态补丁 4 处：CPU 表加 `aarch64`、KERNEL-OS 表加 `linux-ohos*`、OS 校验表加 `-linux-ohos*`、`-linux*` 通配前加 `-linux-ohos*` 守卫（已 `git apply --check` 验证） |
| 2 | 官方 Xiph 下载站 404 | 上游发布基础设施下线（Google Code 时代项目） | conandata.yml url 改为有序列表：逐字节一致的 Google Code Archive 镜像在前，Xiph 官方 URL 保留最后回退；sha256 不变 |
| 3 | 上游无单元/集成测试框架 | 2013 年 Xiph 小库，仅有 check-local 规范 grep | build() 仍完整运行 `make check`（3 组）；test_package 补 2 场景 17 断言消费者测试；PR 如实声明（路径 A） |
| 4 | HMDFS 下 Autoconf 临时目录/权限 | umask 077 + 只读 /tmp（E114 类，libkate 同款） | 复用 libkate 逻辑：运行时把 configure 中 `umask 077` 改 `022`、`./confXXXXXX` 改 `TMPDIR` 兜底；configure/make 期间 `os.umask(0o022)` |
| 5 | 真机预检依赖 libffi/3.4.4 以 CCI 配方构建，configure 报 `/data/service/hnp/bin/bash: inaccessible or not found`（Error 127，2026-09-18 compile 阶段） | glib 直连裸 `libffi/3.4.4`，预检双远端优先命中 CCI（日志打 CCI 专属补丁 `0008-3.4.4-invalid-CFI-advance_loc.patch`，本仓配方无此补丁）；HMBS 的 readonly_tmp 诊断是误归因，真因是 CCI 劫持（ayatana-ido 第 15 轮同指纹实证） | 复用 ayatana-ido 已验证的 ohpcd 发布 RREV：`self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc", override=True)`（同版本 pin，不扰动 glib package_id；切 3.5.2 会迫使 glib 源码重建，已证伪故不采用） |
| 6 | 链接 lib/libtiger.la 时 libtool 报 `//lib/libkate.la is not a valid libtool archive`（2026-09-18 compile 阶段） | E236 类：libkate 包内 liboggkate.la 烤死 `--prefix=/` 的 `libdir=//lib` 绝对路径，libtool 链接时读取依赖 .la 追查不存在的 `//lib` 路径（gts/0.7.6 CI #27860 同指纹） | 复用 gts 解法：configure 成功后、make 前删除各依赖 libdir 下 `*.la`（libtool 回退到同目录 .a/.so 直连）；package() 删除自产 `*.la`（bwm/0.6.3、exiv2/0.28.7 同例），不改测试口径 |
| 7 | `make install DESTDIR` 在 `libtool --mode=install` 后 `chmod cannot access DESTDIR//lib/libtiger.a`（2026-09-18 package 阶段；此前 .la 清除已让链接与 `make check` 3/3 通过） | `--libdir=${prefix}/lib` 在 `--prefix=/` 下展开为 `//lib`，双斜杠进安装路径与 .la/.pc 元数据（babeltrace/1.5.11 同因；zeitgeist/1.0.4：`//lib` 还会污染 .pc 的 `-L`） | configure 改传绝对路径 `--bindir=/bin --sbindir=/bin --libdir=/lib --includedir=/include --oldincludedir=/include`（babeltrace 同款）；DESTDIR 落点不变（仍为包内 bin/lib/include），测试口径不变 |
| 8 | 上条 `--libdir=/lib` 后仍 `chmod cannot access DESTDIR/lib/libtiger.a`（2026-09-18 package 阶段；日志已显示 `test -z "/lib"` 即单斜杠生效） | `//lib` 假设被证伪：单斜杠下 libtool 安装仍失败，真因是 HMBS runtime `install` shim 在 `--mode=install` 下未实际拷贝（`--silent` 掩盖了真实 install 行），与 libdir 拼写无关；属安装器域而非配置域 | 新路线（与前三轮不同）：package() 改跑 `make install V=1`（暴露真实 install 行供下轮诊断）+ 安装前 `ls lib/.libs`/`grep libdir/old_library` 探针区分“没产出”与“没装上”；`make install` 抛异常时回退为已构建产物（`lib/.libs/libtiger.a[.so*]`、头文件、`.pc`）的 `copy()` 手动落盘（同 DESTDIR 布局），无产物才 re-raise；不改测试口径 |
| 9 | 包已构建成功（`make check` 3/3 通过、fallback 落盘 `libtiger.a`+头文件）后 `package_info(): ... includes package 'glib::', but such package is not a direct requirement`（2026-09-18 package_info 阶段） | `package_info()` 声明了 `glib::gobject-2.0`/`glib::glib-2.0` 链接项，但 `requirements()` 里 glib 仅为 `override=True`（版本 pin，不算 direct edge），Conan 2 校验拒绝非 direct 包的 component requires；与编译器/安装器无关 | glib 改回直接依赖 `self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)`（同版本 pin 不分叉，与 pango 所 pin 版本一致）；其余 override pin 不变，不改测试口径 |

## 源码修改

- `patches/0001-misc-autotools-config-sub.patch`（portability）：仅改
  `misc/autotools/config.sub`，4 个 hunk（详见上表 #1）。补丁由源文件 diff
  生成，已本地 `git apply --check` 验证；真机预检通过后 dev 轮可用
  refresh-patch 复核格式。

## 上游测试审计

- 归档共 100+ 条目：无 `tests/`、`test/`、`spec/` 目录，无 `*_test.c`、
  `test_*.py` 测试源；`examples/src/simple.c` 是读 stdin Ogg 流的演示程序。
- 顶层 `Makefile.am`：无 `TESTS`、`check_PROGRAMS`，仅有 `check-local`：
  ① Tiger 符号命名空间（nm 前缀检查）；② 内存分配封装检查；
  ③ 残留调试打印检查。均只用 NM/GREP 分析产物与源码，无需执行目标码，
  OHOS 交叉构建可完整运行。
- `configure.ac`：无测试框架注册（无 gtest/ctest/pytest）。
- 结论：上游 0 个单元/集成用例；`make check` 的 3 组 check-local 即上游
  全部可执行检查，`HMBS_UPSTREAM_TEST_RESULT(discovered=3, executed=3)`，
  详见 `test_package/MANIFEST.yml`。
- 证伪要求：消费者测试对渲染输出做非空校验（白底 clear 后首字节非零，
  非“空文件比空文件”）；PASS 行计数 + 退出码双重门禁。

## 依赖版本

- libkate/0.4.3（Kate 解码，公开头包含 `kate/kate.h`，transitive）
- cairo/1.18.4（transitive；与 gtk3 栈同版本）
- pango/1.50.14.1.1（transitive，提供 pangocairo；与 gtk3 栈同版本）
- W0 说明：本机 Windows 环境无法运行 conan download 预检；依赖版本按
  仓库已合入配方的 published/主流 pin 选择，待 HMBS 真机预检实际解析验证。

## 验证结果

```bash
# test_package：2 场景 17 断言（待真机预检回填实测数）
./test_tiger              # 版本查询 + 渲染器全生命周期 + 白底渲染输出校验（10）
./test_tiger --null-args  # NULL 参数故障注入（7）
# 上游：make check（3 组 check-local，待真机预检回填）
```

真机预检 evidence（HMBS 后台执行）回填后更新本节；PR 正文「上游测试用例通过率」
以预检日志为准。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libtiger.a | 静态库（默认；shared=True 时为 libtiger.so.5） |
| include/tiger/tiger.h、tiger_config.h | 公开头 |
| lib/pkgconfig/tiger.pc | pkg-config 描述（Requires: kate, pangocairo） |

## 注意事项

1. 本库为渲染库（R40）：test_package 不止调 version，还覆盖渲染器创建、
   cairo 缓冲绑定、无字体白底渲染与输出校验；但完整字幕渲染需 Kate 事件
   流与字体栈，超出消费者冒烟范围，已在 PR 补充说明如实声明。
2. Windows 检出注意：仓库同时存在 `archives/l/libXext` 与 `archives/l/libxext`
  （大小写仅差），Windows 工作树会碰撞产生虚假修改；与本 PR 无关，勿提交。
3. 本机另有 `archives/g/gama` 文件名含回车（`...patch\r\r`），Windows 无法
   检出，已用稀疏检出排除；属本地工作树限制，不影响 Linux 真机与 CI。
