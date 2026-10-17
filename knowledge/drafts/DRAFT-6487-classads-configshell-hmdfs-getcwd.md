# draft-classads-1.0.10-configshell-hmdfs-getcwd

## 症状

autotools 包在 conan create 的 configure 阶段输出数百条：

```
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
job-working-directory: error retrieving current directory: getcwd: cannot access parent directories: Invalid argument
...
configure: error: cannot run /data/service/hnp/bin/bash ./config.sub
```

conftest 临时目录操作错乱（`mkdir: cannot create directory 'sub': File exists` 与
`cd: conftest.dir: No such file or directory` 并存）。

## 根因

profile `[buildenv]` 注入 `CONFIG_SHELL=/data/service/hnp/bin/bash`（OHOS 系统
bash）。该 bash 二进制对 HMDFS 挂载目录的 getcwd() 返回 ENOTSUP/EINVAL。autoconf
一旦采用 CONFIG_SHELL 就以它运行 config.guess/config.sub/config.status，全链路
getcwd 失败。**非负载问题**：同目录 SSH 手动 `pwd` 正常、最低负载时同样失败；
conan create 的子进程树稳定复现。

## 修复

conanfile build() 的 run 命令内联覆盖（环境变量就近优先于 profile buildenv）：

```python
self.run(f'cd "{src}" && CONFIG_SHELL=/bin/sh CC={cc} ... ./configure ... && make ...')
```

同时把构建放回源码目录内执行（不传 cwd，由 shell 内部 cd 进入）——conan 缓存的
`p/b/<hash>/b/build-release` 子目录在 HMDFS 上同样触发 getcwd 风暴，浅一层
（`p/b/<hash>/b`）正常。

## 适用范围

- 所有走 profile ohos-aarch64（buildenv 注入 OHOS bash）的 autotools 包；
- 与优化级别、包大小无关。

## 反例/边界

- 同目录 SSH 登录 shell 手动 pwd 正常（差异在 conan 子进程继承的环境与 bash 版本）；
- CMake 包不受影响（不调用 CONFIG_SHELL）。

## 触发实例

classads/1.0.10（2026-09-09），修复后 conan-verify G2 全绿。

补充实例：hamlib/4.7.1（2026-09-28）——同一现象出现在 `clean-verify` 的 **G0**
（不是 `conan create`）：`clean_verify.py` 默认 `config_shell=/data/service/hnp/bin/bash`，
在 `$HOME` 根目录下 getcwd 正常、进入任何**子目录**即失败，于是 configure 第 1445 行
`ac_pwd=\`pwd\`` 报 `working directory cannot be determined`。
处理：`CONFIG_SHELL=/bin/sh python3 scripts/ohc-run.py clean-verify <pkg> <ver>`，
随后 G0 通过（5 补丁应用 + configure/make/install，14 bin / 11 lib）。
说明该默认值对 G0 与 G2（conan 子进程）都有影响，凡走 autotools configure 的门禁
都应显式内联 `CONFIG_SHELL=/bin/sh`。

## 相关

DRAFT-E551（CONFIG_SHELL=bash 老 ltmain.sh 丢引号转义）——解法手段相同
（内联 CONFIG_SHELL=/bin/sh），根因不同（转义丢失 vs getcwd 系统调用失败）。
