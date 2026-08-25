# DRAFT-hmdfs-autotools-nested-configure：HMDFS 上 autotools 项目（含嵌套子项目 configure）的构建适配方法

> Contributor: makeblacksheepgreat | Status: Draft | Updated: 2026-08-21
> Source: asterisk-srtp 22.10.1 HarmonyOS PC adaptation, PR #6055（18 次 conan-verify 迭代）

## 现象

在 HarmonyOS PC（HMDFS，hmmac=use_task）上用 conan/CI 进程树构建 autoconf 项目时，
`config.status` 报：

```text
./config.status: line 597: ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

随后连锁失败：Makefile 机制不完整 → `make` 报 `No rule to make target ...`；
或触发嵌套子项目重建时报 `C compiler cannot create executables`（缺省 `cc` 不存在）、
`Could not find required 'Libxml2' development package`。

## 与现有知识的关系

- `E011/E052/E060` 已记录单层 configure 的 umask/mktemp 现象与 mktemp wrapper 方案。
- 本草稿补充三个新要点：
  1. **嵌套子项目的 configure 必须同步补丁**——Asterisk 的 `menuselect/configure`
     是独立 autoconf 脚本，只补顶层时主构建成功而子项目确定性失败
     （asterisk-srtp 案例：主 configure 补丁后成功，menuselect 连续 6 次失败）。
  2. **$TMPDIR 工作目录构建**——把源码复制到 `$TMPDIR/builds/<pkg>` 构建、产物拷回，
     规避 `.conan2` 缓存目录的额外限制。
  3. **间歇性失败重跑即成功**——config.status 失败后直接重跑 `./config.status`
     （实验验证 exit=0），无需重新 configure。

## 方案（可机械执行的完整修复链）

1. **递归补丁所有 configure**：
   ```bash
   find . -name configure -exec sed -i 's/umask 077/umask 022/g' {} +
   ```
   决定性对照证据：主 configure 补丁后（077×0 / 022×4）config.status 成功；
   menuselect/configure 未补丁（077×2 / 022×0）连续 6 次失败；同步补丁后 G2 通过。

2. **$TMPDIR 工作目录构建**：
   ```python
   work = "/storage/Users/currentUser/tmp/builds/conan-<name>-<ver>"
   shutil.copytree(self.source_folder, work)
   with chdir(self, work):  # Asterisk 必须 in-source 构建
       self.run("./configure ...")
   ```

3. **config.status 失败重试**：configure 后检查 `makeopts` 是否生成（>1000 字节），
   缺失则重跑 `./config.status`（最多 3 次，间隔 5 秒）。

4. **make 变量注入**：
   - `BUILD_CC=<clang>` —— MAKE_MENUSELECT 等规则硬编码 `CC="$(BUILD_CC)"=cc`，鸿蒙无 cc
   - `PKG_CONFIG_PATH=<sys_prefix>/lib/pkgconfig` —— 嵌套子项目探测 libxml2 等依赖

5. **menuselect 类工具的绕过**（如适用）：
   - 预配置子项目：`cd menuselect && CC=clang PKG_CONFIG_PATH=... ./configure`
   - 注入预生成的 `menuselect.makeopts` / `menuselect.makedeps`（排除列表语义）
   - **时序关键**：注入必须在预配置之后（否则 make 用预配置产出的 menuselect 二进制
     重新生成默认 makeopts 全模块启用，覆盖注入文件；默认配置下 res_adsi 等
     GCC 嵌套函数扩展在 clang 下编译失败）
   - 未来时间戳 `os.utime(dst, future)` 让 make 认为已是最新

6. **只构建目标子目录**：`make -C res SUBDIR=res ASTTOPDIR=$work SOLINK='...'`
   （模块 .so 不链接核心，无需构建 main/utils；子 make 必须显式传 ASTTOPDIR，
   否则报 `No rule to make target '/Makefile.moddir_rules'`；SOLINK 不随环境传递需显式传）

## 验证

```bash
grep -c "umask 077" configure menuselect/configure   # 应全为 0
ls -la makeopts include/asterisk/autoconfig.h        # config.status 完整产物
conan create ... && conan-verify G0-G4 全 PASS       # asterisk-srtp 实测通过
```

## 适用边界

- 适用于 HMDFS 上任何含 autoconf configure 的三方库（单层或嵌套）。
- umask 补丁只影响构建期临时文件权限，不改变产物内容，属可移植性修复而非平台 hack。
- 若递归补丁后仍失败，按 E052 使用 mktemp wrapper 包装。
