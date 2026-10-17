# DRAFT-cpdb-libs-1.2.0-config-status-hmdfs-mktemp-wrapper-path-prepend — HMDFS 上 config.status 临时目录权限失败：PATH-prepend 可执行 mktemp wrapper 方案

- 触发事件：cpdb-libs 1.2.0 返工，远端 CI PR #12677 conan build+test 失败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-cpdb-libs-1.2.0-config-status-hmdfs-mktemp-wrapper-path-prepend

## 现象

远端 CI `zsh ci/conan/build_and_test.sh` 的 conan create 阶段，L0/KC/JC 全过、
4 个补丁应用成功、autogen.sh 与 configure 检查全过之后，config.status 失败：

```
./config.status: line 800: ./confGfDnfg/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

L1_RESULT=fail，pass rate 0%。本地 R01 `conan create` 却通过（exit=0，
12/12 PASS）——两者环境差异是取证关键。

## 根因

autoconf 生成文件（configure/config.status）的 AS_TMPDIR 逻辑：

```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` ||
  (umask 077 && mkdir "$tmp")
```

依赖 0700 权限语义。HMDFS 上：

1. toybox `mktemp -d` 显式 chmod(0700) 被映射为 `drwx--S---`（setgid、
   组位为空）——即使 `mkdir -p` 对照（umask 077）产 `drwxrws--x` 组位可写；
2. OHOS 进程 uid 映射异常（CI bad uid 20020101）非目录属主，DAC 落到组位，
   但组位为空 → 目录内建任何文件 EACCES；
3. config.status 第一写 `echo 'BEGIN {' >"$ac_tmp/subs1.awk"` 即失败。

本地 R01 通过是因为本地进程 uid 恰好映射为目录属主（20001006），DAC 走
属主位。

## 修复

配方 `generate()`（OHOS 分支）创建 `build_folder/mktemp-wrapper/mktemp`
可执行 sh 脚本并 prepend 到 PATH（scoped 到 conanbuild 环境，不落盘系统
目录、不提交，R6）：

```sh
#!/bin/sh
mode=""
for a in "$@"; do
  case "$a" in
    -d) mode="-d" ;;
  esac
done
if [ "$mode" != "-d" ]; then
  exec /usr/bin/mktemp "$@"
fi
dir=""
for a in "$@"; do
  case "$a" in
    -d) ;;
    *)  dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="./tmp.XXXXXX"
base=$(dirname "$dir")
pat=$(basename "$dir")
out=""
i=0
while [ -z "$out" ] && [ $i -lt 100 ]; do
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$RANDOM/")"
  if (umask 077 && mkdir -p "$cand" 2>/dev/null); then out="$cand"; fi
  i=$((i+1))
done
[ -n "$out" ] && { echo "$out"; exit 0; }
exit 1
```

关键点：

- `-d` 用 `mkdir -p`（HMDFS 产 drwxrws--x 组位可写）模拟并打印路径；
- 非 `-d` 调用（mktemp 的其它用法）原样转发真 mktemp，退出码保留；
- wrapper 仅存在于 build_folder，随 conan build 生命周期，无系统痕迹；
- 与 DRAFT-libuio（BASH_ENV bash 函数 `export -f mktemp` +
  CONFIG_SHELL=bash）的区别：本方案走可执行脚本 + PATH 查找，任意
  shell（mksh/sh 的 config.status）同样生效，不依赖 bash 专属特性。

## 验证

- 修复后 `conan create . --build=cpdb-libs/*`（ohos-aarch64 profile）：
  exit=0，0 处 Permission denied，`config.status: creating Makefile/pc`
  全部成功，消费者测试 12/12 PASS（`repro-r02-fixed-conan-create.log`）；
- W3 `build_and_test.sh`：RC=0，JC_RESULT=pass，L0/L1/L4/L5 pass
  （`repro-r02-finish.log`）；
- finish：finish_success（step5b/step8 为与 R01 相同的框架级非阻塞警告）。

日志：`/storage/Users/currentUser/tmp/cpdb-libs-r01-logs/`（forensics-r02.log、
repro-r02-fixed-conan-create.log、repro-r02-finish.log）。

## 适用边界

- 适用：HMDFS/受限文件系统上 autoconf（configure/config.status）构建报
  `conf*/subs1.awk: Permission denied` / `could not setup config files
  machinery`；判据 `ls -ld conf*` 见 `drwx--S---`（组位空）即命中；
- 适用：任意 shell 驱动的 config.status（mksh/sh），无需 CONFIG_SHELL 钉扎；
- 反例/注意：上游脚本以绝对路径调用 mktemp 时 PATH 方案不生效（改
  BASH_ENV/libuio 方案）；组位被安全策略连锁封锁的挂载需换 tmpfs
  （E060）或换构建目录（E110）。

## 关联

- similar_to：
  - DRAFT-libuio-0.3.0-hmdfs-uid-mapping-umask077-mktemp-eacces（同错误
    签名、同根因家族；方案=BASH_ENV bash 函数 + CONFIG_SHELL 钉扎）；
  - E011（edit-umask-in-configure）/ E052（modify_tmpdir）/ E060
    （use-tmpfs-workaround）/ E110（use_alternate_build_dir）/ E112/E114
    （bypass-mktemp，sed 改 ac_tmp）/ E118（patch-script）/ E125
    （relocate-build-dir）——同 HMDFS config.status 家族，方案各异；
- caused_by：autoconf AS_TMPDIR `(umask 077 && mktemp -d)` + HMDFS 权限
  语义 + 构建进程 uid 映射；
- 先行实证：archives/a/accel-config/4.1.9 同款 `_create_mktemp_wrapper`
  已在仓内实践。