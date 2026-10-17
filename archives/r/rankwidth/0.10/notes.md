# rankwidth 0.10 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-10-03
- 编译器: clang/clang++
- 状态: built（待真机 rule4 验证后由 HMBS 统一提交）
- 适配路径：路径 A（基础适配）
- 申请人：yinuoguo，队伍名称：干

## 上游信息
- 名称：rankwidth（源码包名 rw-0.10.tar.gz，库名 librw，头文件 rw.h）
- 版本：0.10（2025-12-16 发布，355.8 kB）
- 仓库地址：https://sourceforge.net/projects/rankwidth/
- 源码 URL：https://downloads.sourceforge.net/project/rankwidth/rw-0.10.tar.gz
- sha256：89a8ed364893ac1b70ab70a152e3e7db3cf348bb69098aa6dbb969639df927db（MSYS2 PKGBUILD 与 SageMath checksums.ini 交叉确认一致）
- 许可证：GPL-2.0-or-later
- 描述：计算图的 rank-width 与 rank-decomposition 的 C 库/程序

## 依赖版本
- 无外部依赖（library-only 形态）。SageMath spkg 声明 no dependencies；Gentoo rw-0.10 仅 RDEPEND 与 xpaint 的 librw.so 文件冲突，无构建依赖。
- 刻意不引入 igraph：`rw`/`simplerw` 可执行文件才需要 igraph（MSYS2 depends igraph；Gentoo 注释 "executable depends on igraph"），本适配按 Gentoo 同款 `--disable-executable` 只构建 librw，避免把 igraph（含 bundled ~10 库、libxml2/GLPK/ARPACK 可选依赖）拖入闭包。

## 编译步骤

实际编译（真机 OHOS aarch64，由 HMBS 预检执行）：
```bash
sh ./configure --disable-executable --prefix=/ --enable-static --disable-shared
make -j1
make check   # 上游无测试套件，no-op 通过，仅保留 L1c 痕迹
make install DESTDIR=<package_folder>
```

本地未执行 conan（按任务守则，真机验证由 HMBS 后台统一执行）。

## 上游测试审计（无正式套件，有文档化烟雾，已提升为回归）
- rw-0.10.tar.gz 实测 24 条目：无 tests/ 或 test/ 目录；Makefile.am（534 字节）仅 librw.la + 条件 rw，无 TESTS/check_PROGRAMS；configure.ac（816 字节）仅 --enable-executable + 可选 igraph 探测。
- Alpine aports testing/rankwidth/APKBUILD（0.9）：`options="!check" # no test suite`；Gentoo rw-0.10 全程无测试阶段；NixOS 注记 check phase is empty；MSYS2 check() 为空 stub。
- README（1526 字节）文档化烟雾：`rw --edgelist example_graphs/igrid`；example_graphs 含 grid（50 字节，9 点）、igrid（358 字节，20 点）、Hangematte（110 字节，14 点）。
- simplerw.c（4880 字节）需 igraph.h，library-only（--disable-executable，Gentoo 同策略）无法原样构建可执行文件，故以 igraph-free 驱动保留 verbatim calculate_level/get_rw 循环（见 upstream_smoke.c 溯源头），数据文件逐字节 vendor。
- 结论：无正式套件但有 1 个文档化烟雾 x 3 图 = 上游总数 3；MANIFEST 声明 upstream_tests_exist: true + auto + 12 条审计 + 3 条 upstream_tests，真机逐图 exit-code 判定。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 本机无法下载 SourceForge 源码（403） | 本机网络对 sourceforge 限制 | 采用 MSYS2/Sage/Gentoo 三方交叉确认的 URL+sha256，不在配方中硬编码镜像；conandata 保留官方 URL 列表，CI 按官方通道下载 |
| 2 | 可执行文件依赖 igraph，闭包过重 | simplerw.c 含 igraph.h（Alpine igraph-1.0.0.patch 可证） | `--disable-executable` 只构建 librw，与 Gentoo 0.10 同策略；PR 正文如实说明 |
| 3 | Windows 检出主干时大小写冲突（libXext/libxext）与 gama 补丁文件名含 CR | 上游文件名在大小写不敏感文件系统非法 | 本地对冲突路径设 skip-worktree，不纳入本 PR；本 PR 仅含 archives/r/rankwidth |
| 4 | rw.h 具体 API 签名无法在本机直接查看源码 | SourceForge 直连被拒 | 以 SageMath rankwidth.pxd（cdef extern from "rw.h"）为 API 真源：init_rw_dec/destroy_rw/calculate_level/get_rw + cslots/adjacency_matrix；测试仅调用有把握的四个函数，不直触全局变量，避免头文件版本漂移导致编译失败 |
| 5 | 真机 configure 后 config.status 报 can't create ./conffWpDiI/subs1.awk: Permission denied | HMDFS 对 mktemp -d "./confXXXXXX" 建目录强制 setgid 得 owner 不可写目录（E011/E129；HMBS 诊断 unsafe_local_mktemp），configure 内 config.status 后续写临时文件失败 | 最小适配：configure/config.status 内 umask 077→022；当 HMBS_AUTOCONF_MKTEMP_FALLBACK=1 时仅 configure 阶段前置 mktemp 垫片（*conf* 返回失败触发 mkdir 回退，其余委托真实 mktemp），configure 后移出 PATH；TMPDIR 沿用 HMBS 注入可写目录；不跳过 make check 与 test_package |
| 6 | 真机 package() 的 install-dist_docDATA 报 Error 64（EX_USAGE） | HMBS install 垫片仅接受单文件双参调用，automake 把 README+example_graphs 多文档批量进一次 `install -c -m 644 a b c dir/`（lzop/1.04、adms/2.3.7 同族；含非 ASCII 名 Hängematte） | 安装工具层最小适配：package() 内写 cp/mkdir 语义的多文件 install 垫片（chmod 最佳努力，适配 CHMOD=0）并重定向所有生成 Makefile 的 INSTALL 变量；文档照常安装，不跳过任何安装目标与测试 |
| 7 | 真机 test_package 的 cmake 在 project() 处报 CMAKE_C_COMPILER 为 /data/service/hnp/bin/clang 不可用 | ohos profile 把 tools.build:compiler_executables 钉死在旧路径，真机 clang 已迁移至 PATH（如 ~/usr/local/bin），vanilla CMakeToolchain 原文烘焙死路径（bzrtp/5.3.105、ots/0.5.0 同族） | test_package 增加显式 generate()：conf→PATH 探测可用编译器，经 CMAKE_C/CXX_COMPILER 缓存变量强制传入并补丁已生成工具链文件；同步生成 VirtualRunEnv 供 conanrun；不改测试口径与用例数 |
| 8 | 2026-10-05 真机预检 compile 阶段 tar child process Cannot fork Out of memory + Error is not recoverable，上游测试 0/0/0，无配方帧指向 | 整机 RAM 耗尽致 fork 失败，非配方逻辑：本包源码仅 355.8 kB 且已单任务 make -j1，无并行可降；tar 解包期配方代码几乎尚未运行，调编译优化旗对该阶段零作用；与 shell/编译器/umask/install/编译器钉死层均无关，属真机环境故障（守则：工具链临时故障停留等待；zurl/1.12.0 #42 同指纹判环境故障零改动等待；kyua 第二十六轮明示解包期 fork 失败时调 flag 无效） | 功能代码零改动：不叠加任何配方/补丁/测试改动以保 #1-#7 验证链有效待复检；仅追加本条诊断记录；待健康真机复检，若推进到 configure/make/check 则按原链继续，若同 OOM 重现则转后端核查 runner 内存/cgroup 配额 |

| 9 | 2026-10-05 真机 evidence 门 incomplete：清单表明上游存在测试，no_tests/0 不允许通过 | HMBS 清单把 README 文档化烟雾计为上游测试，与配方 no_tests/0 冲突；verbatim simplerw 需 igraph 无法原样运行 | 按 libarcus/5.0.0 经验提升捆绑烟雾为回归：新增 upstream_smoke.c（保留 verbatim 计算循环，igraph I/O 换最小 edgelist 解析）+ 3 图 vendor + test_package 首跑冒烟并以 exit-code 发 passed 标记，主包删除 no_tests 标记，MANIFEST 改 exist:true/total:3/auto |

## 源码修改
- 无 patches/。library-only 开关通过 configure 参数实现，无需改源码；R8 平台宏零引入。

## 验证结果
```bash
# 真机预检（HMBS 后台执行，环境与官方 CI 同源）：
# - conan create archives/r/rankwidth/0.10（含 make check 空通过 + upstream_smoke 3 图 + test_package 4/4）
# - 上游测试：3/3（conan-smoke，逐图 exit-code，igrid 为 README 原生示例）
# - 新增测试：4/4（test_rankwidth.c 四个真实 API 场景）
# 本轮为工作树准备轮，未执行真机验证；数字待 HMBS 预检回填，以预检日志为准。
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方（library-only，主包不发 upstream 标记，证据由 test_package 发） |
| conandata.yml | 官方 URL 列表 + sha256 |
| test_package/test_rankwidth.c | 4 个真实 rw.h API 场景（init/calculate/get/destroy，n=1/2/3/4） |
| test_package/CMakeLists.txt + conanfile.py | 构建 test_rankwidth + upstream_smoke，输出 HMBS_TEST_PACKAGE_RESULT + HMBS_UPSTREAM_TEST_RESULT |
| test_package/MANIFEST.yml | upstream 3 图声明（exist:true/auto/12 条审计）+ 新增 4 用例声明 |
| test_package/upstream_smoke.c + grid/igrid/hangematte.edgelist | igraph-free 烟雾驱动 + 3 图逐字节 vendor（含溯源头） |

## 注意事项
- 本包为纯库包（package_type=library，bindirs 为空），按 R38 不需要软件级 commands.json。
- shared 默认为 False（静态），符合非系统同名库的常规做法；librw.so 与 xpaint 的文件冲突仅存在于 Gentoo 语境，OHOS 制品仓无此冲突。
- 首次适配版本号直接使用上游 0.10，无后缀（R37）。
