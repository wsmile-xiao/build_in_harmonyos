# oggz 1.1.3 适配笔记 (OpenHarmony PC / aarch64)

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++ (musl, aarch64-linux-ohos)
- 平台: OpenHarmony PC aarch64 (uname -s = HarmonyOS)
- 状态: built (conan-verify G1-G4 + L2/L4/L5 通过; 未上传制品仓)

## 编译步骤
1. 源码: https://downloads.xiph.org/releases/liboggz/liboggz-1.1.3.tar.gz (sha256 2466d03b...656e2f)
2. conanfile.py source(): 手动 tarfile 解压(flatten liboggz-1.1.3/) + apply_conandata_patches
   补丁: 0001 config.guess HarmonyOS, 0002 config.sub linux-ohos, 0003 configure 临时目录 mkdir
3. generate(): PkgConfigDeps(libogg -> pkg-config 'ogg') + AutotoolsToolchain (shared=False => --enable-static/--disable-shared)
4. build(): python subprocess 用受控 env 驱动 configure && make -j1
5. package(): subprocess make install DESTDIR=<package_folder> -j1; 删除 *.la; OHOS ELF 签名 (bin 工具 12 个自带/补 .codesign)
6. 验证: conan create (含 test_package 真实调用 liboggz API) 通过; conan-verify 8 道门禁通过

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧 config.guess(2022) 无 HarmonyOS 分支 (E007) | patch-autotools-ohos.pl + config.sub kernel/OS 白名单 (E072) |
| 2 | config.status 报 "./confXXXXXX: Permission denied" | config.status 用 mktemp -d 在 CWD 建临时目录, OHOS HMDFS 不可用 (E002) | 0003-configure.patch 改为 plain mkdir (与 flac 同款) |
| 3 | conan get(strip_root) 报 PATCHES IsADirectoryError | tarball 顶层文件 PATCHES 与导出的小写 patches/ 目录在大小写不敏感沙箱 FS 上冲突 | source() 手动 tarfile 解压并跳过 PATCHES |
| 4 | conan 内 configure heredoc/管道失败 (cat - / sort - Permission denied) | DEFAULT_PREFIX/bin 的 coreutils shim 抢占 PATH (E540); conan self.run 每次重放 profile buildenv PATH | build() 用 python subprocess + 固定 PATH=/system/bin:/usr/bin:/bin:/data/service/hnp/bin:... |
| 5 | W3 build_and_test 报 timeout 无法执行 conan | timeout 解析到 usr/local/bin shim | 运行 finish 时前置 PATH 使 timeout 取 /usr/bin/timeout |
| 6 | test_package 编译找不到 <ogg/ogg.h> | libogg 配方 (cmake_layout) 未向 CMakeDeps 宣告 include 目录 | test_package generate() 注入 LIBOGG_INCLUDE_DIR |
| 7 | 平台运行时 .so 经 HMDFS 软链接无法加载 (本沙箱) | HMDFS symlink + musl loader 沙箱限制 | 默认静态打包(shared=False); 上游单测以实体 .so 复本直接运行全部通过 |

## 源码修改(补丁)
- 0001-config.guess.patch: HarmonyOS(uname -s) 分支 -> aarch64-unknown-linux-ohos
- 0002-config.sub.patch: ohos-linux 三元组 + ohos* OS + linux-ohos* kernel 白名单
- 0003-configure.patch: config.status 临时目录 mktemp -d -> mkdir

## 依赖版本
- libogg/1.3.6.1 (系统同名库, 强制静态 R26; 已在 ohpcd 发布)
- pkg-config / autotools / make (环境自带)

## 验证结果
- conan create 成功: 打包 liboggz.a + 14 个 oggz 头文件 + 13 个 CLI 工具 + oggz.pc + man
- test_package: test.c 调用 oggz_open_stdio(OGGZ_WRITE/READ)+oggz_close, ctest 1/1 Passed
- conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- 上游单元测试: src/tests 24 个测试二进制直接运行通过 (comment/io/write/read/seek 系列);
  make check 的 httpdate_test 因 libtool wrapper + HMDFS getcwd 环境无法经封装执行(环境限制, 非代码缺陷)
- OHOS ELF 签名: bin/ 12 个 ELF 均带 .codesign (binary-sign-tool 自签/保留)

## 交付物
| 文件 | 说明 |
|------|------|
| archives/o/oggz/1.1.3/conanfile.py | Conan 配方 (libogg/1.3.6.1 静态) |
| archives/o/oggz/1.1.3/conandata.yml | 官方源 + sha256 + 3 补丁 |
| archives/o/oggz/1.1.3/patches/ | 3 个 OHOS 平台补丁 |
| archives/o/oggz/1.1.3/test_package/ | test.c 真实调用 liboggz API (R34) |
| archives/o/oggz/commands.json | 13 个 CLI 工具声明 (R38) |

## 注意事项
- R1: 参数最少化 (仅 --prefix; conan 由 toolchain 传参)
- R26: libogg 静态; R32: os 判断 in ("Linux","OHOS"); R36: libogg 已发布; R37: 版本 1.1.3
- R39: URL 官方源 downloads.xiph.org
- R40: 多媒体库, 平台适配为 configure 层 (config.guess/sub/临时目录), 无 stub; 代码路径经单测验证
- 状态 built: conan-verify 通过但未做 conan upload / PR (本次为编译协作子任务)

---
**编译结束**: 2026-09-03 17:11
**最终状态**: built
