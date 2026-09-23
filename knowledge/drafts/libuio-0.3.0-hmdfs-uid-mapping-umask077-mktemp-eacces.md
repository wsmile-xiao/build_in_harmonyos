# libuio 0.3.0 — HMDFS uid 映射 + umask 077：mktemp 目录 EACCES（draft）

**Category**: ohos | build-system | libc | filesystem · **Severity**: 3 · **Tool**: config.status/configure/mktemp/make

## 症状

configure 全部检查通过，最后 `creating ./config.status` 之后立即死：

```text
./config.status: line 817: ./confkmHkNj/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

mksh 下报 `./config.status[982]: ...`。`bash -x` 追到首个写入
`echo 'BEGIN {' >"$ac_tmp/subs1.awk"`。

## 根因

1. .conan2 所在 HMDFS 挂载点上，进程建的目录属主显示为**数字 uid**（20001006），
   与进程身份名不匹配 → DAC 落到组（file_manager）：**组位有 rw 才可写**。
2. autoconf AS_TMPDIR 用 `(umask 077 && mktemp -d "./confXXXXXX")`；GNU mktemp
   显式 chmod(0700) 在 HMDFS 映射成 `drwx--S---`（组位空）→ 建文件一律 EACCES。
3. 迷惑性双料：`mkdir`（无显式 chmod）即使 umask 077 也得到 `drwxrws--x`（组位有
   rw）**可写**；home/tmp 挂载点（属主名匹配）连 `drwx--S---` 都可写——
   跨目录、跨挂载点结论互相矛盾，极易误判为"shell 兼容性"或"随机故障"。

## 判别口诀

`ls -ld conf*`：`drwx--S---` + 属主是数字 uid → 命中本条。

## 对策

build 目录写 `bash_env.sh`（mktemp 包装：内部 `umask 022` 调真 mktemp +
`export -f`），配三个环境变量：

```text
BASH_ENV=<build>/bash_env.sh          # 所有非交互 bash 自动 source（函数全链路生效）
CONFIG_SHELL=<hnp bash 绝对路径>       # config.status/Makefile 的 SHELL 钉到 bash（mksh 不读 BASH_ENV）
PWD=<build_folder>                    # 见 getcwd 姊妹条目
```

注意：往 os.environ 塞 `BASH_FUNC_mktemp%%` 实测被 conan 的 conanbuild 包装
丢失——BASH_ENV 文件才是可靠通道。完整实现：
`archives/l/libuio/0.3.0/conanfile.py` build() OHOS 块。
