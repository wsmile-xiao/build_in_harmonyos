# DRAFT-ohos-no-bin-bash-upstream-test-shebang：OHOS PC 无 /bin/bash，上游 #!/bin/bash 测试需按 shebang 选解释器

> Contributor: ohc-worker | Status: Draft | Updated: 2026-10-02
> 来源：kamailio-lua 6.0.6 适配（上游 kamailio `test/unit` 全量执行环节）
> 对应：`knowledge/drafts/DRAFT-ohos-no-bin-bash-upstream-test-shebang.kv`

## 现象

在 OHOS PC 源码树内逐个执行上游测试脚本（`cd test/unit && ./N.sh`）时，大量用例以
退出码 **127** 结束，输出为空或仅：

```console
$ ./37.sh ; echo $?
timeout: exec ./37.sh: No such file or directory
127
```

而同目录下 `#!/bin/sh` 的用例可以正常执行（返回 0 或真实业务退出码）。
本案例中 49 个用例里 36 个受此影响，若不处理会得到 36 个"假失败"，污染上游测试统计。

## 根因

OHOS PC 的根文件系统**不提供 `/bin/bash`**，只有 `/bin/sh`；bash 实体位于工具链目录
`/data/service/hnp/bin/bash`（GNU bash 5.3.0）：

```console
$ ls -l /bin/bash
ls: /bin/bash: No such file or directory
$ ls -l /bin/sh
-rwxr-xr-x 1 root shell 306288 ... /bin/sh
$ /data/service/hnp/bin/bash --version | head -1
GNU bash, version 5.3.0(1)-release (aarch64-unknown-linux-gnu)
```

shebang 是绝对路径，执行 `./N.sh` 时内核直接 exec `/bin/bash` → ENOENT → shell 将
"命令不可执行"上报为 exit 127（错误文案近似"permission denied / not found"，易被误判为
权限或文件缺失问题）。

## 推荐方案

执行上游测试前读取首行 shebang，**按 shebang 显式选择解释器**，不改上游测试文件：

```bash
for f in *.sh; do
    if head -1 "$f" | grep -q bash; then
        interp=/data/service/hnp/bin/bash
    else
        interp=/bin/sh
    fi
    timeout 120 "$interp" "./$f"; echo "$f exit=$?"
done
```

配套：统计时把"退出码 + 上游自身的 `not found, not run` 守卫输出"一起记录，才能把
SKIP（上游主动跳过）与 FAIL（真实失败）分开。

## 备选方案

统一用 `/bin/sh` 执行全部用例——仅当用例语法兼容 POSIX sh 时成立；bash 专有语法
（`[[ ]]`、`&>` 等）会失败，且改变上游执行语义，仅作最后手段。

## 反面策略

- 在 `/bin/bash` 建软链或把 bash 复制到 `/bin`：`/` 为只读系统分区，且污染共享环境，
  CI worker 重建后失效——禁止。
