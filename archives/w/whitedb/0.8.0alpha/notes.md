# whitedb 0.8.0alpha 适配笔记

## 版本说明（任务总纲版本替换规则）

任务指定版本 `whitedb-0.7.3-git211004` 在上游**不存在**：
- savannah.nongnu.org/projects/whitedb/ → 404（无此项目组）
- download.savannah.nongnu.org/releases/whitedb/ → 404，具体文件 302 后镜像 404
- GitHub priitj/whitedb 无 `0.7.3-git211004` tag

按任务总纲「若上游找不到任务指定版本，则直接使用上游最新版本继续执行」，采用上游最新发布版本 **v0.8.0alpha**（2022-12-01，GitHub `priitj/whitedb`，源码包实测可下载）。v0.8.0alpha 此前未适配过（制品仓无配方、archives/knowledge 无记录）。

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，tarball 无预生成 configure）
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
# 1. 自举生成 configure（tarball 无预生成 configure）
autoreconf -fi   # 本地验证；配方内用 aclocal→autoconf→autoheader→libtoolize→automake 直跑链

# 2. E114 修复（OHOS HMDFS）：config.status 临时目录写权限
#    config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建 2700 目录，
#    本机 HMDFS 下进程 uid(20020179) 与文件属主(20001006) 不一致导致无法写入
#    subs1.awk。修复：预建可写目录 + 改 configure 内嵌 ac_tmp 指向该目录 + trap 只透传退出码。
#    探索阶段本地实测：sed 's/umask 077/umask 002/' config.status 亦可解（组可写 2775）。

# 3. configure / make / install
./configure --prefix=$HOME/usr/local --disable-shared --enable-static
make -j2
make install DESTDIR=$TEST_PREFIX

# 4. 上游测试
make check   # TOTAL=2 PASS=1 SKIP=1 FAIL=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压后 work/orig 只剩扁平文件，Db/Main/Parser 等目录全部丢失 | F068 `_promote_nested_source` 误判：tarball 根目录只有 configure.ac/Makefile.am，不含 `_BUILD_MARKERS`（configure/CMakeLists.txt/Makefile/meson.build）；`_find_source_subdir` 递归到含手写 Makefile 的 `Server/` 子目录并误提升，`_promote_nested_source` 删除了其余全部源码 | 手动重建 .orig/.work：解压 tarball + 单层提升 `whitedb-0.8.0alpha/` → 根目录；重写 .tarball-sha256；重建 edit-tracker 基线（243 文件）；清理损坏备份 |
| 2 | `config.status: can't create ./confWh1axE/subs1.awk: Permission denied` | E114：HMDFS 上 config.status 的 `(umask 077 && mktemp -d)` 建 2700 目录（drwx--S---），本机进程 uid 与文件属主映射不一致，组位无写权限 | 探索阶段 sed 's/umask 077/umask 002/' config.status 通过；配方内固化 E114 官方修法（预建可写目录+改 ac_tmp+TMPDIR，同 libgsf/abiword 先例） |
| 3 | 上游 tarball 无预生成 configure | GitHub 源码包仅含 configure.ac/Makefile.am | 配方 build() 先自举；tool_requires automake/1.18 + libtool/2.5.4（制品仓已发布，参照 abiword-plugin-* 先例） |
| 4 | whitedb 库名是 libwgdb 而非 libwhitedb | 上游 Main/Makefile.am: `lib_LTLIBRARIES = libwgdb.la`；whitedb.pc `Libs: -lwgdb` | conanfile package_info 声明 `cpp_info.libs = ["wgdb"]`；commands.json 声明 wgdb CLI 工具（R38） |

## 依赖版本

无 conan 运行时依赖（纯 C 库，仅需系统 libc/libm）。构建工具：
- automake/1.18（tool_requires，制品仓）
- libtool/2.5.4（tool_requires，制品仓）

## 验证结果

```bash
# 上游测试（make check，Makefile.am TESTS 注册 2 项）
TOTAL: 2  PASS: 1  SKIP: 1  FAIL: 0
# PASS: Test/common.test —— Main/selftest common 全量公共功能测试
# SKIP: Test/log.test（exit 77）—— configure 默认 --disable-logging，selftest 检测日志功能禁用后主动跳过

# 消费者验证（test_package）
test_whitedb: 调用 wg_attach_local_database/wg_create_record/wg_encode_int/wg_encode_str/
wg_set_field/wg_get_field/wg_decode_int/wg_decode_str/wg_delete_local_database 做 int/str 字段 roundtrip
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方：autogen 自举 + E114 修复 + make check 集成 |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | CMake 消费者测试（真实调用 whitedb API） |
| commands.json | 软件级 CLI 工具声明（wgdb） |

## 注意事项

- E114 修复在 conanfile.py 内联（非 patches/ 文件），仅 OHOS 平台生效
- 版本替换为 v0.8.0alpha，最终提审时分支信息 `feat/whitedb-0.7.3-git211004` 由用户在任务平台修改
---

**编译结束**: 2026-09-15 04:33
**最终状态**: built
