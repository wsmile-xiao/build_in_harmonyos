# libxmlb 0.3.19 编译笔记

## 编译信息
- **软件**: libxmlb
- **版本**: 0.3.19
- **构建系统**: meson (>=0.60, 实测 1.11.1)
- **产物类型**: 共享库 libxmlb.so.2.0.0 + xb-tool CLI
- **编译日期**: 2026-09-17（conan 适配）；2026-05-26（历史手工编译）

## 历史（2026-05-26 手工编译，status=built）
手工 meson 编译成功，遗留三个问题：
1. glib 预编译包 libintl 静态库被 meson 链接为动态 → undefined symbol（当时以 sed 改 build.ninja 绕过）
2. 测试因 LD_LIBRARY_PATH 缺失无法运行，状态降级 built
3. 无 conan 配方、无 test_package

## 前序会话（2026-09-16，同分支 8ab9ea1b8）
前一 AI 会话已在 feat/libxmlb-0.3.19 分支提交完整 conan 适配（glib/2.88.0 静态 +
xz/5.6.2 + zstd/1.5.6，CMake test_package），但推送后未创建 PR、未经 CI/AI 检视。
其知识草稿（静态 glib 双实例 GObject 类型系统冲突、liblzma.pc shim）验证了静态
glib 路线的根本问题——草稿自身给出的"长期正解：依赖方 glib 提供 shared=True
变体"正是 glib/2.88.3。本会话在原分支上继续优化：切换 glib/2.88.3 共享构建、
liblzma/5.8.1 直连（消除 pc shim）、上游测试 49/49 原生执行（R51）、ELF 全量重签
（含 xb-tool）、test_package 改 meson+pkg-config 并驱动 xb-tool 留档验证、
conandata 改用官方 release tarball（前序 git-archive tarball + gh-proxy 首位镜像
有 PF7 拦截风险）。保留其两份知识草稿，另沉淀本会话两条。

## 本次 conan 适配（2026-09-17）
以 glib-networking 2.90.0 / gtk 3.24.43 / accountsservice 26.27.3 的 CI 通过模式为底稿重写。

### 依赖（W0 已验证 ohpcd 制品仓发布）
- glib/2.88.3（**共享构建**）— libxmlb 暴露 GObject 类型（xb_silo_get_type 等），
  静态 glib 会在同进程动态 glib 场景下双重注册类型系统（glib-networking 先例）。
  glib 2.88.3 内嵌 proxy-libintl，历史 libintl 问题就此消失。
- liblzma/5.8.1（静态）
- zstd/1.5.7.1（共享）

### 关键适配点
1. **glib .pc 修正层**：glib 安装 .pc 为 prefix=/ 且 Requires(.private) 列静态内部依赖
   （proxy-libintl/zlib/libpcre2-8/libffi）。复制到 glib-pc-fix/ 重写 prefix、剥离虚假
   Requires，置于 PKG_CONFIG_PATH 首位。由此 gio-unix-2.0.pc（glib 包独有，
   PkgConfigDeps 不生成）可解析 → xb-tool 的 SIGINT 处理（g_unix_signal_add_full）保留，
   无裁剪。
2. **不裁剪**：lzma/zstd 上游 auto 特性显式 enabled（上游测试 test.xml.xz/test.xml.zst
   覆盖）；cli=true（xb-tool）；tests=true（49 用例全部原生执行）。
   仅禁用 introspection/gtkdoc（OHOS worker 无 g-ir-scanner/gtkdoc-scan，GIR 为绑定
   产物非 C API 组成部分，与仓库内 glib/gtk/at-spi2-core 一致）。
3. **ELF 重签**：meson install 改写 ELF（DT_RUNPATH 清理）使 lld 链接期自签失效
   （E077）。安装后 llvm-objcopy 剥旧 .codesign + binary-sign-tool 重签
   （PACKAGE_CODESIGN=PASS signed_elfs=4：libxmlb.so.2.0.0/.so.2/.so + xb-tool）。
   tc.strip=None 防二次改写。
4. **.so 别名物化**：libxmlb.so.2/libxmlb.so 由符号链接物化为常规文件拷贝
   （HMDFS，glib/gtk 打包模式）。
5. **installed-tests 路径**：conan MesonToolchain 把 libexecdir 映射到 bindir，
   installed-tests 落在 bin/installed-tests —— package() 中 rmdir 移除
   （glib 打包惯例，测试已在 build() 阶段原生跑过）。
6. **AR/AS/STRIP/NM/RANLIB**：CI worker 导出 llvm-* 裸名 PATH 不可见 → 弹出并按
   绝对路径锁定（glib-networking 先例）。
7. **xmlb.pc prefix 修正**：meson 以 --prefix=/ 安装，xmlb.pc 的 prefix 重写为
   package_folder。
8. **组件 requires 引用形态**：glib/2.88.3 组件名为 glib/gobject/gio（带
   pkg_config_name 属性映射 glib-2.0 等），component requires 须写 glib::glib ——
   首次跑 conan create 即因 glib::glib-2.0 报 "Component not found" 被拦下。

### 上游测试（R51 三步法）
1. **清点**：src/xb-self-test.c 单文件，g_test_add_func 注册 51 处；49 默认执行 +
   2 个 perf-only（threading/speed，g_test_perf() 才注册）。
2. **运行**：build() 内 meson test 原生执行（LD_LIBRARY_PATH 覆盖 glib/zstd/构建
   目录，TMPDIR 指向可写目录——根 /tmp 只读）。
3. **结果**：**49/49 全部通过**（1/1 xb-self-test OK，TAP 0 not-ok；conan create
   日志留档）。消费者测试 test_package 7 CHECK + 4 硬退出全过，并驱动包内
   xb-tool compile + query 真实执行（conanrun 环境，输出随 CI 日志留档）。

### W3 本地 CI 模拟结果（如实记录）
- L0=pass（结构完整性）L1=pass（上游测试 + test_package，L1e 破坏性反证通过）
- **L2=skip（非阻塞）**：L2 冒烟裸跑 bin/xb-tool（无 LD_LIBRARY_PATH），动态链接
  的 conan CLI 无法解析 libxmlb.so.2/glib —— conan 共享依赖 CLI 的预期行为；
  xb-tool 的真实执行验证由 test_package test() 以 conanrun 环境完成并留档。
- L4=pass（无补丁污染）L5=pass（bin/ 有产物）整体 1/1 成功。
- 注：xb-tool 无 --version 选项（GOptionContext 仅 -h/--help），--help 在
  conanrun 下正常。

### meson 配置
```
meson setup builddir --prefix=/ \
  -Ddefault_library=shared -Dwrap_mode=nodownload \
  -Dintrospection=false -Dgtkdoc=false -Dtests=true \
  -Dlzma=enabled -Dzstd=enabled -Dcli=true
```

### 编译产物（conan 包）
- lib/libxmlb.so.2.0.0（+ 物化别名 .so.2/.so）
- bin/xb-tool（compile/query/dump/export 子命令；test_package test() 中以
  conanrun 环境真实执行 compile+query 并随 CI 日志留档）
- include/libxmlb-2/{xmlb.h, libxmlb/xb-*.h}
- lib/pkgconfig/xmlb.pc

### 遗留
无 — conan verify（G1-G4）与 W3 本地 CI 模拟（L0/L1/L4/L5 pass，L2 按设计
skip，整体 1/1 成功）通过，上游测试 49/49 全过。upload 由 PR 合并 main 后
CI 执行（R29），届时状态可升级 published。

编译状态: built
---

**编译结束**: 2026-09-17 03:36
**最终状态**: built
