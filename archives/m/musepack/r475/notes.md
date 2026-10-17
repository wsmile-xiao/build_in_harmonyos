# musepack r475 — HarmonyOS PC (aarch64, os=OHOS) 适配笔记

## 基本信息
- 上游源: https://files.musepack.net/source/musepack_src_r475.tar.gz (官方)
- 实测 sha256: a4b1742f997f83e1056142d556a8c20845ba764b70365ff9ccf2e3f81c427b2b
- 构建系统: CMake (上游 2009 年快照, 自带 configure.in 但以 CMakeLists.txt 为准)
- 语言: 纯 C (R47 lang-preflight detected=c, 兼容族通过)
- 依赖: libcuefile/r475 + libreplaygain/r475 (均已在 ohpcd 制品仓发布, W0 conan download 实测通过)
  - mpcgain ← libreplaygain (replaygain/gain_analysis.h + libreplaygain.a)
  - mpcchap ← libcuefile (cuetools/cuefile.h + libcuefile.a)

## 探索编译结论 (模式 B, CMake)
- 工具链: 本机 clang 15 (OHOS aarch64 目标), cmake 4.1.2
- 产物: libmpcdec.a / libmpcenc.a / libmpcpsy.a + bin 工具
  mpcdec/mpcenc/mpcgain/mpc2sv8/mpccut/mpcchap/wavcmp
- make install DESTDIR=staging → bin/ include/mpc/ lib/ 结构完整, RC=0
- make check: 上游无测试目标 (ctest 空集), 记录为上游事实
- 执行类冒烟 (mpcenc/mpcdec --version): 本沙箱域禁止执行新生成 ELF
  (hello world 亦 RC=126 Operation not permitted, 与知识 E052/E077 同源;
  binary-sign-tool selfSign + chmod 均无效), 属平台限制, 不阻塞编译验证。
  执行验证由 CI 执行机承担 (test_package 编解码回环 + CI conan test)。

## 源码修改清单 (探索阶段直接修改, 补丁由 refresh-patch --auto 生成)
1. CMakeLists.txt: CMAKE_MINIMUM_REQUIRED 2.4 → 3.5
   (CMake 4.x 移除 <3.5 兼容, 不改则 configure 直接失败)
2. CMakeLists.txt: set(CMAKE_C_FLAGS "-O3 ...") → 追加式 "${CMAKE_C_FLAGS} -O3 ... -fcommon"
   - 覆盖式写法会丢弃 Conan toolchain 注入的 CFLAGS (R33 关联)
   - -fcommon: mpc_decoder.c/requant.c 对 Res_bit/__Cc/__Dc 的多重
     tentative definition, 现代 clang 默认 -fno-common → ld.lld duplicate symbol
     (知识图谱未命中此模式, 已按 R31 沉淀草稿)
3. mpcenc/mpcenc.h: fpu_control.h 的 include 守卫由 __linux__ 收紧为
   __linux__ && __i386__ (该头仅 x86 glibc 提供; mpcenc.c 的 _FPU_GETCW
   使用点本就被 __i386__ 守卫, aarch64 为 IEEE-754 硬件控制无需该头)
   — portability 修复, 非 __OHOS__ 平台宏
4. mpcenc/keyboard.c: POSIX 分支补 #include <sys/time.h> / <sys/select.h>
   (struct timeval / fd_set / select 在部分 libc 不被 termios.h 间接引入;
   两个都是 POSIX 标准头, 非 __OHOS__ 平台宏)
5. libmpcdec/libmpcenc/libmpcpsy CMakeLists.txt: 输出库规范命名
   (OUTPUT_NAME mpcdec/mpcenc/mpcpsy, 去掉 _static 后缀与上游 autotools
   产物名对齐) + install(TARGETS ... ARCHIVE DESTINATION lib)
   (上游 CMake 版遗漏库安装规则, 只有工具安装)
6. include/CMakeLists.txt: INSTALL(DIRECTORY mpc ...) 加
   FILES_MATCHING PATTERN "*.h" (上游头文件目录带 .svn 元数据残留,
   不加会把 .svn 整个装进 include/)

## W3 本地 JC FAIL 差异分析（CI prdiff vs 本地 full，非本包缺陷）
finish Step5/10 W3 本地 CI 模拟的 junk_check FAIL（Junk Files: 3）全部命中
**git 已跟踪的上游既有文件**（git log -1 origin/main 自证，时间均早于本任务）：
- archives/e/embree/4.4.1/.submit-state.json   ← 7b69b0e2bc 2026-09-02 feat(embree): 4.4.1 适配完成
- archives/f/flatcv/0.3.0/.staging-verified    ← 6dd2761100 2026-08-31 【积分赛】feat: 适配 FlatCV 0.3.0
- archives/l/libmorton/0.2.12/.staging-verified ← 7b355aff78 2026-09-02 【知识库扩展】feat(libmorton): 0.2.12
- archives/g/goaccess/1.10.2/ncurses-headers.tar.gz ← 51eae6ae0e 2026-08-27 feat(goaccess): 1.10.2
（JC5 另 8 项隐藏文件同理，均为他人包目录既有文件）
结论：CI 侧 junk_check 为 prdiff 模式（ci/scripts/junk_check.sh 优先级 1，pr.diff
为唯一权威，只扫 PR 文件清单），本 PR 仅含 archives/m/musepack/ 与知识草稿 →
CI 必然 PASS；本地 FAIL 是本地 full 模式整仓扫描对上游既有文件的误报。
musepack 自身零命中，本包不引入任何垃圾文件。

## Conan 配方要点
- requirements: libcuefile/r475 + libreplaygain/r475 (精确版本)
- generate(): R49 build_folder 私有 prefix 注入 — 复制依赖包 include/lib
  到 os.path.join(self.build_folder, "prefix"), 通过 CMakeToolchain variables
  把 FIND_PATH/FIND_LIBRARY 结果变量 (REPLAY_GAIN_INCLUDE_DIR 等) 指向私有
  prefix; 禁止注入 /usr/local (PF6)
- SHARED=OFF: 全静态产物, 避免 .so RPATH/HMDFS 问题; mpcdec 非系统同名库,
  静态交付由 Conan 管理依赖链
- package_info: cpp_info.libs = ["mpcdec", "mpcenc", "mpcpsy"]
- commands.json (R38): 产物含 7 个命令行工具, 软件级声明 mpcenc/mpcdec/mpcgain
  为主命令
- test_package (R34): 自洽回环 — 生成 WAV → mpcenc 编码 .mpc → mpcdec 解码回
  PCM 校验非空 + 链接 libmpcdec 校验 SV8 streaminfo API; test_type=explicit
  (本沙箱不可执行, conan create 不跑 explicit 测试; CI 执行机通过 conan test 执行)
---

**编译结束**: 2026-09-03 00:23
**最终状态**: built
