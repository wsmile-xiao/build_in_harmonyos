# DRAFT-LOCAL-VERIFY-STALE-PKG-FOLDER-AND-PRECOMMIT-GATE — 改配方后本地复验的两个静默陷阱

## 错误特征

### (a) 改了 `package()` 但 `conan create` 好像没生效

```
pd-ggee/0.28: Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created
# CREATE_RC=0，看起来一切正常
$ ls <pkg>/lib/pd-externals
control  experimental  filters  ggee-meta.pd  gui  logo100.gif  other  signal  state.list
                                     ^^^^^^^^^ 明明把 keep_path 改成了 False，这里却还在
```

或者反过来：把 `keep_path=False` 改成 `True` 想保留目录结构，结果**新旧位置各一份**。

### (b) 分支还没提交就跑本地门禁，JC1/JC5 凭空变红

```
[step] JC1: 运行时状态文件检查...
[FAIL] JC1: 5 个运行时状态文件被跟踪:
       archives/c/cloog/0.21.1/.build-closed
       archives/c/cloog/0.21.1/.staging-verified
       archives/k/kics/2.1.20/.staging-verified
       archives/l/libbfio/20260623/.staging-verified
       archives/t/thc/3.8/.staging-verified
[FAIL] JC5: 5 个 archives 下未登记的隐藏文件
[step] JC6: PR 单软件原子性检查...
  full 模式（整仓扫描），跳过单软件检
JC_RESULT=fail
JC_ERRORS=2
L1_RESULT=skip: blocked_by_JC
```

注意被点名的包**一个都不是你正在做的包**。

## 触发条件

- 阶段: build / test / 本地门禁
- (a) 修改了 `package()`，且该 package_id 之前已构建过
- (b) 在工作区有未提交的新文件时启动 `ci/conan/build_and_test.sh`

## 根因分析

### (a) package_id 不含 `package()` 的实现，`copy()` 只写不删

`package_id` 只由 settings / options / requires 决定。Conan 认为同一个 package_id 的产物是
同一个东西，于是复用已有的 package folder。而 `conan.tools.files.copy()` **只往目标目录写
文件、从不清理**：

- 改 `keep_path=True → False`：新位置写出文件，旧位置的文件**不会被删**，两个位置同时存在；
- 改 `False → True`：同理，扁平位置残留。

所以 `conan create` 返回 rc=0 也**不能**说明布局改对了。必须直接 `ls` 包目录核对。

### (b) 门禁的单软件/整仓模式取决于「相对 merge-base 的 diff」

`ci/conan/build_and_test.sh` 会先算 PR diff 来决定 JC1/JC5/JC6 用单软件还是整仓模式。
工作区里有**未提交**的新文件时它拿不到 diff，于是打印 `full 模式（整仓扫描），跳过单软件检`，
JC1/JC5 扫全仓——命中的 `archives/c/cloog/...`、`archives/t/thc/...` 等是 `origin/main`
**本来就已经跟踪**的隐藏运行时文件，与本次改动无关。

判据（一行定生死）：

```bash
git cat-file -e origin/main:archives/c/cloog/0.21.1/.build-closed && echo STALE_IN_MAIN
```

命中即存量问题。

## 解决方案

### 固化顺序，不要跳步

```bash
# ① 先 commit（哪怕内容还没最终定），再跑本地门禁 —— 门禁结果才有意义
git add <显式路径> && git commit -m ...
CI_BRANCH=feat/<pkg>-<ver> CONAN_PROFILE=ohos-aarch64-wsl \
  CI_PACKAGES="archives/<x>/<pkg>/<ver>" zsh ci/conan/build_and_test.sh

# ② 改了 package() 先清缓存再复验
conan remove "<name>/<version>" -c
conan create <pkgdir> --name=<name> --version=<ver> \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing

# ③ 直接核对包目录，不要只看 rc=0
D=$(ls -d /root/.conan2/p/b/<pkg-prefix>*/p | tail -1)
ls "$D/lib"; find "$D/lib" -mindepth 1 -type d | wc -l
```

### JC 报警先判存量

```bash
git cat-file -e origin/main:<被点名的隐藏文件路径> && echo "存量残留，与本 PR 无关"
```

存量残留**不要**去改别人的归档目录（越权），也不要为它改自己的配方。

### 提交/推送前的最后一道复核

门禁运行期间会临时把 `conandata.yml` 改写成 `file://.../.build-cache/...` 再在退出时还原。
提交前必须确认：

```bash
grep -c 'file://' archives/<x>/<pkg>/<ver>/conandata.yml   # 必须是 0
git status --short
```

## 验证

```bash
# (a) 缓存复用会掩盖改动
conan remove "pd-ggee/0.28" -c          # 清掉
conan create ... > /dev/null 2>&1
find <pkgfolder>/lib -name 'state.list'  # 期望只有 1 处

# (b) JC 报警归属
git cat-file -e origin/main:archives/t/thc/3.8/.staging-verified && echo STALE_IN_MAIN
```

## 禁止做法

- ❌ 改完 `package()` 不清 conan 缓存就复验。
- ❌ 在 `git commit` 之前跑本地门禁，并把 full 模式下的 JC 报警当成自己引入的。
- ❌ `git add -A`：`.build-cache/`（门禁 predl 缓存）未被 gitignore，会被带进提交并触发 JC3/JC5。
- ❌ 为不存在的缺陷去改别人的归档目录。
