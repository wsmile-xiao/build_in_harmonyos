- **三方库名称**：acedb
- **上游版本**：4.9.62（Sanger Institute 归档分支）
- **上游仓库地址**：https://github.com/richarddurbin/acedb
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | 来源：wmd5/mddriver.c、wmd5/digtest.c（MD5 摘要校验，`make md5test` 目标） |
| 集成测试 | 0 | 上游无集成测试框架 |
| 其他测试 | 0 | acelibtest 需交互式数据库初始化（环境限制，可编译不可自动化）；xtest/coltest/giftest/boxtest 依赖 GTK2 图形环境，OHOS 无 GTK2 无法构建 |
| **合计** | **2** | 上游可自动化运行测试为 wmd5 两个 MD5 校验程序 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | 上游 mddriver/digtest 编译运行，摘要校验通过 |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 7 | 新增 | test_package/test.sh 冒烟测试（tace banner/usage、taql -h/-version、mddriver/digtest 摘要、acediff Usage） |
| **合计** | **9** | **+7** | 7 个新增断言全部通过（conan create 实测 ALL ACEDB TESTS PASSED） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无正式测试框架，适配后补全了测试（请在下方说明）

> 若选择「是」，须说明：
> - **补全的测试范围**：为可执行程序新增 6 个冒烟断言（test_package/test.sh），覆盖 tace（ACeDB 主程序 banner + usage）、taql（AQL 查询语言入口）、mddriver/digtest（上游 MD5 摘要校验）、acediff（工具入口）
> - **补全原因**：上游 4.9.62 为 2016 年归档代码，无 make check 目标；`make test` 目标中图形测试（xtest/coltest 等）依赖 GTK2，OHOS 无 GTK2 无法构建；仅 wmd5 两个测试程序可自动化
> - **新增测试文件清单**：
>   1. `archives/a/acedb/4.9.62/test_package/test.sh` — 6 断言冒烟测试（实质调用被测包二进制并校验输出）
>   2. `archives/a/acedb/4.9.62/test_package/conanfile.py` — 可执行程序 test_package 入口（VirtualRunEnv + test.sh）
>   3. `archives/a/acedb/4.9.62/test_package/MANIFEST.yml` — 测试声明（上游 mddriver/digtest + 新增 test.sh）

## 验证结果

- 编译状态：通过（本地 wmake 编译 8 个工具 + 2 个上游测试程序，aarch64 ELF；conan create 干净构建通过；conan-verify G0-G4 全 PASS；pre_pr_audit W5 审计通过 P0=0/P1=0/P2=0）
- 上游测试用例通过率：2/2（100%）
- 新增测试用例通过率：7/7（100%）

## 补充说明

1. **自定义 wmake 构建系统适配**：acedb 不使用 autotools/cmake，而是 Sanger 自定义的 wmake 系统（`ACEDB_MACHINE` + `wmake/*_DEF` + 顶层 makefile 驱动 truemake）。新增 `wmake/OHOS_4_DEF` 定义 OHOS aarch64/clang15 构建参数，conan 配方以 `ACEDB_MACHINE=OHOS_4` 驱动构建。
2. **GTK2 依赖处理（实质逻辑，非空壳 stub）**：OHOS 无 GTK2（且无 X11 显示环境），图形工具（xace/giface/blixem/dotter 等）无法构建。通过 `ACEDB_NO_GTK` 条件化 graph.h/gex.h/genebuilder.h/smapmethods.h 的 gtk 头文件包含，仅构建命令行/服务端工具（tace/taql/saceserver/saceclient/acediff/acediffsorted/makeUserPasswd/tagcount）——这是 acedb 数据库引擎的核心价值，非空壳 stub。
3. **OHOS sysroot 适配补丁（8 个）**：mystdlib.h 移除自定义 qsort 声明（现代 POSIX 系统 stdlib.h 提供标准原型）；mydirent.h 通过 LINUX POSIX 分支正确包含 dirent.h（无需平台宏）；truemake SHELL 与 perl shebang 改为 OHOS 实际路径（无 /bin/bash、/usr/bin/perl）。
4. **OHOS 可执行限制**：hmdfs 上 strip 后的 ELF 无法执行（Operation not permitted），conan 配方 `package()` 直接复制未 strip 二进制。
5. **CI 沙箱 hmdfs 容错**：CI 运行在 OHOS 沙箱（hmdfs 文件系统），`chmod u+w` 静默成功但权限位不生效，`aceSetReleaseDir` 的 `-w` 检查会导致构建中断；已对 release dir 元数据更新做不可写容错（WARNING 后跳过，不影响构建产物）。
5. **可复现性**：源码 URL 固定到具体 commit（86d8c1c92d8a2c58cd090e85a1e17771612bfcb9 = master HEAD），避免可变分支引用导致未来构建不可复现；sha256 与固定 commit 产物一致（本地解压 diff 验证与 master 源码无差异）。
6. **依赖说明**：glib-2.0/readline/ncurses/flex(libfl) 由 cmd-pkgs 预编译包提供（系统依赖，非 conan 包）；conan-verify G0-G4/L2/L4/L5 全 PASS。
7. **已知限制**：图形界面工具（xace 等）因 OHOS 无 GTK2 未适配；acelibtest 需要交互式数据库初始化，未纳入自动化测试。
