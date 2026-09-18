# glpk 4.65 编译笔记（HarmonyOS PC · Conan autotools）

## 定位
- 产出动态 libglpk.so.40 与命令行求解器 glpsol（CLI，见软件级 commands.json）。
- 上游无独立测试套件（无 TESTS/CTest/GTest），官方 make check 仅 2 个检查项
  （glpsol --version、glpsol --mps murtagh.mps --max），8 个示例程序为样例类非独立用例。
- 双口径：2/2 通过（100%），8 个示例程序全部编译+运行成功。

## 关键适配
1. **umask 077 → 022**：glpk configure/config.status 用 `(umask 077 && mktemp -d ...)` 创建
   0700 临时目录；HarmonyOS hmdfs 上当前用户非该目录属主且 group 无写权限，
   config.status 写 subs1.awk 报 Permission denied。配方 build() 内对 configure 全局替换
   umask 077 → 022 后通过（与 5.0 配方同源修复）。
2. **--build/--host 显式三元组**：`--build=aarch64-unknown-linux-musl --host=...` 让 configure
   走原生路径跳过 config.guess，无需打补丁（沿用 5.0 验证结论）。
3. **gmp 依赖接线**：--with-gmp 时 configure 用 AC_CHECK_HEADER 探 gmp.h，需经 os.environ
   补 CPPFLAGS/LDFLAGS 指到 conan gmp 包（autoconf 烤进 Makefile，比 extra_cflags 可靠）。
4. **临时目录恢复**：/tmp 为只读 erofs，/dev/shm 无写权限，全部构建/测试在 $HOME/tmp 专用
   目录 + TMPDIR/TMP/TEMP 环境变量下进行。

## 验证
- 上游 make check：2/2 通过（--version + murtagh.mps OPTIMAL）。
- 示例程序 8/8：sample/iptsamp/mplsamp1/mplsamp2/netgen/nppsamp/spxsamp1/spxsamp2 编译运行成功。
- HarmonyOS 专项测试 glpk_ohos_test.c 3 场景全绿：
  公开 API 求解 LP（obj=212, x1=12, x2=44 校验）、双线程并发求解（reentrancy/TLS）、
  dlopen 动态加载 + glp_version=4.65。
- test_package：真解官方例题 LP（max 10x1+6x2+4x3），5 条断言（z=733.333333 等）。

## 状态
built（待 CI conan create 复核）
---

**编译结束**: 2026-09-16 13:57
**最终状态**: built
