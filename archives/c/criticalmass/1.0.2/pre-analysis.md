# criticalmass 1.0.2 HarmonyOS PC 预分析

## 结论

适配风险中等偏高，但均有对策（详见风险表）。项目是 SDL 1.2/OpenGL C++ 老游戏
（autotools automake 1.4 era，configure 3583 行生成物），主要风险集中在：GL 库缺失
（--enable-dyngl 动态解析）、SDL 1.2 栈发现机制（AC_ARG_VAR 显式注入）、2012 版
config.guess/config.sub 不识别 OHOS（FSF 2024 覆盖 + 双三元组）、resource.dat/Packer
打包链（补丁改为运行时直读 data/ 目录）、捆绑 2009 版 curl 子树（移除，改 conan 制品）。
上游零测试，验证以 test_package 的 --version 冒烟承担。

## 平台扫描

| 项目 | 结果 | 处理 |
|---|---|---|
| 构建系统 | Autotools（automake 1.4 era） | 直接补丁 configure/Makefile.in 生成物，不重跑 autogen；AutotoolsToolchain + AutotoolsDeps |
| 必需依赖 | SDL 1.2 API、SDL_image、SDL_mixer、png16、z、m、curl | sdl12-compat/1.2.68、sdl-image/1.2.12、sdl-mixer/1.2.12（⚠️ 见依赖缺口）、libpng/1.6.58（png16）、zlib/1.3.1.1 传递、musl libm、curl/8.15.0.1 |
| GL | configure.in:109-110 在 TARGET=UNIX 且非 dyngl 时 AC_CHECK_LIB(GL) | OHOS 无 libGL.so → 必传 `--enable-dyngl`（DYNAMIC_GL 经 SDL_GL_GetProcAddress 运行时解析） |
| SDL 发现 | 老栈只有 sdl-config 脚本路径，无 pkg-config "sdl" 模块 | patches/0003 加 AC_ARG_VAR(SDL_CFLAGS, SDL_LIBS)，配方显式注入 |
| 交叉编译 | conftest 运行探测（无签名 ELF 无法在 worker 沙箱运行）；config.status mktemp(0700) HMDFS 临时目录不可写 | 双三元组 `--build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos` 强制交叉模式，跳过运行探测 |
| config.guess/config.sub | 2012 旧版不识别 aarch64-unknown-linux-ohos | files/ 打包 FSF 2024 版，build() 拷入源码根（cheops 先例） |
| 打包链 | resource.dat 由 tools/Packer 生成（pkgdata_DATA 安装）；data/ 6 个子目录非 automake install 目标 | patches/0006 移除 resource.dat 生成链、运行时直读 data/；package() 手工拷贝 share/Critical_Mass/data/ |
| 捆绑 curl | tarball 自带 2009 版 curl/ 子树（AC_CONFIG_SUBDIRS） | patches/0001 移除引用，改 conan curl/8.15.0.1（game/OnlineUpdate.cpp） |
| libpng | configure.in 检查 png12 旧名 | patches/0002 改 png16，依赖 libpng/1.6.58（libs=["png16"]） |
| 产物签名 | OHOS ELF 未签名运行报 Operation not permitted | package() 内 llvm-objcopy --remove-section .codesign + binary-sign-tool sign -selfSign 1（julius 先例） |
| 并行构建 | HMDFS 上 make 并行 mkfifo/jobserver 问题 | make -j1（julius/cheops 先例） |
| 上游测试 | 0（无 test/ 目录、无 AC_CONFIG_TESTDIR/TESTS） | test_package 自建 `critter --version` 断言 "Critical_Mass 1.0.2"（0004 补丁使其在 SDL/GL 初始化前退出） |

## 风险表（R1-R9）

| # | 风险 | 影响 | 对策 | 状态 |
|---|------|------|------|------|
| R1 | resource.dat/Packer 打包链 | 构建期运行 Packer 生成资源包，OHOS 上无意义且有失败面 | 0006 补丁移除生成链，运行时直读 data/ | ✅ 已解 |
| R2 | libGL.so 缺失 | configure AC_CHECK_LIB(GL) 失败 | --enable-dyngl 动态解析 | ✅ 已解 |
| R3 | configure 重置 clang CFLAGS/CXXFLAGS | 工具链标志丢失 | 0005 补丁保护 | ✅ 已解 |
| R4 | config.sub 2012 不认 -ohos | configure 报 Invalid configuration | FSF 2024 config.sub/g uess 覆盖 + 双三元组 | ✅ 已解 |
| R5 | curl 头/库无上游检查 | 链接失败或隐式缺失 | requirements 声明 curl/8.15.0.1，AutotoolsDeps 聚合注入 | ✅ 已解 |
| R6 | sdl-config 缺失/路径错误 | SDL 探测失败 | 0003 AC_ARG_VAR + 配方注入 SDL_CFLAGS/SDL_LIBS | ✅ 已解 |
| R7 | conftest 运行探测 / mktemp umask 077 | configure 失败或半成品 Makefile | 双三元组强制交叉 + 0001 规避 | ✅ 已解 |
| R8 | data/ 非 automake install 目标 | 运行缺资源 | package() 拷贝 6 子目录到 share/Critical_Mass/data/ | ✅ 已解 |
| R9 | HMDFS 并行 mkfifo | make 卡死/失败 | make -j1 | ✅ 已解 |

## 测试边界

上游零测试。游戏本体需显示/输入/音频，无法在非交互沙箱运行真实对局（客观限制，
备注记录）。可验证面：`critter --version`（0004 补丁在 SDL/GL 初始化前处理，stdout
输出版本后 exit(0)），test_package 断言 stdout 含 `Critical_Mass 1.0.2`。

## 已知缺口 / 阻塞

- **sdl-mixer/1.2.12 未合入 origin/main、未发布 ohpcd**（仅本地 + 远端分支
  `feat/sdl-mixer-1.2.12`）。CI/preflight 若按 ohpcd 解析不到该制品，conan create
  会缺依赖失败——属依赖交付缺口，非本库代码问题，检验时说明（用户已确认依赖项
  不阻塞，届时说明即可）。
- SourceForge 官方 /download 直连在 CI/本环境不可靠（HTML 拦截/截断，SHA-256 不符），
  已改用实测校验一致的 macports/gentoo 镜像（conandata.yml url 列表）。