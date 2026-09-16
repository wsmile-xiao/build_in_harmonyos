# dh-vim-addon 0.6 适配笔记

## 适配环境
- **构建系统**: none（纯 Perl 脚本打包，零编译）
- **适配日期**: 2026-09-13
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）
- **运行时依赖**: debhelper/13.3.4（`Debian::Debhelper::Dh_Lib`）、
  dpkg/1.23.7（`Dpkg::Control::Info` / `Dpkg::Version`）

## 语言预检（R47 / 协议 v0.8 附录 D）
本软件是 **纯 Perl**（debhelper 的 dh_* 插件 + dh sequence 模块），不是 C/C++。
R47 要求 checkout 后、进主流程前跑 `lang-preflight`，**必须显式声明任务语言为 perl**
（默认 `cpp` 会把本任务误判为 `env_unsupported` 而错误终止）。

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight dh-vim-addon 0.6 \
    --src $BUILD_SRC_DIR --lang perl
# ✅ 语言匹配: task=perl, detected=perl — 继续适配主流程（exit 0）
# evidence: build_system=none / manifest=未发现语言 manifest 文件 /
#           source_stats=源文件 1 个（perl:1），主体占比 100%
```

## W0 依赖预检（R35/R36/PF4）
方法：`conan download <ref> -r=ohpcd --only-recipe`（R35：禁止用 `conan list`
判断 binary 是否存在）。

| 依赖 | 上游声明 | 制品仓 | 处置 |
|------|---------|--------|------|
| debhelper/13.3.4 | `debhelper (>= 10.2.5)` | ✅ 已发布（rev ca526456…） | 声明 `requires` |
| dpkg/1.23.7 | `libdpkg-perl` | ✅ 已发布（rev 2be049ff…） | 声明 `requires` |
| vim-common | `vim-common` | ❌ 未收录 | **不声明**（禁止捎带适配依赖） |

`vim-common` 提供 `helpztags`（为含 `doc/` 目录的插件生成帮助标签）与 vim
运行时目录；缺失仅影响该可选步骤，核心的“插件目录 → Vim/Neovim packpath
符号链接”能力不受影响。

## 适配步骤（conan create 全流程）

```bash
conan create archives/d/dh-vim-addon/0.6 \
    -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 \
    --build=missing
```

### 1. 源码获取（source()）
沙箱 `get()` 有 PermissionError 风险——`download()` + 手动解压：
```bash
tar -xzf dh-vim-addon_0.6.tar.gz --no-same-owner || true
cp -a dh-vim-addon-debian-0.6/. . && rm -rf dh-vim-addon-debian-0.6
```
tarball（17231 字节，sha256=b5fa98d7…c856606，与官方 git-archive 一致）内容：
- `dh_vim-addon`（Perl CLI，debhelper 的 dh_* 插件）
- `vim_addon.pm`（dh sequence 插件）
- `COPYING`（GPL-3.0）
- `debian/`（changelog / clean / control / copyright / gbp.conf / install /
  manpages / rules / salsa-ci.yml / source/format）

### 2. 构建（build()）
纯 Perl 无编译步骤——`build()` 直接 `pass`。

### 3. 打包（package()）
挑文件安装（禁止整目录拷贝）：
- `dh_vim-addon` → `<pkg>/bin/dh_vim-addon`（chmod 0o755）
- `vim_addon.pm` → `<pkg>/lib/perl5/Debian/Debhelper/Sequence/vim_addon.pm`
- `dh-vim-addon.1` → `<pkg>/share/man/man1/dh-vim-addon.1`（pod2man 生成，
  见下）
- `COPYING` → `<pkg>/licenses/COPYING`
- `package_info()`：`cpp_info.libs=[]`、`bindirs=["bin"]`

**man 页生成**：上游 `debian/rules` 用
`pod2man --utf8 dh_vim-addon > dh-vim-addon.1` 生成，tarball 内**不含** `.1`。
配方内尽力生成：优先 `pod2man`，回退 `perl -MPod::Man`；两者皆不可用则跳过
（man 页非运行必需，不阻塞打包，也不伪造内容）。

### 4. 消费者验证（test_package，test_type="explicit"）
- **R1 文件存在断言**：`bin/dh_vim-addon` + `Sequence/vim_addon.pm`（2 断言）
- **R2 `perl -c` 语法检查**：两文件均退出码 0（2 断言）。PERL5LIB 加入本包与
  依赖包（debhelper/dpkg）的 perl 库根；**不** walk 全树——dpkg 包的
  `Dselect/Method/Config.pm` 会遮蔽 perl 核心 `Config` 模块。
- **R3 功能冒烟（真实运行）**：构造最小 debian 骨架（`debian/control` 用
  `Build-Depends: debhelper-compat (= 13)`，**不得**再有 `debian/compat`——
  否则报 compat 重复），addon 目录置于 `debian/smoke/`（tmpdir；放
  `debian/tmp` 会报 `No directories found matching`），真实运行
  `dh_vim-addon -psmoke`（3 断言）：
  - 退出码 0
  - `usr/share/vim/vimfiles/pack/dist-bundle/start/smoke` 符号链接创建
  - `usr/share/vim/vimfiles/pack/dist-bundle/opt/optsmoke` 符号链接创建
- **R4 鸿蒙特有测试（OpenHarmony 平台特性，7 断言）**：上游是 Debian 侧工具，
  其前提（系统 `/usr/bin/perl`、0755 安装权限、短路径制品树）在 OHOS 上都不成立，
  故针对平台差异单独成组：
  - **H1** 目标机为 OpenHarmony aarch64（`os.uname()` → `sysname=HarmonyOS`,
    `machine=aarch64`）——确保消费链跑在 OHOS 目标而不是交叉构建主机
    （用 `os.uname()` 而非 `uname` 子进程：CI worker 的 `PATH` 不含 `uname`，
    实测 `subprocess.run(["uname","-m"])` 会 `FileNotFoundError`）
  - **H2** 平台 perl 来自 OHOS 自带 hnp 运行时（`/data/service/hnp/bin/perl`
    → `/data/service/hnp/perl.org/perl_5.42.0/bin/perl`）；OHOS 无系统 perl
    发行包，模块必须由 Conan 依赖提供
  - **H3** 解释器按目标架构构建（`perl -V:archname` = `aarch64-linux`）
  - **H4** OHOS 权限语义下安装产物保留属主可执行位（实测 `mode=0o770`，
    非 Debian 常见 0755；CLI 调用与 CI L2 门禁都依赖此位）
  - **H5** packpath 符号链接为**相对**目标（`../../../../../smoke`）——OHOS 上
    Conan 包位于 `/storage/Users/<user>/.conan2/...` 长绝对路径，绝对链接在
    制品迁移/重定位后失效（2 断言）
  - **H6** 上游固定 shebang `#!/usr/bin/perl` 未经改写（0 补丁）；OHOS 上
    `/usr/bin/perl` 不存在，故调用方必须经平台解释器执行（本测试即该路径）

## 验证结果
- **构建**: `dh-vim-addon/0.6: Package created`
- **R34 消费者验证**: `test_package/test_dh_vim_addon.py` — **14 断言全过**
  （R1/R2/R3 共 7 + R4 鸿蒙特有测试 7）
- **R34 破坏性反向验证**: 移除被测包后重跑 → 6 断言失败、退出码 1（测试真实
  依赖被测包，非空跑）
- **上游测试**: **无**（R51 清点证据见下）

## R51 上游测试清点（三步法）
1. **清点**：`tar tzf dh-vim-addon-debian-0.6.tar.gz` 列出全部 14 个条目
   （源码 2 + COPYING + .gitignore + debian/ 10）；`grep -iE '(^|/)(t|test|
   tests|check)/'` **无命中**。
2. **不能运行的原因**：上游确无测试套件——`debian/rules` 仅 `dh $@` +
   `pod2man`，无 `make check` / `prove`；`debian/control` 无 `Testsuite` /
   autopkgtest。故无“可运行环境”可跑。
3. **如实回填**：`test_package/MANIFEST.yml` 记 `upstream_tests.count=0`，
   描述附清点证据。

## 已知限制
- `dh_vim-addon` 完整运行（生成 `${vim-addon:Depends}` 替换变量）需 Debian
  dpkg 数据库；OHOS 沙箱无此环境。
- addon 含 `doc/` 目录时会调用 `helpztags`（`vim-common` 提供，制品仓未发布），
  沙箱内该命令不存在；故功能冒烟使用不含 `doc/` 的 addon。

## 编译结束
- 最终状态: built（Conan 配方验证通过，W3 本地 CI 模拟通过，未 upload）
- conan_ref: `dh-vim-addon/0.6`（ohpcd/stable）
- 补丁: 0；依赖: debhelper/13.3.4 + dpkg/1.23.7
---

**编译结束**: 2026-09-13 16:18
**最终状态**: built
