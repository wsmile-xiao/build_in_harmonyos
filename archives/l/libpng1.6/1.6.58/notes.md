# libpng1.6 1.6.58 适配笔记

## 编译环境
- 构建系统: autotools
- 编写日期: 2026-09-19
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: 首轮未提交工作树，真机预检待执行

## 上游信息
- 上游仓库: https://github.com/pnggroup/libpng（发布页 http://www.libpng.org/）
- 源码包: https://downloads.sourceforge.net/libpng/libpng-1.6.58.tar.gz
- 构建方式: autotools（避开 CMake 在 OHOS 上的无 SONAME 坑，libtool 自管 SONAME libpng16.so.16）
- 上游测试: `make check`，tests/ 目录共 36 项（pngtest/pnggetset/pngvalid 系列 16 项、pngstest 系列 11 项、pngunknown 系列 7 项、pngimage 2 项，详见 test_package/MANIFEST.yml）

## 编译步骤

autotools 标准流程：POSIX shell 驱动 configure（triplet 取自 clang -dumpmachine）→ `make -j1` → `make check` → `make install`。zlib 经 AutotoolsDeps + PkgConfigDeps 注入。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | uname -s 返回 HarmonyOS | 用 POSIX shell 跑 configure，以目标 C 编译器 `-dumpmachine` 结果提供 native build triplet |
| 2 | AC_CHECK_LIB([z]) 找不到 zlib | 需注入 zlib 的 -I/-L/-lz | AutotoolsDeps + PkgConfigDeps；native 编译 conftest 链接探测通过 |
| 3 | config.status 写 subs1.awk 失败 | Autoconf 私有 `umask 077` 与目录权限冲突 | 把 configure 拷贝到 build 目录的临时副本，`umask 077` 放宽为 `umask 022`，加 `--srcdir`，用后删除 |
| 4 | 测试二进制 Permission denied | 平台要求 ELF 先签名 | shared 构建先给 `.libs/*` ELF 做自签名（.codesign），再执行 `make -j1 check LOG_COMPILER=<posix shell>` |
| 5 | 嵌套 pngstest 驱动直接 exec 脚本 | 脚本无执行位时调用失败 | 构建时把 `exec "${srcdir}/tests/pngstest"` 改写为经 POSIX shell 调用（仅调用方式，不改测试断言） |
| 6 | `.pc` 前缀与 config shell 残留 | install 产物含绝对前缀与配置脚本 | 重定位两个 `.pc` 的 prefix，删除 `.la` 与 `libpng-config` 脚本 |

## 源码修改

无 patches/ 补丁（构建开关 + conanfile 适配即可，上游测试断言零修改）。

## 依赖版本

- zlib/1.3.1.1（ohpcd 站内 Makefile 静态+PIC；conancenter 的 zlib/1.3.2 为 CMake，在本 worker 报未知 HarmonyOS 平台 + 只读 /tmp，见本轮预检）

## 验证结果

- 待真机预检：conan create（shared/static 双配置）+ 上游 `make check` 36 项 + test_package 消费者测试。
- 本配方逻辑与已验证的 libpng/1.6.58.1 同源（同上游源码、同依赖、同测试清单），仅包名改为 libpng1.6。

## 2026-09-19 preflight fix
- FileNotFoundError /data/service/hnp/bin/clang：_c_compiler 不再盲信 conf 绝对路径，仅存在时采用，否则回退 PATH clang/cc/gcc（主配方+test_package 同改）。
- conandata 源地址改为有序列表（download.sourceforge.net 在前、官方 downloads 在后），sha256 不变；首轮下载曾在 twds 镜像超时后重试成功，加回退提高可靠性。

## 2026-09-19 preflight fix v2
- 同指纹第 2 次失败：v1 只修了 Python 侧寻址（_c_compiler 回退有 WARN 日志为证），但 configure 仍报 checking for gcc... /data/service/hnp/bin/clang 且 C compiler cannot create executables，证明 conanbuild 环境注入的失效 CC 覆盖了 Python 侧回退。
- 不同策略：运行时版本命令探活（_probe_live_program 跑 --version）逐个验证 conf c / PATH clang/cc/gcc（含 conf 绝对值 basename 回退），命中才采用；_live_cc_exports 把活体 CC/CXX（含 ac_cv_prog_CC 等 autoconf 缓存变量）内联 export 到 configure/make/check/install 全程 shell 前缀，覆盖 conanbuild 失效值；_build_environment 同步 define CC/CXX 做双保险；test_package 同改探活。

## 2026-09-20 preflight fix: install-man3 Error 64
- 现象：编译+上游 make check 36/36 已通过，package() 的 make install 在 install-man3 挂掉：\`runtime/.../bin/install -c -m 644 libpng.3 libpngpf.3 DESTDIR/share/man/man3\` 报 Error 64。
- 根因：HMBS install shim 仅接受单文件双参调用，多源到目录形态直接 exit 64（EX_USAGE）；与 xeyes/libICE、adms、torsocks 同款 E182/E188 家族。上一轮活体编译器探活已生效（本次 configure/make/check 全过），与本次失败无关。
- 方案（不同路线/参考已过门禁先例）：新增 _write_install_shim（cp/mkdir 语义，多源时 mkdir -p 目标目录，chmod 容错，os.open 0o755 落盘不依赖 chmod 能力）+ _redirect_install_to_shim（改写 build/source 下所有生成 Makefile 的 INSTALL 变量，INSTALL_DATA/PROGRAM 自动跟随）；build() 在 configure 后接线，package() 在 make install 前再次确保接线。
- 未改测试口径：上游 36 项与 test_package 不变。
