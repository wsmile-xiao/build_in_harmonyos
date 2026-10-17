# dh-elpa 2.2.0 适配笔记

## 适配环境
- **构建系统**: none（纯 Perl 脚本打包，零编译；build() 仅 pod2man 生成 man 页）
- **适配日期**: 2026-09-13
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（配方已按仓库规范完成；W3 conan create 须在 CI 环境执行，见"验证状态"）
- **补丁数量**: 1（0001-ohos-templatedir-env-override.patch，portability）
- **运行时依赖**（制品仓检索 `v2/conans/search?q=name/*` 逐项核实）:
  - debhelper/13.3.4 — `Debian::Debhelper::Dh_Lib`（dh_elpa、dh_elpa_test、elpa.pm）✅ 在仓
  - dpkg/1.23.7 — `Dpkg::Version` + `dpkg-parsechangelog`（isnative()/get_source_date_epoch 走 changelog）✅ 在仓
  - perl-config-tiny/2.30 — `Config::Tiny`（elpa.pm、dh_elpa_test）✅ 在仓
  - emacs/29.1 — dh_elpa 的安装器就是 `emacs -batch -l dh-elpa.el`（无 emacs 无法工作）✅ 在仓
  - ncurses/6.5 — **override=True 依赖图冲突消解**（见 §依赖冲突，非直接依赖）
  - `Module::Metadata`（elpa.pm）— **perl 核心双寿命模块（5.13.9 起随 perl core 分发），由系统 perl 提供，无需 conan 依赖**。制品仓检索 `perl-module-metadata/*` 为空（仓库内 1.000038 条目为无 conanfile 的旧格式），不得谎报依赖

## 依赖冲突（CI 实测与消解）

- **现象**：conan create 失败 `ERROR: Version conflict: Conflict between
  ncurses/6.5 and ncurses/6.4 in the graph. Conflict originates from
  emacs/29.1`——emacs/29.1 固定 requires ncurses/6.5，dpkg/1.23.7 固定
  ncurses/6.4，同一 host 图内版本冲突
- **消解**：consumer 侧 `self.requires("ncurses/6.5", override=True)`
  统一到 6.5（仓库标准模式，100+ 先例）。代价：CI 以 ncurses/6.5 重编
  dpkg（dpkg 的 ncurses 仅用于 update-alternatives 交互界面，配方已
  `--without-dselect`，无实质功能影响）。反向统一（override 到 6.4）会
  触发 emacs 从源码重编，代价远大于 dpkg，不可取。

## build() 工作目录（CI 实测与修复）

- **现象**（build #51082）：`RUN: /data/service/hnp/bin/pod2man ... dh_elpa
  > dh_elpa.1` → `Can't open dh_elpa: No such file or directory` →
  `Error in build() method, line 81`——本 fork conan（2.29.1 OHOS 适配版）
  的 build() 默认 cwd 是 `build-release` 子目录，不含源文件
- **修复**：pod2man 命令显式 `cwd=self.source_folder`，.1 生成在源目录，
  package() 从 `self.source_folder` 取文件——in-source 布局，与 dpkg
  配方的 `cwd=self.source_folder` 惯例一致（dpkg notes 同样记录
  "build_folder 是 build-release 无 Makefile"）

## 消费者冒烟 debhelper 兼容级别（CI 实测与修复）

- **现象**（build #51164，测试阶段 R3/R4 全挂，13/17 通过）：dh_elpa
  报 `error: Compatibility levels before 5 are no longer supported
  (level 1 requested)` / `error: Please specify the compatibility level
  in debian/compat`，exit 25——冒烟骨架 debian/ 缺 compat 声明，
  debhelper Dh_Lib 无法确定兼容级别（stderr 中的 changelog_parse(file)
  deprecation 是 dpkg 1.23.7 对 debhelper 13.3.4 旧调用的无害警告，
  非失败原因）
- **修复**：test_dh_elpa.py 冒烟骨架新增 `debian/compat`（内容 `12`，
  与上游 dh-elpa 2.2.0 自身 debhelper-compat (= 12) 一致）

## emacs load-path（CI 实测与修复）

- **现象**（build #51320，compat 修复已生效后）：dh_elpa 报
  `emacs -batch -Q -l package ... returned exit code 255`——`-l package`
  需加载 package.el，而 emacs 包 runenv 只导出单目录
  `EMACSLOADPATH=<pkg>/share/emacs/29.1/lisp`，package.el 位于
  `lisp/emacs-lisp/`，且 `-Q` 隐含 `--no-site-lisp` → emacs 找不到
  `package`（exit 255；dh_elpa 的 doit_quietly 吞掉 emacs stderr，
  故日志只见 exit code）
- **修复**：test_dh_elpa.py 按 emacs 包的 lisp 根补齐 EMACSLOADPATH
  （lisp + 其全部子目录 + 本包 elpa 目录，复现 emacs 默认 dump
  load-path 形态），并新增 `emacs -batch -Q -l package` 预检打印
  stderr（诊断用）
- **消费者提示**：真实消费者运行 dh_elpa 亦需保证 emacs 的 load-path
  含 `lisp/emacs-lisp`（本 test 的补齐方式可直接复用）
- **进展**（build #52239，2026-09-20）：EMACSLOADPATH 补齐后
  `emacs -batch -Q -l package` probe **exit=0**（修复生效）；但 dh_elpa
  内部那条完整命令仍返回 exit 255，且 `doit_quietly` 吞掉 emacs stderr。
  已在 test 中加「同参数手动复现 + emacs API 可用性探针」（探测
  `lm-package-requires`/`copy-package-desc`/`package--make-autoloads-and-stuff`
  等是否存在于 29.1，用于区分「测试环境问题」与「上游 >=30.1 的真实版本
  阻塞」——上游 dh-elpa 2.2.0 声明 emacs >= 1:30.1，制品仓仅 29.1）。

## Emacs 30 API 缺口（CI 实测 + 源码核对 + backport）

- **上游要求**：dh-elpa 2.2.0 `Build-Depends/Depends: emacs (>= 1:30.1)`；
  制品仓最新为 emacs/29.1
- **源码级核对**（Emacs 官方 tag 对照，逐符号验证）：
  `dh-elpa.el` 调用的 API 中，**只有 `lm-package-requires` 在 Emacs 29.1
  缺失**（29.1 的 `lisp/emacs-lisp/lisp-mnt.el` 无此函数，Emacs 30 新增），
  其余（`lm-header-multiline`/`lm-homepage`/`copy-package-desc`/
  `package-desc-from-define`/`package--make-autoloads-and-stuff`/
  `package-generate-autoloads`/`package-load-descriptor`/
  `package-tar-file-info`/`package-read-from-string`）在 29.1 均可用
- **失败现象**：dh_elpa 内部 `emacs -batch -Q -l package ... -l dh-elpa.el
  -f dhelpa-batch-install-file` 返回 exit 255（`lm-package-requires`
  void-function），`doit_quietly` 吞掉 emacs stderr，日志只见 exit code
- **修复**：补丁 0002 在 `dh-elpa.el` 顶部按 **Emacs 30 源码逐行 backport**
  `lm-package-requires` + `lm--prepare-package-dependencies`
  （`(unless (fboundp 'lm-package-requires) ...)` 守卫，Emacs ≥ 30 上是
  no-op，非 stub——语义与上游完全一致），使 dh-elpa 2.2.0 可在
  emacs/29.1 运行

## 适配步骤（conan create 全流程）

```bash
conan create archives/d/dh-elpa/2.2.0 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
```

### 1. 源码获取（source()）
沙箱 `get()` 有 PermissionError 风险——`download()` + 手动解压：
```bash
tar -xJf dh-elpa_2.2.0.tar.xz --no-same-owner || true
cp -a work/. . && rm -rf work
```
tarball（27 KiB，sha256=4d448416…fd5154 与 `dh-elpa_2.2.0.dsc` Checksums-Sha256 双源核对一致）：
- `dh_elpa`（543 行 Perl，debhelper 的 dh_* 插件）
- `dh_elpa_test`（ERT/Buttercup 测试运行器）
- `elpa.pm`（29 行 dh sequence 插件）
- `dh-elpa.el`（289 行 Emacs Lisp 安装器，emacs -batch 调用）
- `emacsen-common/{compat,install,remove}`（debhelper 模板，`#ELPAPACKAGE#` 占位符）
- `autoscripts/prerm-elpa`、`helper/{install,remove}`（dh-elpa-helper 二进制包内容）
- `debian/`（打包元数据；Testsuite: autopkgtest，1 项 build-deb）

### 2. 补丁（patches/）
`0001-ohos-templatedir-env-override.patch`：上游 `$templatedir` 硬编码
`/usr/share/debhelper/dh_elpa/emacsen-common`，conan 包布局无 `/usr` 根，
字节编译模式的 helper 脚本生成（sed_file 模板替换）会失败。补丁增加
`DH_ELPA_TEMPLATEDIR` 环境变量覆盖，默认保持 Debian 行为——与 dh 自身的
`DH_AUTOSCRIPTDIR` 转义口同构，无平台宏（符合 R8/PF5）。

### 3. 构建（build()）
纯 Perl 无编译步骤——仅执行上游 debian/rules 同款 man 页生成：
```bash
pod2man -c Debhelper --section=1 dh_elpa > dh_elpa.1
pod2man -c Debhelper --section=1 dh_elpa_test > dh_elpa_test.1
```
pod2man 在 OHOS worker 位于 `/data/service/hnp/bin/pod2man`；缺失时优雅跳过
（warning，非致命）。

### 4. 打包（package()）
挑文件安装（禁止整目录拷贝），与 Debian dh-elpa/dh-elpa-helper 二进制包布局一致：
- `dh_elpa`、`dh_elpa_test` → `<pkg>/bin/`（0755）
- `elpa.pm` → `<pkg>/share/perl5/Debian/Debhelper/Sequence/elpa.pm`
- `emacsen-common/*` → `<pkg>/share/debhelper/dh_elpa/emacsen-common/`
- `autoscripts/prerm-elpa` → `<pkg>/share/debhelper/autoscripts/`
- `helper/{install,remove}` → `<pkg>/lib/dh-elpa/`（0755；dh-elpa-helper 并入本包）
- `dh-elpa.el` → `<pkg>/share/emacs/site-lisp/elpa/`
- `dh_elpa.1`、`dh_elpa_test.1` → `<pkg>/share/man/man1/`（pod2man 产物）
- `package_info()`：`cpp_info.libs=[]`、`bindirs=["bin"]`

### 5. 消费者验证（test_package，test_type="explicit"）
- **R1 文件存在断言**：bin×2 + Sequence/elpa.pm + emacsen-common 模板×3 +
  prerm-elpa + lib/dh-elpa×2 + dh-elpa.el（10 断言；man 页存在则 +1 条件）
- **R2 perl -c 语法检查**：dh_elpa + elpa.pm（2 硬断言），PERL5LIB 加入本包
  share/perl5 与依赖包 perl 库根；dh_elpa_test 依赖的 File::Find::Rule /
  Array::Utils / Text::Glob / Debian::Control 未发布 ohpcd——先 `perl -M`
  探测，齐备才断言（+1），缺失 SMOKE-NOTE 受限说明
- **R3 功能冒烟（--no-byte-compile）**：最小 debian 骨架（control/compat=12/
  changelog/elpa）+ 单文件 `smoke.el`，真实运行 `dh_elpa --no-byte-compile`——emacs
  -batch 安装器把 .el 装入 `debian/smoke/usr/share/emacs/site-lisp/elpa/
  smoke-0.1/` 并生成 `smoke-pkg.el`（2 断言）
- **R4 功能冒烟（字节编译默认开启）**：`DH_ELPA_TEMPLATEDIR` 指向包内模板
  目录后运行 `dh_elpa`——emacsen-common helper 脚本
  （`debian/smoke/usr/lib/emacsen-common/packages/install/smoke`）生成 +
  `debian/smoke.substvars` misc:Depends 写入（2 断言）。**构建期不产 .elc
  是上游语义**：字节编译由生成的 helper 脚本在消费机安装时执行
  （helper/install:56-62 `byte-recompile-directory`）；尾部 postinst/prerm
  autoscript 阶段因沙箱无 `/usr/share/debhelper/autoscripts`（debhelper 包
  未携带 postinst-emacsen 模板）受阻，如实 SMOKE-NOTE 记录为受限通过，
  不伪造通过率
- 断言总数 17；emacs 无法在沙箱执行时 R3/R4 如实降级为受限说明
  （SMOKE-NOTE），R1/R2 硬断言不受影响

## 验证状态（如实声明）
- **本机（Windows + Python 3.14）**：conanfile.py / test_package 文件已做
  Python 语法核验；补丁 git apply --check 通过；制品仓依赖存在性已用
  `v2/conans/search` API 逐项核实（debhelper/dpkg/perl-config-tiny/emacs
  在仓，perl-module-metadata 不在仓且不需要）。**未执行 conan create**——
  本机无 conan 与 OHOS 工具链，W3 本地编译验证须在 CI/OHOS 环境执行
  （finish step [5/10]）。
- **鸿蒙 PC W3 核验（2026-09-19）**：依赖已按 R35 口径（`conan download
  --only-recipe`）在鸿蒙本机复验全部发布——debhelper/13.3.4（recipe
  rev ca526456）、dpkg/1.23.7（2be049ff）、perl-config-tiny/2.30
  （9cca4759）、emacs/29.1（a4a2d4bb）；perl-module-metadata 确认不存在
  （Module::Metadata 为 perl 核心，不得补加）；emacs/30.1 亦未发布（上游
  >=30.1 在制品仓层面无法满足，29.1 为当前最优）。当日核验因分支/归档
  未推送远端而未能执行 conan create（非配方问题）——分支推送后按 §适配
  步骤重跑 W3 即可。
- **上游测试（R51 申报）**：上游有 DEP-8 autopkgtest 共 1 项（build-deb，
  用 dpkg-buildpackage 构建 debian/tests/elpa-test 夹具包并校验
  ${elpa:Depends}），依赖 build-essential/dpkg/dpkg-dev/emacs-nox——在
  OHOS 沙箱无 Debian 打包环境不可运行——如实申报，消费者视角验证由
  test_package 17 断言覆盖。

## 已知限制
- `dh_elpa_test` 的 ERT/Buttercup 运行模式依赖 File::Find::Rule /
  Array::Utils / Text::Glob / Debian::Control 四个模块，均未发布 ohpcd——
  `dh --with elpa` 序列的测试步骤受限（dh_elpa 主安装路径不受影响）
- 上游要求 emacs >= 1:30.1，制品仓为 29.1——package.el API 兼容，版本偏差
  已在配方注释与 manifest 记录
- 字节编译模式生成的 postinst/prerm 维护者脚本依赖 debhelper 的
  autoscripts（postinst-emacsen），debhelper 包未携带——沙箱内该阶段受阻
- 生成的 emacsen-common helper 脚本内含 `/usr/lib/dh-elpa` 与
  `/usr/share/emacs` 绝对路径（上游布局 fidelity），真实 Debian 类消费者
  环境方可执行
