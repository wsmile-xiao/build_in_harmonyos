# libsmartcols 2.42.3 适配笔记

> 取源法：util-linux 2.42.3 源码树的 libsmartcols 子目录（同 util-linux 系其他 lib 件——util-linux/2.42 编 libblkid/libuuid/libmount 三件、util-linux-login/2.42.2 编 login）。

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libsmartcols（util-linux 的表格输出库） |
| 版本 | 2.42.3 |
| 上游 | https://git.kernel.org/pub/scm/utils/util-linux/util-linux.git（tag v2.42.3） |
| 构建系统 | autotools（util-linux 树 configure） |
| 语言 | 纯 C |
| 许可证 | LGPL-2.1-or-later |
| 前置依赖 | libuuid/2.40.4（制品仓已发布 ✅） |

## 二、上游验证（W0）
- tag v2.42.3 实存：kernel.org util-linux-2.42.3.tar.xz ✅
- sha256：`66ac7c0e725278eb2b039e3104f2c91119341d941b41bac7a285c695f940bd57`（官方 sha256sums.asc 核对一致+本地下载实测一致）
- 前置 libuuid/2.40.4：`conan download libuuid/2.40.4 -r=ohpcd --only-recipe` ✅ 已发布

## 三、OHOS 适配要点（util-linux/2.42 已合入配方同款，实测过的结论）
1. **E011（umask 077）**：configure 头部注入 `umask 000` + `(umask 077 && mktemp -d "./confXXXXXX")` → `(umask 000 && ...)`。
2. **config.guess/config.sub OHOS 识别**：config/ 子目录 2026 新版格式 patch（ohos* OS 行 + linux-ohos*- kernel-os 行 + aarch64:Linux OHOS case）。
3. **TMPDIR**：autoconf $ac_tmp 落 /tmp（OHOS 只读）→ build_folder。
4. **--build/--host**：显式 aarch64-unknown-linux-ohos（与 util-linux/2.42 同款）。
5. **只编库**：`--disable-all-programs --enable-libsmartcols --enable-libuuid`（configure 依赖解析需要 libuuid 同树构建；产物打包时剔除 uuid——归 libuuid/2.40.4 包管）。
6. **内部依赖 libcommon.la**：util-linux 内部库，同树构建自动解决（libsmartcols_la_LIBADD = libcommon.la）。

## 四、上游测试
- **N 口径（rule4）**：上游 tests/ts/libsmartcols/ 全部 5 个 ts 脚本（title/fromfile/termreduce-loop/continuous-json/filter）——展开 90 个原子断言（fromfile 22 sub-tests + filter 65 sub-tests + 3 个单项）。另 samples/ 10 个 check_PROGRAMS 作为 ts 的 helper 程序（sample-scols-* 系列被 ts 直接调用，非独立注册测试）。
- **本地执行方式**：构建树 `make sample-scols-* test_scols_termreduce`（--disable-all-programs 不编 check_PROGRAMS，需显式 make）→ ts 脚本从源码树 tests/ts/libsmartcols/ 运行：`bash ./<ts> --srcdir=<S> --builddir=<B>`（⚠ --builddir 不能是第一个参数——functions.sh 的 ts_option_argument 用 sed 正则 `.*[ \t\n]--builddir=...` 要求前面有空白字符，放首位会解析失败回落源码树）。
- **本地实测结果（2026-09-18，aarch64 OHOS）**：**5/5 脚本全过，90/90 断言全过（100%，0 FAILED）**：
  - title: OK
  - fromfile: OK（all 22 sub-tests PASSED）
  - termreduce-loop: OK
  - continuous-json: OK
  - filter: OK（all 65 sub-tests PASSED）
  - （toybox sed "Unknown option in-place" 为 diff 环节噪音，不影响判定——输出与 expected 全部一致）
- **关键 OHOS 发现（scols_print_table_to_string）**：OHOS musl 的 open_memstream 在 do_print_table 写入后无显式 fflush 时，fclose 后 *data 为空串且部分路径进程退出时 Illegal instruction（最小复现：直接调用→rc=0 data=[]+退出崩；手动 open_memstream+显式 fflush→data 完整+干净退出；scols_print_table 直写 stdout 完全正常）。修法：配方内 patch print-api.c 在 fclose 前加 fflush(stream)（glibc/musl 双兼容）。
- **consumer 验证**：test_package/test_smartcols.c 真实调用 table API（scols_new_table/new_column/new_line/sprintf/print_table_to_string）并断言渲染输出含预期单元格内容——实测渲染 `NAME/STATE` 两列两行完整表格。

## 五、构建命令（复现）
```bash
conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```
