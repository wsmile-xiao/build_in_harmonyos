# mlmmj 1.6.0 — OHOS 适配笔记

## 来源与版本

- 上游发布包：`mlmmj-1.6.0.tar.gz`（顶层目录 `mlmmj-1.6.0/`）
- 下载地址：`https://codeberg.org/mlmmj/mlmmj/releases/download/RELEASE_1.6.0/mlmmj-1.6.0.tar.gz`
  （上游发布已迁至 Codeberg；`mlmmj.org/releases/` 旧路径 404。设备端实下 sha256 与下方锁定值逐字节一致）
- SHA256：`2161e0b2d2d8cc54625f7439dec3a9ef54b2343a50c34fe22ba5098b9ec04633`
- 构建系统：autotools（configure 由 autoconf 2.72 生成；build-aux 内为 2018 年版 config.guess/config.sub）
- 许可证：MIT

## 构建配置

| configure 开关 | 原因 |
|---|---|
| `--disable-tests` | tests 默认开启且 configure 阶段硬依赖 ATF；包构建不需要，上游测试在设备上单独执行 |
| `--disable-dependency-tracking` | 常规 |
| `--disable-silent-rules` | 保留完整编译日志 |

不使用 `--build=/--host=/--target=`（native 编译纪律）：三元组识别由 0001/0002 补丁下的 config.guess/config.sub 自检完成。

## 补丁清单与落点

| 补丁 | 文件 | 内容 | 依据 |
|---|---|---|---|
| 0001 | `build-aux/config.guess` | re-header 检测 `__OHOS__` → `LIBC=ohos`；case 头后新增 `*:HarmonyOS:*:*` 分支映射机器名并输出 `<cpu>-unknown-linux-ohos` | 上游不识别 HarmonyOS uname |
| 0002 | `build-aux/config.sub` | `maybe_os` 列表加 `linux-ohos*`；`android-linux)` 后新增 `ohos-linux)` 分支（`os=linux-ohos`）；主白名单加 `linux-ohos* \| ohos*` | 否则 `linux-ohos` 被 `linux*)` sed 变换吞成 `linux-gnu-ohos`；裸 `ohos` 直接 "system not recognized" |
| 0003 | `configure` | 两处 `umask 077` → `022`（confXXXXXX 临时目录） | E011：HMDFS UID 映射使 0700 目录对当前进程不可写 |
| 0004 | `src/Makefile.am` + `src/Makefile.in` | install-exec-hook 的 `ln -f -s` 别名（`mlmmj-recieve`、`mlmmj-make-ml.sh`）改为 `cp -f` | E050：HMDFS 全盘禁 symlink（EPERM）。先改 .am 再改 .in，防止 make 触发生成规则覆盖 |
| 0005 | `src/mlmmj-make-ml.in` | `TEXTLIBDIR` 优先解析脚本自身所在目录的 `../share/mlmmj/text.skel`，找不到回退编译期默认值 | conan 包不可重定位：`@textlibdir@` 被 config.status 替换为构建期绝对路径 |
| 0006 | `src/strgen.c` | `decode_qp()` 在 `fclose(bufp)` 前补 `fflush(bufp)`（一处，无守卫） | OHOS libc 的 `fclose()` 丢弃未 flush 的 open_memstream 缓冲，解码后的头部单词返回空串 |
| 0007 | `src/mlmmj.c` | `open_listdir()`：uid 与 st_uid 不一致时回退 `access(listdir, W_OK)` 可写性判定——可写即放行，不可写仍按原样报错；HMDFS 对所有路径 stat() 均报存储属主（20001006）而进程运行在每会话 uid 下，单凭 uid 比较会拒绝合法列表属主。属主/root 保持原短路行为 | HMDFS 属主映射；纯 POSIX 判定（无平台条件编译），仅放宽「非属主但可写」 |
| 0008 | `include/xstring.h` | `xstring_free()` / `xstring_get()` 两处在 `fclose(str->fp)` 前各补 `fflush(str->fp)` | 同 0006；未 flush 时 OHOS libc 的 `fclose()` 还会使流处于退出期崩溃的状态 |

补丁为 unified diff（a/ b/ 前缀，strip 1）；0006/0008 为同源 libc 语义问题的两处修复，0007 为 POSIX 可写性回退（无平台条件编译），补丁间文件不相交，按序应用无耦合。

## 本地验收（Windows 主机）

制作脚本 `craft_mlmmj.py` 对原始 tarball 做行级编辑生成 8 个补丁，并完成：

- **config.sub 矩阵 4/4 通过**：`aarch64-unknown-linux-ohos`、`arm-unknown-linux-ohos`、`x86_64-unknown-linux-ohos`、`aarch64-unknown-linux-gnu`（回归）
- **形态探针**：`aarch64-linux-ohos` / `aarch64-ohos-linux` / `aarch64-unknown-ohos` 均归一化为 `aarch64-unknown-linux-ohos`
- **config.guess 假 uname 测试**：模拟 `uname -m aarch64 / -s HarmonyOS` → `aarch64-unknown-linux-ohos`（rc=0）

## 真机验证（2026-10-04，HarmonyOS PC aarch64）

### 门禁与构建

- **conan create 干净构建** + 消费者 test_package：**16/16 通过**（TEST SUMMARY: 16 passed, 0 failed；含 11 命令安装性、make-ml 建列表 17 个文本骨架、三种订阅分区、去重、别名副本、版本横幅）
- **ohc-run.py conan-verify**：G0–G4 + L2/L4/L5 全 PASS，**Verdict: PASS（2026-10-04T15:50:18）**。G0 命中知识库 E490（autotools 脚本执行位）并在 build() 内按方案恢复；L2/L4/L5 无 cache 路径跳过

### 上游 ATF 全量真机执行

- 口径：Kyuafile 声明 **9 个测试程序** = 8 个 atf-sh 脚本（合计 111 条用例条目）+ 1 个 atf-c 程序 `tests/mlmmj`（92 条注册用例）= **203 条**，全部实跑、无跳过、无裁剪。`tests/fakesmtpd` 为 shell 套件使用的辅助程序，不在 Kyuafile 之列。
- 上游自身在 `mlmmj-receive` 的 `tests_init` 中声明了两遍 `simple`（原样保留）；两遍各自在独立工作目录运行，均通过。
- 设备无 kyua（上游 `make check` 的 check-local 直接调用 kyua）：用直跑驱动逐用例执行（驱动与日志不入仓库）。要点：
  - 逐用例独立工作目录（含重名用例的按次计数目录，复刻 kyua 的隔离语义）；
  - 每例 `timeout 300`；用例间清扫 fakesmtpd / 遗留子进程（**OHOS procfs 陷阱**：读取正在退出的 `/proc/<pid>/cmdline` 会自旋不回 EOF，清扫读取须加 `timeout` 上限）；
  - 运行期垫片（上游测试文件零改动）：8 个 shell 套件经 PATH 垫片把 `ln -s` 映射为 `cp -Rf`（E050）；atf-c 程序直接调用 `symlink(2)`，用 LD_PRELOAD 的 `symlink()` 拦截器把失败的调用材料化为递归拷贝（悬空目标保持与平台一致的失败）。
- 结果：**通过 197/203，失败 6，0 跳过、0 裁剪**（atf-sh 106/111；atf-c 91/92）。逐套件：mlmmj-list 6/6、mlmmj-send 1/1、mlmmj-process 8/8、functional-tests 1/1、mlmmj-bounce 9/11、mlmmj-sub 23/23、mlmmj-maintd 30/33、mlmmj-receive 28/28（simple 两条目均过）、tests/mlmmj 91/92。
- 失败 6 条均为平台语义差异（HMDFS 权限位不生效 / 悬空符号链接不可构造 / 沙箱路径 errno 差异），非适配缺陷：

  | 用例 | 预期 | 设备实际 | 根因 |
  |------|------|----------|------|
  | mlmmj-bounce basics_5 | 对悬空符号链接 bounce 文件拒绝（exit 1） | exit 0 | HMDFS 无法创建符号链接，"bounce 文件是悬空符号链接"这一前置形态不可构造 |
  | mlmmj-bounce basics_6 | `chmod 444` 后写入失败（exit 1） | exit 0 | HMDFS 权限位不生效，"不可写"前置条件不可构造 |
  | mlmmj-maintd basics_2 | 日志含 "Permission denied" | 无该行 | `chmod -w` 不生效 |
  | mlmmj-maintd digests_4 | 日志含 "Permission denied" | 无该行 | `chmod -w` 不生效 |
  | mlmmj-maintd unsub_bouncers_6 | 日志含 "Permission denied" | 无该行 | `chmod -r` 不生效 |
  | mlmmj exec_or_die | `/usr/bin/nopenope` 报 "No such file or directory" | "Permission denied" | 应用沙箱对 /usr 路径不可检索（stat/ls 均 EACCES），execve 失败 errno 为 EACCES 而非 ENOENT |

### 重跑步骤（可直接复用）

```sh
# 1. 完整构建 + test_package（消费者 E2E 16 例）
cd <repo>
CONAN_HOME=/storage/Users/currentUser/.conan2 conan create archives/m/mlmmj/1.6.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable

# 2. 官方八门禁
CONAN_HOME=/storage/Users/currentUser/.conan2 python3 ohc-run.py conan-verify mlmmj 1.6.0

# 3. 上游 ATF 测试（kyua 缺失 → 直跑）
#    PATH 前置垫片目录（ln→cp -Rf）、atf-sh 目录；atf-sh tests/<8 脚本>；
#    LD_PRELOAD=symlinkshim.so 直接执行 tests/mlmmj（atf-c）
#    实测驱动：$HOME/mlmmj-atf/run-tests-v64.sh（设备侧，不入仓库）
```

## 可重定位说明（0005 实测点）

消费者 E2E 用打包的 `mlmmj-make-ml -f answerfile` 在任意工作目录建列表并逐例校验：

- `text/` 应部署 17 个骨架文件（若 0005 未生效，TEXTLIBDIR 指向构建期路径，只会得到 "WARNING: List text language 'en' not found"）

## 已知说明

- 上游 `make check` 的 `check-local` 直接调用 kyua；设备无 kyua，8 个 atf-sh 脚本用 atf-sh 直跑，atf-c 程序 `tests/mlmmj` 直接执行（辅助程序 `tests/fakesmtpd` 由 shell 套件自行拉起）。上游测试文件零修改。
- 测试脚本准备的 `ln -s listtexts/en ...`（约 31 处）在 HMDFS 上失败（E050），设备运行用 PATH 垫片（`ln -s` → `cp -Rf`）；atf-c 程序的直接 `symlink(2)` 用 LD_PRELOAD 拦截器材料化。两类垫片都只在设备运行的命令环境里生效，不入包、不改测试源码。
- 设备平台语义（导致上述 6 条用例无法满足前置条件）：
  - HMDFS 上 `chmod` 的权限位不生效（写/读仍可进行）；
  - HMDFS 无法创建符号链接，悬空符号链接这一攻击形态无法构造；
  - 应用沙箱下 `/usr`、`/bin` 等系统路径对进程不可检索（stat/ls 均 EACCES），execve 不存在的路径返回 EACCES 而非 ENOENT；
  - `id` 工具不可用（bad uid xxx），用例里 `test $(id -u) = 0` 的 root 短路不生效（不影响非 root 用例路径）。
- lld 宿主运行时（libxml2.so.16）由 ohos-aarch64 profile 的 `[buildenv] LD_LIBRARY_PATH` 统一承担，配方内不需要 E429 式探测门。
- mlmmj 工具使用裸 getopt；`--version`/`--help` 会被逐字符解析，但 `h` 字母命中 `print_help`（`exit(EXIT_SUCCESS)`），平台 L2 冒烟门禁可经 `--help` 兜底全部通过。
