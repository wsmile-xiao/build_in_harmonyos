# slugify 1.0.1 适配笔记

## 编译环境
- 构建系统: none（纯 bash 脚本，只装不编）
- 适配日期: 2026-09-28
- 解释器: bash/5.3（制品仓 ohpcd，aarch64 OHOS 构建，无 PT_INTERP 可在 x86 runner 经 qemu binfmt 运行）
- 状态: built
- 构建机: x86_64 runner，profile `ci/conan/profiles/ohos-aarch64`

## 上游与源码
- 仓库: https://github.com/JabberLabs/slugify（原 benlinton/slugify，MIT）
- tag v1.0.1 = commit `22584c704d577109cca8e217fce0396b362b6095`
- 源码包: `https://github.com/JabberLabs/slugify/archive/refs/tags/v1.0.1.tar.gz`，
  sha256 `f6873b062119d3eaa7d89254fc6e241debf074da02e3189f12e08b372af096e5`，
  仅含 `README.md`、`slugify`、`slugify.1`、`slugify.1.ronn` 四个文件
- LICENSE: tag 归档中没有。作者在紧随其后的提交 `b2a371b3fdb05fa34f57a259b4acd81b6066cda4`
  （"Add MIT license"，父提交即 v1.0.1，只新增 LICENSE）补入；配方固定到该提交下载
  （`https://github.com/JabberLabs/slugify/raw/<commit>/LICENSE`：github.com 域名可走 CI 的镜像 fallback，
  raw.githubusercontent.com 不在其映射表内且本机直连多次超时），
  sha256 `cbb6c2a45b78dcd895e251aa96f89ebb22b5f8196ca6b389e13a39c471079abf`，
  git blob `d766444d` 与上游 master 的 LICENSE 一致

## 前置检查
- W0 依赖: `conan download bash/5.3 -r=ohpcd --only-recipe` 成功（recipe rev `ee1787fd11ca391a9526bf13db0cce51`，
  二进制 package rev `450b7b2ec0e27ac1220ebc565f4d00a4` 可下载）。`tr`/`sed`/`mv` 为系统命令（鸿蒙上由 toybox 提供），无 Conan 依赖
- W0b 历史: 仓库无 slugify 归档（`archives/p/python-slugify` 是不相关的 Python 库）；参照同形态已合并先例
  `cronic/3`（bash 脚本、显式 `bash <pkg>/bin/…` 调用）、`bamclipper/1.0.0`、`bash-argsparse`（`requires("bash/5.3")`）
- lang-preflight: `--lang other` → detected `other`（无语言 manifest；判定器按扩展名计数，无扩展名的 bash 主脚本计 0）。
  默认 `cpp` 口径会误判并自动写 `env_unsupported` 终态，故按 cronic/zgen 先例以 `other` 申报；CI 能力矩阵中 bash 脚本类为 ✅

## 适配步骤
1. `init-build slugify 1.0.1 --url=<tag 归档>`；`.work` 与 `.orig` 为硬链接（E543），解包后立即逐文件
   `cp --remove-destination` 断链
2. 在 `.work/slugify` 修改改名逻辑（见「源码修改」），`refresh-patch --auto` 生成 `patches/0001-slugify.patch`
3. `conan-init` 按 manifest 的 `build.system` 选模板：init-build 把它写成 `autotools`，且 `software`、
   `build_system` 字段留着未替换的模板占位符；先改为 `headeronly` 再生成，随后按脚本工具形态重写 conanfile / test_package
4. 配方：`package_type=application`，`requires("bash/5.3", run=True)`（解释器二进制随消费者安装，VirtualRunEnv 把其 bin 放进运行期 PATH）；
   `build()` 打补丁后用 bash/5.3 做 `bash -n` 语法检查；`package()` 安装 `bin/slugify`、`share/man/man1/slugify.1`、
   `licenses/LICENSE`；`package_id()` 清空（纯脚本单一包 ID）
5. `conan-verify` G1–G4、L2/L4/L5 全通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 鸿蒙 PC 用户存储上 `slugify README.md` 输出 `conflict: README.md`，不改名 | HMDFS 大小写不敏感，`[ -e readme.md ]` 命中源文件自身；上游只按 `$OSTYPE=darwin*` 特判，鸿蒙 bash 的 OSTYPE 是 `linux-gnu` | 补丁：目标与源为同一文件（`-ef`）时视为大小写别名，不判冲突（知识草稿 E429-draft-B041） |
| 2 | 跳过检查直接改名也无效 | 同一 inode 两个名字间 `rename(2)` 是 no-op，GNU mv 报 `are the same file`（vfat 实测 mv rc=1；os.rename 成功但名字不变） | 经同目录临时名 `${source%/}.slugify.$$` 两步改名；临时名去尾斜杠兼容 `Photos/` 这类参数 |
| 3 | 别名判断会把「目标恰为源的硬链接/符号链接」也当成同一文件 | `-ef` 比较 inode 且跟随符号链接 | 第一步改名后若目标名仍存在（独立目录项），立即还原并照旧报 `conflict`，不覆盖、不丢链接 |
| 4 | 鸿蒙上无法直接执行 `#!/usr/bin/env bash` 脚本 | 无 `/usr/bin/env`（E037）；HMDFS 用户分区对 `#!` 脚本 exec 一律 EACCES（DRAFT-cdb-20251021） | 不改 shebang（Linux 上仍可直接执行）；`run=True` 让 bash/5.3 的 bin 进入消费者运行期 PATH，鸿蒙上以 `bash "$(command -v slugify)" …` 调用；测试按此形态调用，且不依赖执行位查找脚本 |
| 5 | v1.0.1 归档无 LICENSE | 上游在 tag 之后一个提交才加 | conandata `license` 键固定到提交 b2a371b 下载并校验 sha256（CI 预下载会提取 conandata 中全部 URL） |
| 6 | G2 结束后遗留 `conandata.yml.ghfast-bak` | conan_verify 的 finally 只还原 conandata.yml、不删备份 | 核对与 conandata.yml 一致后删除（已 gitignore，另在 SKILL_FEEDBACK 反馈） |
| 7 | finish 内 conan-verify 复用缓存包时 `package_info()` 报 `TypeError: expected str, bytes or os.PathLike object, not NoneType` | 普通 `requires` 下 application 包的依赖被标为 Skipped binaries，`self.dependencies["bash"].package_folder` 为 None（与 DRAFT-conan-runtime-interpreter-package-no-bin-path 同源） | 改为 `requires("bash/5.3", run=True)`，删除 `package_info()` 中对依赖路径的引用 |
| 8 | W3 L1e 判 `negative test: test does not depend on package` | L1e 重跑 `conan test` 只传 `-pr`，build profile 回落本机默认（Linux x86_64），test() 的 `can_run()` 早退让测试体被跳过（DRAFT-probalign-1.4-l1e-conan-test-missing-build-profile） | 去掉 `can_run()` 早退：跑不了 bash/5.3 的机器应当失败，而不是不执行就报通过 |
| 9 | W3 结束后工作区 `conandata.yml` 被改成 gh-proxy 镜像列表，并留下 `conandata.yml.orig` | build_and_test.sh 的 mirror fallback 就地改写，预下载的 EXIT trap 只还原到改写后的版本 | `git checkout` 还原并删除备份（PF7 拦镜像域名；另在 SKILL_FEEDBACK 反馈） |

## 源码修改
`patches/0001-slugify.patch`（patch_type: portability，不含平台宏，对任意大小写不敏感文件系统生效）：
- 新增 `case_alias`：`[ "$source" -ef "$target" ]` 为真时置 1
- 冲突条件由 `[ -e "$target" -a $case_sensitive_filesystem -eq 1 ]` 改为再加 `-a $case_alias -eq 0`
- 别名改名：临时名 `${source%/}.slugify.$$` 已被占用则报 `conflict`；否则 `mv 源 临时名`，若目标名仍存在则还原并报 `conflict`，
  否则 `mv 临时名 目标`（失败则改回源名）
- 大小写敏感 FS 上行为与上游一致；已知差异：dry-run 对「目标恰为源的硬链接/符号链接」预演为 `rename`，实跑报 `conflict`

## 依赖版本
- bash/5.3（requires，运行期解释器）
- 系统命令 tr、sed、mv

## 上游测试清点（R51）
- 源码包 4 个文件，无 `tests/` 目录、无构建系统（无 make check / ctest / pytest 注册项）、无 CI 配置；
  GitHub master 目录树仅多一个 LICENSE → 上游自动化测试 **0**
- README「Usage Examples」给出 19 条带期望输出的用法示例 → 全部转成 `test_package/test_slugify.sh` 的 18 个用例
  （转义与加引号两种写法是同一文件名，合为 1 例）。两处 README 文字与 1.0.1 代码输出不一致，用例按代码断言：
  dry-run 不带 `-v` 时不打印 `ignore:` 行；`-vac` 示例回显的源文件名应保留三个空格

## 验证结果

### finish W3 本地 CI（ci/conan/build_and_test.sh）
```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed          # README 18/18、鸿蒙特有 5/5
[ok] L1e: Negative test confirmed — test genuinely depends on slugify   # bin/ 移走后 conan test 失败
L2_RESULT=skip: slugify version/help failed    # 非阻塞：上游脚本没有 --version/--help 长选项
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Pass rate: 100.0% (1/1)
```

### conan-verify（G2 conan create 内的 test_package，ext4 大小写敏感）
```
README usage cases: 18/18 passed
# interpreter : …/bash/5.3…/bin/bash (5.3.0(1)-release, aarch64-unknown-linux-gnu)
# filesystem  : case-sensitive -> plain rename path
HarmonyOS-specific consumer cases: 5/5 passed
```

### 大小写不敏感文件系统实测（本地 vfat 回环挂载，模拟 HMDFS 语义）
打包产物 `bin/slugify` + bash/5.3（qemu binfmt 执行 aarch64 二进制），`SLUGIFY_TEST_ROOT=<vfat 挂载点>`：
```
# filesystem  : case-insensitive (HMDFS-like) -> patched alias path
HarmonyOS-specific consumer cases: 5/5 passed      exit=0
README usage cases: 18/18 passed                   exit=0
```
补充探针：slugify 的 `-a` 依赖 `sed 's/\- /-/'`，鸿蒙上 sed 由 toybox 提供、正则走 libc。用 OHOS NDK clang 静态编译调用
`regcomp`/`regexec` 的探针在 qemu 下实测：BRE `\- ` 与 ` \-` 均编译成功并按字面 `-` 匹配（与 GNU sed 一致）。

反向对照：同一环境换成未打补丁的上游 1.0.1 脚本：
```
FAIL [1] HC-1 …  conflict: README.md / conflict: Photo.JPG
FAIL [2] HC-2 …  conflict: Photos/
FAIL [3] HC-3 …  dry run 预演为 conflict
PASS [4] HC-4
FAIL [5] HC-5 …  link 'README.md' is not web friendly
HarmonyOS-specific consumer cases: 1/5 passed      exit=1
```

## 鸿蒙特有测试（rule12）
`test_package/test_slugify_ohos.sh`，5 个端到端消费者用例。消费者从 conanrun 环境的 PATH 找到打包的 slugify
（不依赖执行位），经 bash/5.3 显式解释执行，对临时目录中的真实文件改名，再核对输出、目录项与文件内容：
- HC-1 文件仅大小写改名（README.md、Photo.JPG → readme.md、photo.jpg，notes.txt 保持）
- HC-2 目录仅大小写改名，参数带 Tab 补全尾斜杠（Photos/ → photos/，子文件完好）
- HC-3 dry-run 预演仅大小写改名，目录不变
- HC-4 真冲突（My File.txt 与已有的另一个 my_file.txt）仍拒绝；大小写敏感 FS 上另构造同 inode 硬链接与指向源的符号链接，
  验证补丁的还原分支
- HC-5 Web 发布流水线：`slugify -ac *` 规范化下载目录 → 消费者按实际存储的名字生成 index.html → 逐个链接按精确名（大小写敏感，
  同 Web 服务器）解析并核对内容

执行情况：大小写不敏感存储（HMDFS；本地 vfat 实测）上 HC-1/2/3/5 走补丁新增的别名分支；大小写敏感 FS（本地 ext4，
以及工作目录不在 HMDFS 上的 CI worker）上同一用例走普通改名分支、期望结果相同，用例不 skip；HC-4 的还原分支只能在
大小写敏感 FS 上构造。CI 实际走哪条分支以日志中驱动打印的 `# filesystem :` 行为准。
以上均为本地实跑（x86 runner + qemu 执行 OHOS bash），非鸿蒙真机：解释器是 bash/5.3（OHOS 构建），但脚本调用的
`tr`/`sed`/`mv` 是 x86 宿主的 GNU coreutils，不是鸿蒙 toybox；vfat 只复现了大小写不敏感语义，HMDFS 本身未实测。

## 注意事项
- 鸿蒙上调用方式：`bash "$(command -v slugify)" [-acdhintuv] 文件…`（Conan 消费者的 conanrun 环境已把 bash/5.3 与本包 bin 前置进 PATH）
- slugify 只处理参数给出的条目本身，不递归目录
- `tr A-Z a-z` 只转换 ASCII 字母，非 ASCII 文件名的大小写保持原样（上游行为）
---

**编译结束**: 2026-09-28 08:23（finish W3 通过）
**最终状态**: built
