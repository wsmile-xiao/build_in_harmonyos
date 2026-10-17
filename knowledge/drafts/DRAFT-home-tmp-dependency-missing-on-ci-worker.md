# DRAFT-home-tmp-dependency-missing-on-ci-worker — ${HOME}/tmp 父目录假设：本地绿、CI 红

## 现象 (What happened)

libexif-gtk 0.5.0（OHOS PC 适配）的**本地**全部通过：

```
$ conan create archives/l/libexif-gtk/0.5.0 -pr:h=… -pr:b=… --build=missing
libexif-gtk/0.5.0: Package '2b456a561e14c868e246ae0c264ebfd74c6ddb4b' built / created
libexif-gtk 0.5.0 test_package: 6 checks, 0 failed          # exit 0
$ zsh ci/conan/build_and_test.sh archives/l/libexif-gtk/0.5.0
JC=pass  L0=pass  L1=pass  L2=skip  L4=warn  L5=pass   Pass rate 100%   # exit 0
```

同一 commit 的 **CI**（PR #11607，build #54325，worker `OpenHarmonyPCDeveloper-CI-030`）却在
`conan-build-test` 步骤失败（`conan-build-test ❌`，exit 1），失败点：

```
checking whether to use NLS... no
...
configure: creating ./config.status
mkdir: '/storage/Users/currentUser/tmp/conf8316-11777': No such file or directory
config.status: error: cannot create a temporary directory in .

libexif-gtk/0.5.0: ERROR: Package '2b456a56…' build failed
ERROR: libexif-gtk/0.5.0: Error in build() method, line 123
	autotools.configure()
	ConanException: Error 1 while executing
```

> CI 的失败诊断类别显示为「**未知**」（未自动归类），只能靠人读日志定位。

## 根因 (Root cause)

HMDFS 上 `umask 077 && mktemp -d` 生成的目录不可写（`drwx--S---`），于是既定修法是把
configure 的 `ac_tmp` 改到 **`${HOME}/tmp`** 并把 umask 降到 022（知识库 E136 / E114；
同族 `libexif/0.6.26.1` 配方就是这一方案）。

该修法隐含一个**未声明的假设：`${HOME}/tmp` 已经存在**：

| 环境 | $HOME | $HOME/tmp | 结果 |
|---|---|---|---|
| 本地探索机 | `/storage/Users/currentUser` | **已存在**（本项目 TMPDIR 默认就是 `~/tmp`，由历史脚本创建） | `mktemp -d "${HOME}/tmp/confXXXXXX"` 成功 → 全绿 |
| CI worker | `/storage/Users/currentUser`（TMPDIR=`/data/storage/el2/base/cache`） | **不存在** | `mktemp -d` 报 `ENOENT` → 在下游 `config.status` 阶段炸掉 |

而 fallback 分支写的是 `mkdir "$tmp"`（**没有 `-p`**），父目录不存在时同样失败。

两点使问题更隐蔽：
1. 报错出现在 **config.status**（不是 configure 的早期步骤），容易被误判成“权限/文件系统”问题；
2. **本地无论如何重跑都复现不到**（本机 `$HOME/tmp` 恰好存在），只能靠隔离 HOME 复现。

## 隔离复现（秒级，无需 CI）

```bash
mkdir -p /tmp/fakehome                      # 存在，但里面没有 tmp/
HOME=/tmp/fakehome ./configure --prefix=/usr/local --with-gtk3 --disable-rpath --disable-nls; echo $?
# 修复前：
#   mkdir: '…/fakehome/tmp/confXXXX-XXXX': No such file or directory
#   config.status: error: cannot create a temporary directory in .        → exit 1
# 修复后：
#   exit 0，且 …/fakehome/tmp 被自动创建
```

本 PR 的 A/B 实证（同一源码树、只换补丁版本）：

| 补丁 | HOME | exit | 报错 |
|---|---|---|---|
| PR 首版（`mktemp -d "${HOME}/tmp/…"`，无 `mkdir -p`） | `…/fakehome`（无 `tmp/`） | **1** | `mkdir: '…/fakehome/tmp/conf19694-1008': No such file or directory` + `cannot create a temporary directory in .`（与 CI 逐字一致） |
| 本版（两条分支各加 `mkdir -p`） | 同上 | **0** | — |

## 解法 (Fix)

两层一起做（补丁自洽 + 与同族配方一致）：

```sh
# (1) configure 补丁：两条分支都先建父目录
{
  tmp=`(umask 022 && mkdir -p "${HOME}/tmp" && mktemp -d "${HOME}/tmp/confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=${HOME}/tmp/conf$$-$RANDOM
  (umask 022 && mkdir -p "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
```

```python
# (2) 配方 build() 兜底（同族 libexif/0.6.26.1 的 E002 同款；Python 侧，非裸 shell 变量，R33 合规）
def build(self):
    apply_conandata_patches(self)
    Path(os.environ.get("HOME", "/tmp")).joinpath("tmp").mkdir(parents=True, exist_ok=True)
    autotools.configure()
```

**备选**：改用环境提供的 `TMPDIR`（CI 已注入可写目录）：`${TMPDIR:-/tmp}/confXXXXXX` + `mkdir -p`。
语义上更贴合“谁提供谁负责”，但与同族已发布配方的写法不一致。

**禁止**：把临时目录写死在 `/tmp/confXXXXXX`（OHOS 真机 `/tmp` 只读，E002）。

## 适用边界 (Applicability / Scope)

- 适用：任何把临时/缓存目录绑到 `${HOME}/…`、`~/…` 的补丁或配方，且未同时创建该目录；
  尤其是「本地探索机目录已存在、CI worker 目录不存在」的场景。
- 不适用：目标目录由环境变量显式提供且 CI/真机都保证存在（如 conan 的 `build_folder`、`generators_folder`）。
- 边界：修完后仍需在**真机**上跑一遍（本地 `$HOME/tmp` 存在会掩盖问题）；
  报告里应给出“空 HOME 复现命令”，让评审能独立验证。

## 与既有条目查重差异 (Dedup / Delta vs Existing Entries)

| 既有条目 | 差异 |
|---|---|
| `E136` / `E114` | 同族但**不同失败点**：它们解决 HMDFS 上 `umask 077` 使 mktemp 目录不可写（EACCES），本条解决**父目录不存在**（ENOENT）；E136 的推荐写法制定的正是 `${HOME}/tmp`，本条补的是它留下的目录存在性假设 |
| `E002` | `/tmp` 只读，是“不能写死 /tmp”的依据，不涉及 `${HOME}/tmp` 的创建 |
| `DRAFT-E2167-handwritten-configure-conan-injected-args` | 手写 configure 的参数注入问题，与本条（目录存在性）无关 |
| **本条** | 首发覆盖“本地绿 / CI 红”的目录假设差异，并给出秒级隔离复现法（`HOME=<无 tmp 的目录>`）与补丁+配方双层修法 |

## 参考 (References)

- 本 PR 实证：`archives/l/libexif-gtk/0.5.0/patches/0003-configure.patch`、
  `archives/l/libexif-gtk/0.5.0/conanfile.py` 的 `build()`
- CI 失败记录：PR #11607 build #54325（`conan-build-test ❌`，日志见 CI 评论“失败步骤完整日志”）
- 同族配方的兜底写法：`archives/l/libexif/0.6.26.1/conanfile.py`（`build()` 中 `home_tmp.mkdir(parents=True, exist_ok=True)`）
- 关联条目：`E136`、`E114`、`E002`
