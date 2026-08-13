# roswell 24.10.115 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-12
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 源码下载：官方 GitHub tag v24.10.115（codeload 镜像，避免 github.com 直连超时）
2. `sh bootstrap` 生成 configure/Makefile.in（需 `AUTOM4TE=/data/service/hnp/bin/autom4te` 环境变量，
   否则 aclocal 报 `@am_AUTOM4TE@` 未替换错误）
3. configure（E011 修复后成功）：
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX \
     CPPFLAGS="-I$CURL_ROOT/include" \
     LDFLAGS="-L$CURL_ROOT/lib -Wl,-rpath,$CURL_ROOT/lib"
   ```
   - `$CURL_ROOT` = conan 缓存的 curl/8.15.0 包路径
   - 依赖：libcurl（configure.ac 中 AC_CHECK_LIB curl，缺失则 AC_MSG_ERROR 中止）
4. `make -j2` ✅
5. `make install DESTDIR=$TEST_PREFIX` ✅（bin/ros + etc/roswell lisp 脚本 + man pages）
6. `make -j1 check` ✅（tsv_sbcl 测试程序编译链接通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套检测把 `scripts/` 误提升为源码根 | `_BUILD_MARKERS` 不含 autotools 的 configure.ac/Makefile.am；GitHub tag 源码包无生成版 configure | 手动解压 tarball 到 .orig + bootstrap 生成 configure 后重跑 init-build（--no-download --project-dir） |
| 2 | 归档写入 skill 目录而非项目仓库 | 未设置项目目录 | init-build 加 `--project-dir /storage/Users/currentUser/project/新建文件夹3/build_in_harmonyos` |
| 3 | configure 报 `can't create ./confXXX/subs1.awk: Permission denied` | **E011**: HMDFS UID 映射导致 umask 077 的临时目录对当前进程不可写 | `sed -i 's/umask 077/umask 022/g' configure`（知识图谱 E011 推荐方案） |
| 4 | make check 链接失败 `duplicate symbol: argv_orig` | 上游测试代码缺陷：tsv-sbcl-bin.c 与 main.c 均定义 `char** argv_orig`（util.h 已有 extern 声明），OHOS 的 ld.lld 比 GNU ld 严格 | 删除 tsv-sbcl-bin.c 中重复的 `char** argv_orig;` 定义 |
| 5 | `ros --version` 运行时 SIGSEGV (Signal 11) | 鸿蒙 `getpwuid()` 返回 NULL（无 passwd 条目），homedir() 返回 NULL，configdir() 返回 NULL，main.c 中 s_cat(NULL,...) 崩溃 | 平台限制：设置官方支持的环境变量 `ROSWELL_HOME` 后正常运行（`ros --version` 输出 roswell 24.10.115）；test_package 需注入 ROSWELL_HOME |

## 源码修改

- `src/tsv-sbcl-bin.c`：删除 ROSWELL_TSV_TEST 块内重复的 `char** argv_orig;` 定义（main.c 已定义 + util.h extern 声明）
- `configure`（生成文件，E011 修复）：`umask 077` → `umask 022`（2 处）
  - 注：此修改在 finish 的 refresh-patch 阶段由 `--auto` 重新生成补丁

## 依赖版本

- curl/8.15.0（conan 制品仓已发布，本机 conan 缓存路径）→ openssl/3.5.6.1, zlib/1.3.1.1

## 验证结果

```bash
$ ROSWELL_HOME=$HOME/tmp/ros-home ros --version
roswell 24.10.115(NO-GIT-REVISION)
$ make -j1 check   # tsv_sbcl 链接通过
```

## 注意事项

- 运行 ros 必须设置 `ROSWELL_HOME`（绝对路径）——鸿蒙无 passwd 条目导致 homedir() 为 NULL，
  未设置时 main() 中 s_cat(NULL,...) 直接 SIGSEGV；这是官方支持的环境变量，非 hack
- 产物类型：命令行工具（bin/ros），需在软件级目录创建 commands.json（R38）
- libcurl 为运行时依赖：RUNPATH 已写入 conan 缓存路径，conan 打包后由 Conan RPATH 管理

## CI worker 环境问题（已记录，非配方缺陷）

- PR 校验阶段 CI 构建 #22358 首次失败于 `configure: C compiler cannot create executables`
- 根因：CI worker 环境异常——`id` 命令报 `bad uid`（worker passwd 无当前 uid 条目），
  且 checkout-pr 阶段 curl SSL 证书验证失败（worker 缺 CA 证书，CI hint 明确标注"不是 PR 代码问题"）
- 佐证：同一时段其他 PR（tty-clock #5166、alloy #5165）同样 FAILED；本地
  `conan create`（G2 PASS）与 W3 完整 CI 模拟（setup.sh + build_and_test.sh, exit_code=0）均通过
- 处理：等 CI worker 环境恢复后重新触发构建（bluez #5162 于 01:35 PASSED 证明环境已恢复）
---

**编译结束**: 2026-08-12 23:15
**最终状态**: published
