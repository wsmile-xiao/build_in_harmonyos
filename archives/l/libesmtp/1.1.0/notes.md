# libesmtp 1.1.0 适配笔记

## 软件识别

- libesmtp（上游仓库 https://github.com/libesmtp/libESMTP，tag v1.1.0，2021-06-04 发布）是 SMTP 客户端库，
  用于经由预配置 MTA 投递 RFC 2822 邮件，提供会话/消息/收件人/扩展（STARTTLS、DSN、CHUNKING、ETRN）API。
- 构建系统为 **Meson**（meson.build + meson_options.txt），无 configure 脚本，非 autotools。
- 许可证：LGPL-2.1-or-later（示例程序 GPL）。
- 产物：libesmtp.so（SOVERSION 6.2.0，由 CRA 8:0:2 算得）+ 公开头 libesmtp.h、auth-client.h
  + SASL 插件（login/plain/crammd5，openssl 存在时另有 ntlm）+ libesmtp-1.0.pc。
  examples/mail-file 演示程序仅编译不安装，故本包为纯库类型，无需 commands.json（R38）。

## 源码获取

- URL: https://github.com/libesmtp/libESMTP/archive/refs/tags/v1.1.0.tar.gz
- sha256: 32bc3614ca12d21c7d933f32d43410e8744b6f91fdca7732da9877a385e4e6c3
  （与 Buildroot libesmtp.mk 中 v1.1.0 一致，对应 GitHub 生成的同 tag 归档）
- 版本号策略（R37）：首次适配，直接使用上游版本 1.1.0。

## 上游测试审计（no_tests 判定依据）

结论：**上游发布包不存在任何测试套件**，故 test_package/MANIFEST.yml 写
`upstream_tests_exist: false` + 非空 upstream_test_audit，test_package 每轮
输出 HMBS_UPSTREAM_TEST_RESULT status=no_tests、discovered=0、executed=0。

- meson.build 全文无 `test()` 目标定义；targets 仅 library + 插件子目录 + examples；
- meson_options.txt 仅 7 个构建特性开关，无测试选项；
- 源码树无 tests/、test/、check/ 目录，无测试源码；
- examples/mail-file.c 为演示程序（openssl 存在才编译，不安装），非测试；
- 上游文档仅描述构建安装，无测试入口。

## 配方要点

1. **Meson + PkgConfigDeps**：上游用 `dependency('openssl')` 经 pkg-config 探测，
   配方以 PkgConfigDeps 生成 .pc，使 openssl/3.5.6 可被找到；MesonToolchain 设
   `tls=enabled`（STARTTLS 为核心能力，对应 smtp-tls.c 与 ntlm 插件）、
   `pthreads=enabled`、`lwres=disabled`（OHOS 无 libbind9，上游默认亦为 disabled），
   bdat/etrn/xusr/xdg 保持上游默认值 true。
2. **default_library 跟随 shared 选项**：上游 `library('esmtp')` 默认同时构建，
   配方按 shared 选项显式指定 shared/static。
3. **ar/ranlib 注入**：MesonToolchain 不把 compiler_executables 的 ar/ranlib 写进
   native 文件，沿用 cairo/libass 配方做法，补绝对路径进 conan_meson_native.ini。
4. **version-script 链接**：上游以 `-Wl,--version-script,libesmtp.map` 控制导出符号，
   OHOS lld 支持该参数，保持原样（若真机链接报错再评估）。
5. **R26**：libesmtp 非系统同名库（/lib 无 libesmtp.so），保持默认动态链接。
6. **R32**：validate 用 `in ("Linux", "OHOS")`；package_info system_libs 同口径。
7. **R33**：build() 无裸 shell 环境变量，编译器全部经 Toolchain 注入。
8. **依赖（R36）**：仅 openssl/3.5.6（制品仓已发布，多版本并存，3.5.6 为常用版本，
   cyrus-sasl 等配方在用），无链式缺失。

## 真机预检轮次记录

- **第 2 次聚焦修复（与前次不同策略）**：前两轮预检连续失败于依赖构建阶段——
  `openssl/3.5.6` 未固定 revision 时 conan 从 conancenter 下载 CCI recipe
  （rev 13f8f30151479797ca8a7c014856f849），它无条件 requires 上游 zlib/1.3.2，
  其 cmake 在 OHOS 下失败（System unknown HarmonyOS + compiler check），本包
  自身的 generate()/build() 尚未执行；第 1 轮仅在本包内透传 TMPDIR（E002），
  无法影响依赖包构建，故指纹重复失败。本轮改用 abuild-sudo/ppp/re 已验证先例：
  `self.requires("openssl/3.5.6#748fc4deb56588d6f8ce900b21e8eb0a")` 固定到 ohpcd
  的 OHOS 兼容 recipe（无 zlib 依赖，静态 no-shared），从依赖图层面消除上游
  zlib 构建；E002 透传保留作为本包自身 meson/ninja 临时文件的纵深防护。
- **第 3 次聚焦修复（与前次不同策略）**：openssl pin 生效后依赖图通过（包 ID
  变化、新失败定位到本包 `meson.configure()`）：`ERROR: Unknown compiler(s):
  [['/data/service/hnp/bin/clang']]`，`clang --version` 报 ENOENT——profile 硬
  编码的编译器路径在此预检 runner 上不存在。前次只修了依赖与 TMPDIR，未触及
  编译器路径。本轮新增编译器存在性探测与回退（bulletty/bubblewrap 先例改编为
  Meson 版）：conf 路径为文件时原样保留；缺失时按 PATH（hmbs 前置工具目录）、
  OHOS_NDK_HOME、版本无关 SDK glob 顺序解析，仅重写 native/cross 文件中“当前
  路径已不存在”的 `c`/`cpp` 项，并注入 ar/ranlib；SDK 树编译器按 bubblewrap
  先例将其 llvm/lib 前置 LD_LIBRARY_PATH（lld 的 libxml2 探测）。test_package
  同步：仅当 profile 编译器缺失时覆盖 CMAKE_C/CXX_COMPILER 二进制路径，
  sysroot/target 仍走工具链文件，断言计数不变。
- **第 4 次聚焦修复（与前三轮不同策略）**：前三轮分别解决 TMPDIR 只读、
  openssl CCI 依赖图、profile clang 缺失；本轮日志首次进入 meson dependency
  探测并失败于 `dependency('openssl')`：`Run-time dependency openssl found:
  NO (tried system)` + `Pkg-config for machine host machine not found`——缺的是
  pkg-config 可执行文件本身，而非 openssl.pc 内容。前三轮均未提供该工具，
  故旧假设（依赖版本/编译器路径/临时目录）已不再适用。本轮换新路线：参照
  harfbuzz 14.2.0.2 / cataract 1.0.0 / gxr 先例，`build_requirements()` 新增
  `tool_requires("pkgconf/3.0.4")`（archives/p/pkgconf/manifest.yaml 中已
  published 的 OHOS 修订），并在 `_patch_meson_machine_files()` 中按
  conf tools.gnu:pkg_config → build pkgconf 包 bin → PATH 顺序探测，仅当
  native/cross 文件缺 `pkg-config` 项时注入绝对路径；已有项保持不动。
  PkgConfigDeps 生成的 openssl.pc 内容与查找路径不变，测试口径未动。

## test_package 设计（R34/L0d/L0e）

- 第 5 轮：真机首次进入链接阶段，`examples/mail-file` 报 `undefined symbol: getpass`（musl 系 OHOS libc 已删除该废弃函数，上游自注 FIXME；demo 不安装）；顶层 `subdir('examples')` 注释掉，库/插件/pkg-config 不变。
- 第 6/7 轮：首版 unified-diff 补丁先后失败（先 hunk 计数 11 应为 12，后 hunk 行号 168 在真实包上漂移到 sources 列表致 Failed to apply patch）；改用行号无关的 `replace_in_file` 在 source() 内替换，删除 patches/ 目录与 conandata patches 节，彻底消除行号漂移。
- 第 8 轮：主库编译通过（replace_in_file 策略生效），test_package 倒在 CMakeToolchain 钉死的 /data/service/hnp/bin/clang（-D 变量覆盖无效）；改用新策略：解析器新增 $HOME/.harmonybrew 与 /storage/Users/*/.harmonybrew 显式探测，并在 cmake.configure 前直接重写 conan_toolchain.cmake 中已不存在的编译器路径，-D 变量保留为双保险。

- test.c：离线调用真实 API，全程不联网（不调用 smtp_start_session）：
  建会话 → 版本前缀校验（参照 "1.1.0" 非空，避免空比空）→ 服务器/主机名设置 →
  消息组装（发件人/收件人/头/消息体/DSN/尺寸估计）→ enumerate 回调计数 →
  超时配置，共 6 组断言；失败返回非零。
- conanfile.py：CMake 构建 + 运行，解析 `PASS[n/6]` 行计数输出
  HMBS_TEST_PACKAGE_RESULT（discovered=6），随后复发 no_tests 上游标记
  （防包缓存命中轮次缺证据）；末尾 self.run() 满足 L0d。
- 直链 `-lesmtp`（非 dlopen），L1e 破坏性反向验证可在编译/链接期失败。

## 待真机预检确认

- meson configure/build 在 OHOS clang 下的一次性通过情况；
- version-script 在 OHOS lld 下的行为；
- openssl 传递依赖的运行时加载（LD_LIBRARY_PATH 收集逻辑）；
- 6 组断言在真机的实际表现。
