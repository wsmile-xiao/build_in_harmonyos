# 同一条上游仓库里有 Meson 与 Autotools 两条构建线时，选 Meson 能一次性绕开 Autotools 在 HMDFS 上的三类环境坑

- **id**: `DRAFT-6818-libdb-5.3.35-meson-sidesteps-autotools-hmdfs-pits`
- **severity**: 1（构建直接失败 / 产物不全）
- **category**: build, portability, conan, filesystem, ohos
- **来源**: `archives/l/libdb/5.3.35` 适配（PR 11637，平台任务 #6818）
- **状态**: UNMATCHED（草稿，待审）

## 一句话

Autotools 生成物（`configure` / `config.status` / `config.guess` / `config.sub` / `libtool`）在
HarmonyOS PC 的 HMDFS 上会踩三类坑；**Meson 不生成 `config.status`、不生成 libtool**，
所以只要上游同时提供 Meson 线，选它就能一次绕开全部三类 —— 判据是产物树里
**有没有那两个文件**，而不是主观偏好。

## 三类坑

| # | 坑 | 触发点 | 症状 |
|---|---|---|---|
| ① | 回显探测假阳性 | `dist/configure` 用当前 shell 跑 `print -r --` 探针，ksh/zsh 下 `print` 是内建 → 探测「成功」→ 把 `ECHO='print -r --'` 固化进 `config.status` | 构建期 `config.status` 由 `/bin/sh` 执行，`print` 不存在 → `print: command not found`，往往在写 Makefile 中途炸，表现为产物不全 |
| ② | `umask 077 && mktemp -d ./confXXXXXX` 拒写 | `dist/configure:29848` 的 `config.status` 逻辑 | setgid 目录上 mktemp 失败 → `cannot create`；隐蔽版本会继续跑，后续 sed 步骤找不到临时文件 |
| ③ | `config.guess` / `config.sub` 时代过旧 | 5.3.28 线随包发布的时间戳是 `2011-11-11` | `checking host system type` 判定 unknown → 走错平台分支 |

三者的共同点：**都发生在 Autotools 生成物里，不在库源码里**。

## 判据（可复现）

```bash
# 乘积树里有没有那两个文件 —— 有就暴露，没有就全部不存在
find <builddir> -maxdepth 2 \( -name 'config.status' -o -name 'libtool' \)

# 三类坑各自的定位命令（Autotools 线）
grep -n 'print -r --'        dist/configure   # → 9386-9388
grep -n 'umask 077 && mktemp' dist/configure  # → 29848
head -3                      dist/config.guess  # → timestamp='2011-11-11'
```

## 实证与反面

- **正面（选 Meson）**：`libdb/5.3.35` 走 Meson，补丁数 **1**（版本元数据对齐），
  产物树里没有 `config.status` / `libtool`。
- **反面（留在 Autotools）**：同源 BDB 的两条已入库配方 `berkeley-db5/5.3.28`、
  `db/6.2.32` **都实证过**这三坑，两者都额外携带 `config.guess` / `config.sub` 补丁。
- **回退可行性**：`berkeley-db5` 的那两个补丁对 libdb 5.3.35 的 `dist/` 能
  `patch -p1 --dry-run` 干净应用（两侧 `config.guess` 时间戳同为 2011-11-11），
  但仍需另补 `print` 与 `umask` 两个补丁 —— 即「补丁最少」这个判据也指向 Meson。

## 配方侧落地

```python
def build_requirements(self):
    self.tool_requires("meson/1.11.0")   # L0：tool_requires 不得带版本范围

def build(self):
    apply_conandata_patches(self)
    self.run("PATH=/data/service/hnp/bin:$PATH CC=.../clang AR=.../llvm-ar "
             "meson setup <bdir> <src> --buildtype=release "
             "-Ddefault_library=static", cwd=self.build_folder, env="conanbuild")
    # -j1 是铁律：OHOS 沙箱不支持 mkfifo，jobserver 会炸
    self.run("PATH=/data/service/hnp/bin:$PATH meson compile -C <bdir> -j1",
             env="conanbuild")
```

## 不要这么做

- `autoreconf -fi` 重新生成 → 生成物与上游发布物不一致，且 autoreconf 自身也要碰
  `config.guess`/`config.sub`，等于换个入口再踩一遍。
- `chmod g-s` / `chmod 777` / `mount -o remount,rw` 去迁就 mktemp → 改变被测环境，
  真机/CI 行为不一致。
- `echo ... > config.status` / `touch libtool` 伪造生成物 → 把配置期的确定性失败
  推迟成难以定位的编译期/链接期失败。

## 相关条目

- `E002` —— 鸿蒙 `/tmp` 是 erofs 只读挂载（同属「上游把平台的文件系统/shell 语义当不变量」家族）
- `DRAFT-lazperf-3.4.0-tests-hardcoded-var-tmp-readonly-rootfs` —— 同家族的**测试夹具**版
- `DRAFT-6818-libdb-5.3.35-fork-version-strings-drift-from-release` —— 同批适配的另一条：
  换构建线之后版本元数据没跟着换
