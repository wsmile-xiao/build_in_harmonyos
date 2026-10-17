# DRAFT-makedepend-1.0.10-test-package-inplace-build-pollution — test_package 无 layout 时就地构建，test.sh 自建工作目录会被误提交

> **Contributor**: OpenDesk (K4T9) | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: medium | **Category**: conan / test-package / repo-hygiene
> **Audience**: 所有为 application（可执行）包编写 test_package/test.sh 的适配者

## 问题（Symptom）

`conan create` 跑通后 `git add`，提交里**混入了测试运行时产物**（本应只提交 3 个测试文件）：

```console
$ git diff --cached --name-only | grep work/
archives/m/makedepend/1.0.10/test_package/work/Makefile
archives/m/makedepend/1.0.10/test_package/work/demo.c
archives/m/makedepend/1.0.10/test_package/work/dep.h
archives/m/makedepend/1.0.10/test_package/work/no-makefile/standalone.c
```

若未及时发现，这些产物会进 PR，触发 JC4（临时构建产物）/ 原子性审查问题。

## 根因（Root Cause）

1. `test_package/conanfile.py` 未定义 `layout()` 时，Conan 2 把 **test package 的 build folder 直接设为
   test_package 源目录**。`conan create` 日志可直证：

   ```text
   makedepend/1.0.10 (test package): Test package build folder:
       /storage/.../archives/m/makedepend/1.0.10/test_package
   makedepend/1.0.10 (test package): Writing generators to .../test_package
   ```

2. 因此 `test.sh` 里任何"在当前目录创建文件"的写法（`workdir="work"`、`mkdir`、`touch`、
   生成 `Makefile`/`*.c`）都落在**仓库工作区**里。
3. Conan 自己生成的 `conanbuild.sh` / `conanrun.sh` / `metadata/` 已被根 `.gitignore`
   覆盖（`**/test_package/conanbuild*.sh` 等），但**测试脚本自建的业务目录没有兜底规则**，
   于是被 `git add` 一并收集。

## 方案（Recovery，照仓内先例）

用 `${TMPDIR:-$PWD}` 下的唯一目录 + `trap` 退出清理（先例：
`archives/a/abnfgen/0.21/test_package/test_abnfgen.sh`、`archives/a/aaphoto/0.45/test_package/test.sh`）：

```bash
#!/data/service/hnp/bin/bash
set -eu

workdir="${TMPDIR:-$PWD}/makedepend-test-$$"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"
cd "$workdir"
# …后续断言全部在 $workdir 内进行…
```

修复后复验（本次实测）：再跑 `conan create`，`test_package/` 下**不再出现** `work/`，
只剩 `MANIFEST.yml` / `conanfile.py` / `test.sh` 三个受控文件（与 `archives/b/bmake/20200710/test_package/`
的干净形态一致）。

> 注意 `$TMPDIR` 的优先级：OHOS 上 `/tmp` 只读（见 E002、FAQ），所以
> `TMPDIR` 未设置时退到 `$PWD` 也安全；若测试必须写到设备本地可写目录，
> 参照 libassuan/3.0.2.1 notes 的 `/data/storage/el2/base/cache` 做法。

## 查重差异（为何新增）

| 既有条目 | 主题 | 差异 |
|---|---|---|
| E225（正式，预审提示相似 0.39） | CMakeToolchain 默认向 test_package source 写 `CMakeUserPresets.json` 引发的问题 | 同属"Conan 在 test_package 源目录落文件"，但主体不同：E225 的落文件者是 **Conan 生成器**（可由配置关闭）、对象是固定 presets 文件；本条落文件者是**测试脚本自身**创建的业务工作目录（任意中间产物），对策完全不同（生成器侧规避 vs 脚本侧 `$TMPDIR`+`trap`） |
| 根 `.gitignore` 中的 `**/test_package/conanrun*.sh` 等规则 | 只覆盖 **Conan 生成的**环境脚本 | 不覆盖测试脚本自建目录（如 `work/`），本条目补这一缺口 |
| E002 / FAQ（TMPDIR、/tmp 只读） | 临时目录位置与只读/权限 | 讲"写哪里"，不讲"写到源目录会被误提交" |
| DRAFT-6048/6052（test_package 相关） | 各库测试脚本的具体行为问题 | 非"就地构建导致仓库污染"这一共性机制 |

结论：知识库无"test_package 就地构建 → 自建工作目录被误提交 → `$TMPDIR`+`trap` 兜底"的条目。

## 禁止事项（forbid）

- ❌ 用 `git rm --cached` 事后打补丁而不改测试脚本（下次 `conan create` 会再次污染）
- ❌ 为掩盖问题往 `.gitignore` 加宽泛规则（如 `**/work/`）——可能误伤真实源码目录
- ❌ 把测试脚本改成不落盘的"纯 print"形态以规避（违反 PF3/R34：`test()` 必须有实际执行逻辑）
