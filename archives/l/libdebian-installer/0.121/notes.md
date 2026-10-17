# libdebian-installer 0.121 适配笔记

## 编译环境
- **构建系统**: autotools（无现成 configure——autoreconf 生成）
- **编译日期**: 2026-08-27
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（配方内联处理——无独立补丁文件）

## 编译步骤（conan create 全流程）

```bash
conan create archives/l/libdebian-installer/0.121 --build=missing
```

### 1. 源码获取（source()）
沙箱下 `get()` 抛 PermissionError——改用 `download()` + 手动解压：
```bash
tar -xJf libdebian-installer_0.121.tar.xz --no-same-owner || true
cp -a libdebian-installer/. . && rm -rf libdebian-installer
```

### 2. autoreconf 生成 configure
- **automake 版本**：环境 automake-1.17 缺 Automake/Config.pm——`PERL5LIB`
  指向 automake-1.16
- **autoconf 路径**：`/usr/local/bin/autoconf` 是坏的（exit 127）——
  `AUTOCONF` 环境变量指向 `/data/service/hnp/autoconf.org/autoconf_2.72/bin/autoconf`
- **configure.ac 修改**：
  - `AC_INIT` 的 `m4_esyscmd(dpkg-parsechangelog)` 取版本（环境无 dpkg）→
    硬编码 `0.121`
  - `PKG_CHECK_MODULES([CHECK], ...)`（系统无 pkg.m4 宏）→ 注释（测试框架非必需）

### 3. configure + config.status mktemp（关键攻坚，同 dpkg）
`/tmp` 只读 + `$HOME/.ci_logs` 不可写 + autoconf 相对路径 mktemp →
`./confXXXXXX/subs1.awk: Permission denied`。解法（SKILL 步骤 2——configure
尾部自动执行 config.status，事后改 ac_tmp 已来不及）：
- configure 执行前替换其 mktemp 模板：`mktemp -d "./confXXXXXX"` →
  `mktemp -d "${TMPDIR}/confXXXXXX"`
- configure 命令带 `TMPDIR=/data/storage/el2/base/cache`
- 详见 SKILL: `docs/skills/autotools-config-status-mktemp-sandbox.md`

### 4. 上游测试（build() 集成——rule 4 实测回填）
上游 check 测试套件（test/ 目录——main.c + test_hash.c + test_system_packages.c
+ test_exec.c——8 用例）：build() 内编译并运行，实测 **8/8 = 100% 通过**
（`Checks: 8, Failures: 0, Errors: 0`）：
```bash
clang -I<src>/include -I<check>/include -DDATADIR="<src>/test" \
  <src>/test/main.c <src>/test/test_hash.c <src>/test/test_system_packages.c \
  <src>/test/test_exec.c <src>/src/.libs/libdebian-installer.a \
  <src>/src/system/.libs/libsystem.a <check>/lib/libcheck.a -o test_ldi
TMPDIR=/data/storage/el2/base/cache ./test_ldi   # check mkstemp 需可写临时目录
```
> 注意：DATADIR 必须用绝对路径（相对路径时 test_system_packages 读 Packages
> 文件失败段错误——非代码缺陷，是测试脚手架路径问题）。

### 5. 打包（package()）
上游 Makefile 无 install 目标（`make install` 报 'No rule to make target
install'）——手动拷贝静态库（src/.libs 与 src/system/.libs 下的 .a）+ 头文件
（include/ 目录）到包内 lib/ 与 include/。

## 验证结果
- **构建**: `libdebian-installer/0.121: Package created`
- **上游测试**: 实测 **8/8 = 100% 通过**（check 框架——Checks: 8, Failures: 0, Errors: 0——build() 集成回填，rule 4）
- **R34 消费者验证**: test_package — 静态库存在 OK

## 已知限制
- 上游测试需 check 库（ohpcd 已发布 check/0.15.2）——仅本机构建时链接（can_run 守卫）
- 测试框架（check）依赖已移除（构建不需要）
