# DRAFT-E571：libcheck 在只读 /tmp 的 OHOS 上无需私有自建 —— TEMP 是最高优先候选

> Contributor: Awstme | Status: Draft | Updated: 2026-09-11
> Source: PR（本 PR）libtsm 4.3.0 适配 —— 设备原生上游测试阶段实测

## 背景

libcheck（`check`）是很多 C 项目的上游测试框架：`test/meson.build` 里
`dependency('check')` 之后用 `START_TEST` / `tcase_add_test` 注册用例，运行期由
check fork 出子进程执行每个用例并通过临时文件回传结果。

OHOS 设备的 `/tmp` 是 **root 属主只读目录**（实测 `drwxr-xr-x root root`），因此 check
在运行期创建通信临时文件会失败：

```text
.../check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so
$ echo $?
2
```

## 机理（与 E547 一致的部分）

libcheck 0.15.x 的 `open_tmp_file()`（`src/check_msg.c`）按

```text
TEMP  →  P_tmpdir  →  TMPDIR  →  "."
```

的顺序探测候选临时目录，其中 `P_tmpdir` 在 musl 下固定展开为 `"/tmp"`。由于
`P_tmpdir` 排在 `TMPDIR` **之前**，在 `/tmp` 只读的设备上只设置 `TMPDIR` 不会改变结果
——这与"环境变量覆盖内建默认值"的常规直觉相反。

## 与既有条目的差异（本条新增的可复用结论）

E547 草稿（`knowledge/drafts/DRAFT-E547-ohos-libcheck-p-tmpdir-tmpdir-priority.{kv,md}`，
cjose 任务）对该机理的描述是正确的，但其推荐方案是「把 libcheck 作为仅测试使用的私有依赖
**从源码自建**，并在 `src/check_msg.c` 中把 `getenv("TMPDIR")` 探测提前到 `P_tmpdir`
之前」；E002（`/tmp` 只读时设置 `TMPDIR`）对本场景不生效。

本条的实测反证：`TEMP` 本来就是探测顺序中的**第一项**，因此

1. 不需要自建 libcheck，**ohpcd 发行包 `check/0.15.2` 的原始二进制即可工作**；
2. 修复动作只是一条环境变量：运行测试前 `export TEMP=<任务可写目录>`；
3. 单独设置 `TMPDIR` 仍失败（与 E547 的机理描述一致）。

### 反证命令与实测输出（设备实测，2026-09-11）

探针（链接 ohpcd 发行包 check/0.15.2，未做任何源码修改）：

```sh
CHK=/storage/Users/currentUser/.conan2/p/check78d1451f90356/p   # conan cache path check/0.15.2:<pkgid>
clang -I"$CHK/include" -L"$CHK/lib" -o check_probe check_probe.c -lcheck -lpthread -lm -lrt
```

```text
# ① 默认环境（/tmp 只读）
$ LD_LIBRARY_PATH="$CHK/lib" ./check_probe
.../check01f6875eb3aa2/b/src/check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so
rc=2

# ② 只设 TMPDIR（E547 描述的现象，仍然失败）
$ TMPDIR=/storage/Users/currentUser/tmp/libtsm-4.3.0/tmpw LD_LIBRARY_PATH="$CHK/lib" ./check_probe
.../check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so
rc=2

# ③ 设 TEMP（最高优先候选，生效）
$ TEMP=/storage/Users/currentUser/tmp/libtsm-4.3.0/tmpw LD_LIBRARY_PATH="$CHK/lib" ./check_probe
Running suite(s): probe
100%: Checks: 1, Failures: 0, Errors: 0
probe: ran=1 failed=0
rc=0
```

`strings "$CHK/lib/libcheck.so"` 亦可交叉印证候选顺序：

```text
mkstemp
/tmp          <- P_tmpdir
TEMP
Unable to create temporary file for communication; may not have permissions to do so
```

### 全量套件复现（libtsm 4.3.0 上游 7 套件 / 37 用例）

```sh
cd <src>/libtsm-4.3.0
meson setup build-native            # dependency('check') 由 pkg-config 解析到发行包
meson compile -C build-native
TEMP="$TASK_DIR/tmpw" meson test -C build-native --print-errorlogs
```

```text
1/7 libtsm:htable    OK   2/7 libtsm:screen  OK   3/7 libtsm:symbol OK
4/7 libtsm:valgrind  OK   5/7 libtsm:selection OK 6/7 libtsm:vte_mouse OK
7/7 libtsm:vte       OK
Ok: 7   Fail: 0
```

逐套件 `check` 自报用例数：2 + 4 + 12 + 2 + 1 + 7 + 9 = **37**（全部 `Failures: 0,
Errors: 0`）。不设 `TEMP` 时每个套件 rc=2、`0%: Checks: 0`，无任何用例被执行。

## 复现前提（避免自身绕行手段污染结论）

- 反证 ③ 之前必须先清除其它注入：本机探针直接使用 `LD_LIBRARY_PATH` + 环境变量命令
  形式，不使用任何 `HOME`/`TMPDIR` 沙箱包装；`.gitconfig` 层面的 `GIT_CONFIG_*` 注入与
  本模式无关。
- `TEMP` 目录必须真实可写（任务私有 `$TASK_DIR` 下新建目录，`/tmp` 与 `/data/local/tmp`
  都可能不可写）。

## 适用与不适用

- 适用：任何以 check 为上游测试框架、在设备（`/tmp` 只读）上运行测试的包；包括把
  check 作为 `test_package`/测试依赖的 conan 场景（可用 `env=` 传入 `TEMP`）。
- 不适用：测试命令自身会清空环境（`env -i`）或由被测程序再 `fork` 出干净环境、
  无法把 `TEMP` 传进去时 —— 退回私有自建 + 调整探测顺序的路径（见 kv 的 fallback_*）。

## 关键词

libcheck, check, check_msg.c:317, Unable to create temporary file,
open_tmp_file, mkstemp, TEMP, TMPDIR, P_tmpdir, /tmp read-only, exit status 2,
meson test, 测试框架迁移

---

*与 E002 的区分：E002 是 `/tmp` 只读导致构建工具临时文件失败的通用条目，推荐的
`TMPDIR=<可写>` 对 check 运行期无效（P_tmpdir 优先级更高），必须用 `TEMP`。*
*与 E011 的区分：E011 是 umask 077 目录权限位（HMDFS UID 映射）问题，发生在
configure/config.status 阶段；本条发生在测试运行阶段。*
