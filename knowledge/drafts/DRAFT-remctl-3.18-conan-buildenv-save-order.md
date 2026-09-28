# DRAFT-remctl-3.18: 配方级 `Environment().define()` 覆盖 profile `[buildenv]` **静默失效**——胜负在 `conanbuild.sh` 的 source 顺序

## 一句话

要让配方覆盖 profile `[buildenv]` 里的同名变量（典型是 `CONFIG_SHELL`/`SHELL`），**必须先把 `VirtualBuildEnv(self).generate()` 调在前面**，再 `save_script` 自己的脚本；顺序反了 conan 不报错、不告警，日志与"我根本没写"完全同形。

## 症状（本包逐字首错，remctl 3.18 / 任务 10082 / build-03）

配方 `generate()` 里已经按既有写法保存了路由脚本，脚本内容也确实落盘成功：

```
$ cat <build>/conan/e386_shell_routing.sh
...
export CONFIG_SHELL="/bin/sh"
export SHELL="/bin/sh"
```

但 `conan create` 仍然死在 E386 家族首错，且日志被 getcwd 风暴刷满：

```
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
job-working-directory: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
pwd: error retrieving current directory: getcwd: cannot access parent directories: Bad address
configure: error: working directory cannot be determined
```

## 根因

`conanbuild.sh` 是一条用 `&&` 串起来的 source 链，**链序 = 各 env 脚本被保存的先后**，不是文件名字母序。而 profile 的 `[buildenv]` 由 **`VirtualBuildEnv`** 写进 `conanbuildenv-<id>.sh`。本包改前的实测链序（`tr ' &' '\n\n\n' < conanbuild.sh` 打出）：

```
e386_shell_routing.sh  ->  conanautotoolstoolchain.sh  ->  conanbuildenv-release-armv8.sh
```

同名变量**后写者胜** ⇒ 链尾的 `conanbuildenv` 把 `/bin/sh` 又覆盖回 profile 的 `/data/service/hnp/bin/bash`。

坐实这一点的三条读数（改前，全部免构建、不占设备槽）：

```
$ grep -ln 'hnp/bin/bash' conan/*.sh
conan/conanbuildenv-release-armv8.sh          ← 只有它是写者
$ /bin/sh -c '. ./conanbuild.sh; echo "SHELL=[$SHELL] CONFIG_SHELL=[$CONFIG_SHELL]"'
SHELL=[/data/service/hnp/bin/bash] CONFIG_SHELL=[/data/service/hnp/bin/bash]   ← 我的 define 没活到终点
```

## 最小复现

任一 OHOS autotools 配方，`generate()` 内按"先 save_script、后（或由框架默认顺序）落 conanbuildenv"写：

```python
def generate(self):
    sh = Environment()
    sh.define("CONFIG_SHELL", "/bin/sh")
    sh.define("SHELL", "/bin/sh")
    sh.vars(self, scope="build").save_script("e386_shell_routing")   # ← 早于 VirtualBuildEnv
    VirtualBuildEnv(self).generate()
    AutotoolsToolchain(self).generate()
```

⇒ `configure: error: working directory cannot be determined`，未修复前 100% 复现。

## 修法（只动顺序，配方零其他改动）

```python
def generate(self):
    VirtualBuildEnv(self).generate()        # 先：profile [buildenv] 落成 conanbuildenv-*.sh
    sh = Environment()                      # 后：我的覆盖排在 source 链末尾
    sh.define("CONFIG_SHELL", "/bin/sh")
    sh.define("SHELL", "/bin/sh")
    sh.vars(self, scope="build").save_script("e386_shell_routing")
    AutotoolsToolchain(self).generate()
```

改后读数：build-04 起 `configure` 完整跑完并进入 `make`；最终 **build-16 整条 `conan create` `rc=0`**（`SLOT_DONE:ok`，`MEMCAP peak=205MB`），上游测试逐字 `All tests successful, 63 tests skipped.` / `Files=57, Tests=975`（0 失败），消费者 `test_package` 逐字 `ok 1..5`。

## 为什么它比"看起来对了"更危险

- conan 不产出任何"变量被覆盖"的告警，也没有 `--verbose` 能提示；唯一真相是 `. ./conanbuild.sh` 后的终值。
- 仓库里已有多份配方（如 lksctp-tools 1.0.21）**恰好**把 `VirtualBuildEnv` 写在前面而工作正常，其注释并未说明这是顺序要求 ⇒ 照抄代码块而不核终值的窗口，会在自己包上"已经修好却又红"之间反复横跳。本窗为此烧掉一整个 `conan create` 周期（108.9s）+ 一轮定向探针。

## 适用边界 / 反例

- **只新增变量**（不与 profile `[buildenv]` 同名）时顺序无关，本条不适用。
- `[runenv]` 走的是 `conanrun.sh`，是另一条链，别把本条结论搬去改 `test_package` 环境。
- 需要"在 profile 值上再叠一层"的变量（典型是 `LD_LIBRARY_PATH`）必须用 `prepend_path` 而非 `define`：本机 profile 的 `LD_LIBRARY_PATH` 里有 lld 依赖的 `libxml2.so.16` 路径，用 `define` 会整条抹掉，症状会变成"链接期 lld 崩"这种更难归因的形态。
- 与 `AutotoolsToolchain` 无关：其生成的 `conanautotoolstoolchain.sh` **不含依赖的 `-I/-L`**（实测），那是另一个独立问题（本包按仓库既有写法用 `--with-*=<package_folder>` 显式喂），不要和顺序问题混在一起查。

## 与知识库既有条目的关系（查重结论与新增价值）

- 本仓 `draft-review` 对本草稿的机器读数为：**质量预检 signature/✅ root_cause/✅ rec/✅，预审建议 `create`，TOP4 最高相似度 0.15**（E195 0.15 / E346 0.12 / **E386 0.11** / E035 0.11），无高相似条目。
- **与 E386 的边界（必须写清，否则会被复核判"同族重复"）**：E386 描述的是"HMDFS 源码/构建树会拒绝对生成脚本的直接执行"这一**平台事实**（及其 getcwd 风暴症状）；它**不提供**"在 conan 配方里如何可靠地把 shell 路由换掉、以及换掉后为什么可能不生效"这一层。本条只讲后者：conan 的 `conanbuild.sh` source 链序决定同名 `SHELL`/`CONFIG_SHELL` 的胜者，以及三条**免构建**判别读数。两者是"平台机制"与"工具链使用它的生效条件"的关系，不重叠。
- **同症状同根因**：`DRAFT-6487-classads-configshell-hmdfs-getcwd`。但该条给出的 `approach` 是「`build()` 的 run 命令里内联前缀 `CONFIG_SHELL=/bin/sh`」，**没有覆盖 `generate()` + env 脚本这条路，更没有"它会被 `VirtualBuildEnv` 的落位顺序吃掉"这一失效条件与免构建判别法**。按 AGENTS §6.2 命中条件②（症状相同而使用既有条目未写的另一条解法 ⇒ 按 create 申报），本条申报为新增知识，并与该条互指。
- `DRAFT-E551`（`CONFIG_SHELL=bash` 老 `ltmain.sh` 丢引号转义）手段相同、根因不同，不构成本条的重复。
- 触发面不限于 autotools：任何在 OHOS profile 下需要覆盖 `[buildenv]` 的配方（cmake/meson 同用 `VirtualBuildEnv`）都会撞上，属**平台侧通用机制**而非 remctl 包特有。
