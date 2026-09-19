# seccomp 2.6.1（libseccomp）适配笔记

> 包名说明：本件以 `seccomp` 为包名入库（多包名并存——archives/l/libseccomp/ 的 2.5.x~2.6.1 归档保持不动）。配方技术路线与 libseccomp/2.6.1 已合入配方同源（同 tag v2.6.1、同 sha256）。

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | seccomp（= libseccomp） |
| 版本 | 2.6.1 |
| 上游 | https://github.com/seccomp/libseccomp（tag v2.6.1） |
| 构建系统 | autotools |
| 语言 | 纯 C，零外部依赖 |
| 许可证 | LGPL-2.1 |

## 二、上游验证（W0）
- tag v2.6.1 实存：GitHub releases/libseccomp-2.6.1.tar.gz ✅
- sha256：`501f66c667225d53791b97e1d7cf85ab764c297d04881f60f38f451c4b0ee1be`（本地下载实测一致）
- 依赖：无（纯 C 零依赖库）

## 三、OHOS 适配要点（与 libseccomp 系已合入配方同款，实测过的结论）
1. **E011（HMDFS 执行位）**：源码复制到 `/data/storage/el2/base/cache/seccomp-src-<build_id>` 再 configure/make；work 目录加 package_id 后缀防 CI 并发冲突。
2. **E007（config.guess 不识别 OHOS）**：显式 `--build=aarch64-unknown-linux-gnu`（交叉编译形态）。
3. **configure 链接检查 patch（el2 沙箱）**：
   - cross.cache 预置 `ac_cv_prog_cc_works=yes` / `ac_cv_prog_cc_cross=yes` / `lt_cv_deplibs_check_method=pass_all` / `lt_cv_ld_force_load=no`
   - `(eval "$ac_link_default") 2>&5` → `(eval "touch conftest") 2>&5`（works 检查）
   - `checking for suffix of executables` 段的 `(eval "$ac_link") 2>&5` → touch（exeext 探测）
   - `if test "$cross_compiling" = maybe` → `if true`（强制 cross_compiling=yes）
4. **make 顺序**：先 `make -C src`（libseccomp.so）再 `make -C tools`（scmp_sys_resolver 链接依赖）再全量 `make -j1`——CI 上直接全量 make 会因 src/.libs 未生成而链接失败（实测）。
5. **tests/regression toybox 兼容**：`tail -n +0 --pid=$pid -f $log` → `tail -n +0 $log`（toybox tail 不支持 --pid，-f 会永久挂起逃逸 timeout——CI 14400s 被杀实测教训）。
6. **PWD 显式设置**：HMDFS getcwd() 随机失败（E011 同源）——`os.environ["PWD"] = work`。

## 四、上游测试（tests/ 套——62 项 .tests）
- **N 口径（rule4）**：上游 tests/ 目录 62 个 `.tests` 文件 = 62 个注册测试 batch（`ls tests/*.tests | wc -l` 实测）。展开为 2150 个原子测试项（每 batch 含多条 test type 数据行）。
- **本地执行方式**：`make check SHELL=/data/service/hnp/bin/bash` 编译 check_PROGRAMS（automake 机制 make all 不编测试程序）+ tests/regression 脚本（从 tests/ 目录运行：`timeout 300 env LD_LIBRARY_PATH=<work>/src/.libs /data/service/hnp/bin/bash ./regression`，GLBL_SYS_ARCH 等 ../tools 相对路径要求 cwd=tests/）。
- **本地实测结果（2026-09-18，aarch64 OHOS）**：62 batch 全跑，**2150 项：2040 SUCCESS / 0 FAILURE / 0 ERROR / 111 SKIPPED**：
  - 75 SKIPPED (architecture difference)——x86 等非本机架构专属 syscall 测试项，上游语义即跳过（非 aarch64 架构项）
  - 25 SKIPPED (valgrind not installed)——bpf-valgrind 类需 valgrind，OHOS 环境未装（环境依赖如实申报）
  - 11 SKIPPED (must specify live tests)——live 类需 `-T live` 显式指定（真实加载 seccomp 过滤器进内核），OHOS 内核形态下不默认跑（见第五节）
- **她bang 修复**：tests/38-basic-pfc_coverage.sh 与 55-basic-pfc_binary_tree.sh 上游 shebang 为 /bin/bash（OHOS 无 /bin/bash，rc=126 bad interpreter）——配方内改 /data/service/hnp/bin/bash 后两项均 SUCCESS（等价 2.5.4 归档 0007/0008 补丁）。

## 五、OHOS 内核形态如实申报（W0 深点）
- **构建可用性**：✅ 已验证（conan create 全绿 + test_package 链接运行）
- **运行时内核依赖**：libseccomp 的纯用户态 API（bpf 过滤器生成/db 操作：seccomp_version/seccomp_api_get/seccomp_rule_add→seccomp_gen_bpf 等 sim 路径）完全不依赖内核；`seccomp_load()`（PR_SET_SECCOMP/seccomp() syscall 真实加载）为内核特性依赖项——OHOS 内核形态（HongMeng）下该 syscall 的可用性不由本包宣称，下游使用方按自身内核环境实测。与 kexec 先例同款口径：构建可用性验证 + 运行时内核依赖如实申报。

## 六、构建命令（复现）
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
