# DRAFT-dynamite-0.1.1-libtool-1.5.22-echo-undefined.md

# libtool 1.5.22 生成脚本在 OHOS bash 环境缺 `$echo` 定义与 `$tool_oldlib` 空引用

## 问题

2005 年代（libtool 1.5.22）Autotools 项目在 OHOS 环境构建时，`configure` 生成的
`libtool` 脚本内部大量使用小写 `$echo` 变量（479 处）却从未定义；同时
`old_archive_cmds` / `old_postinstall_cmds` 引用未赋值的 `$tool_oldlib`。
实际报错：

- `../libtool: line 926: X--tag=CC: command not found`
- `libtool: ignoring unknown tag : command not found`
- `ranlib`（空参数）打印 usage 后失败
- `cannot infer operation mode from ... clang`

## 根因

1. 生成 `libtool` 的 `ltmain.sh` 模板是 2005 年 libtool 1.5.22（
   `VERSION=1.5.22`、`TIMESTAMP "(1.1220.2.365 2005/12/18 22:14:06)"`），
   其变量约定依赖 ksh 风格 `print -r --`（`ECHO="print -r --"`），但 OHOS
   Conan profile 用 `/data/service/hnp/bin/bash` 作为 SHELL，bash 无 `print`
   内建，且脚本从未给 `echo=`（小写）赋值 → `$echo "X$1"` 展开为空后把
   `X--tag=CC` 当命令执行。
2. `old_archive_cmds="\$AR \$AR_FLAGS \$oldlib\$oldobjs~\$RANLIB \$tool_oldlib"`
   中的 `$tool_oldlib` 在 1.5.22 中未赋值 → `ranlib` 无参数运行失败。

## 方案

对生成的 `libtool` 脚本做两处最小修复（或对 `generated/libtool` 预生成副本
在 `autotools.configure()` 之后覆盖回 build 树所有实例）：

```text
# An echo program that protects backslashes.
ECHO="print -r --"
echo='echo'                                  # 新增：小写 echo 定义为 bash 内建

sharedlib_from_linklib_cmd="echo"            # 由 "print -r --" 改为 bash 内建

old_postinstall_cmds="chmod 644 \$oldlib~\$RANLIB \$oldlib"   # $tool_oldlib → $oldlib
old_archive_cmds="\$AR \$AR_FLAGS \$oldlib\$oldobjs~\$RANLIB \$oldlib"  # 同上
```

因 `make` 可能在 `build-release` 子树运行、且 `config.status --recheck` 会二次
生成 libtool，覆盖必须：

- 在 `autotools.configure()` 之后、`autotools.make()` 之前执行；
- 对 build/source 两棵树 `os.walk` 所有 `libtool` 实例逐一覆盖并校验
  （`tool_oldlib` 存在才覆盖，避免重复写）；
- 同步 touch `config.status` / `Makefile`，否则 `configure` 新于
  `config.status` 会触发 `--recheck` 二次 configure，重新生成的 libtool 覆盖修复。

## 验证

- `conan-verify dynamite 0.1.1` G2（conan create 干净构建）通过：
  `ar cr .libs/libdynamite.a` + `ranlib` 成功、`make -j1` 完成全部目标；
- `make check` 通过（上游无测试目标）；
- test_package 消费方运行通过。

## 适用边界

- 上游源码包使用 2005 年前后 Autotools（`configure.ac.in` + `bootstrap` 生成
  configure，`AC_PROG_LIBTOOL` 老宏）；
- 构建 SHELL 为 bash（OHOS Conan profile `/data/service/hnp/bin/bash`）或任何
  无 `print` 内建的 shell；
- 需要预生成 configure / 跳过 host bootstrap 的配方（generated/ 模式）。

## 反例 / 限制

- 现代 libtool（2.4.x）无此问题（`$ECHO` 大写变量已正确定义），勿套用；
- 只改源码 `ltmain.sh` 无效：`configure` 生成 libtool 时 `echo=` 定义不在
  ltmain.sh 主体，需改生成产物或预生成副本；
- 修复必须避开 `config.status --recheck` 重生成（见方案），否则被覆盖。

## 查重差异

与 E236/E411/E522（`.la` 归档移动 / 脏 `.lo` / libtool archive 无效）不同：
本条目是生成脚本**变量定义缺失**（`$echo`、`$tool_oldlib`），报错在 `make`
阶段参数解析，非归档/打包产物问题。与 E228（libtool wrapper 执行权限）不同：
本条目无 Permission denied，是命令展开失败。
