# dehydrated-tools-extra 20260506 适配笔记

## 编译环境
- 构建系统: makefile（纯 POSIX shell 脚本包，无编译、无 configure）
- 编译日期: 2026-09-09
- 编译器: 无（不编译任何代码）
- 状态: built

## 编译步骤

1. `conan source`：从官方发布归档
   `https://get.open-infrastructure.net/software/dehydrated-tools-extra/upstream/dehydrated-tools-extra-20260506.tar.xz`
   下载源码（SHA256=b29c06108a9a902d2ecf94578765cb09e1905ccbb15a0b8b63c2a0e52f7f1563，
   与上游 .sha512 及 Kali orig.tar.xz 逐字节一致）。
2. `conan build`：
   - 应用 `patches/0001-ohos-rewrite-bin-sh-shebangs.patch`（shebang 重写）。
   - 真实运行上游官方测试入口 `make test`（bin/* 与 share/hooks/* 共 10 个脚本
     逐一 `sh -n` 语法检查；checkbashisms/shellcheck 在设备上未安装，Makefile
     自身探测缺失即跳过，属上游设计的可选项）。
   - 不运行 `make build`：其唯一作用是用 rst2man（python3-docutils）渲染 man 页，
     设备上没有 rst2man；.rst 文件作为文档随包交付。
3. `conan package`：按上游 install 布局安装——
   - `bin/dehydrated-{cron,hook,nsupdate}` → `bin/`
   - `share/hooks/*`（7 个 hook 脚本）→ `share/dehydrated/hooks/`
   - `share/cron/dehydrated` → `etc/cron.d/dehydrated`
   - `share/logrotate/dehydrated` → `etc/logrotate.d/dehydrated`
   - `LICENSE.txt/CHANGELOG.txt/TODO.txt/VERSION.txt` 与 `share/man/*.rst` → `share/doc/dehydrated-tools-extra/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备镜像无 `/bin/bash`（实存的 `/bin/sh` 等价 mksh）；上游 10 个脚本 shebang 均为 `#!/bin/sh`，解释器随环境浮动、无统一 bash 语义保障 | 上游面向 Debian，发行版保证 /bin/sh 存在 | 补丁 0001 将全部 shebang 重写为实存可用的 `#!/data/service/hnp/bin/bash`（脚本本身是 POSIX sh 语法，bash 可解释），保证解释器可用与 bash 语义 |
| 2 | man 页无法构建 | rst2man（python3-docutils）设备上不存在 | build() 跳过 man 渲染；`share/man/*.rst` 作为文档安装到 share/doc/ |
| 3 | 无法用 --version/--help 冒烟 | 脚本不支持这两个选项；且执行本体有副作用（dehydrated-cron 会真的调 dehydrated 并写 /var/log；dehydrated-hook 依赖 /etc/dehydrated/hook.d 与 run-parts；dehydrated-nsupdate 依赖 dig/nsupdate） | test_package 采用 abcde 式结构化冒烟：存在性 + 可执行位 + shebang 校验 + bash -n 语法检查，不执行脚本本体 |
| 4 | CI L2 门禁会以 `--version`/`--help` 真实执行 bin/ 下脚本 | L2 是 CI 通用冒烟 | 已逐脚本核实副作用安全：dehydrated-hook 对未知参数 fall-through 退出 0；dehydrated-nsupdate 立即报错退出 1；dehydrated-cron 因 dehydrated 未安装经 set -e 快速退出（不会挂起，L2 亦有 15s 超时），均无破坏性。L2 结果为 warn（非阻塞），不影响 CI 通过 |

## 源码修改

- `patches/0001-ohos-rewrite-bin-sh-shebangs.patch`：对
  `bin/dehydrated-cron`、`bin/dehydrated-hook`、`bin/dehydrated-nsupdate` 与
  `share/hooks/*`（7 个）共 10 个文件仅改第 1 行 shebang：
  `#!/bin/sh` → `#!/data/service/hnp/bin/bash`。

## 依赖版本

- 无编译依赖（纯 shell 脚本）。
- 运行时依赖（OHOS 侧边界，如实记录）：本包只是 dehydrated ACME 客户端的周边
  工具，**dehydrated 本体、openssl、curl/wget、dig/nsupdate（bind-dnsutils 或
  knot-dnsutils）、run-parts、cron/logrotate 守护进程均未随本包移植**。在
  OHOS 上完整使用需另行补齐上述运行时依赖；当前包内的脚本可安装、可语法校验，
  但 `dehydrated-cron`/`dehydrated-nsupdate` 的完整功能在设备上尚不可用。

## 验证结果

```bash
# conan create 内（build 阶段，真实运行）：
$ make test
Checking for syntax errors with sh... .......... done.
Checking for bashisms... Note: devscripts not installed, skipping checkbashisms. done.
Checking with shellcheck... Note: shellcheck not installed, skipping shellcheck. done.

# test_package 阶段（真实运行）：
$ /data/service/hnp/bin/bash test_dehydrated_tools_extra.sh <bin_dir> <pkg_root>
dehydrated-tools-extra smoke test: OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/dehydrated-cron | cron 包装器：调 dehydrated --cron 并写日志 |
| bin/dehydrated-hook | hook 分发器：按 HANDLER 参数调 /etc/dehydrated/hook.d 下钩子 |
| bin/dehydrated-nsupdate | DNS hook：以 clean_challenge./deploy_challenge. 前缀符号链接使用 |
| share/dehydrated/hooks/*（7 个） | hook 示例脚本（chrony、extra 证书、hostname、ocsp、清理、权限、服务重载） |
| etc/cron.d/dehydrated、etc/logrotate.d/dehydrated | cron 与日志轮转配置 |
| share/doc/dehydrated-tools-extra/* | LICENSE/CHANGELOG/TODO/VERSION 与 3 个 rst man 页源文件 |

## 注意事项

- 全部脚本已重写 shebang 为 `#!/data/service/hnp/bin/bash`；脚本为 POSIX sh 语法，
  由 bash 解释执行。
- 运行时依赖边界见上文"依赖版本"一节：dehydrated 本体及其工具链（openssl、
  dig/nsupdate 等）未随包移植，完整功能待依赖补齐。
- `.rst` man 页未渲染（rst2man 缺失），如需 man 页可在有 python3-docutils 的
  环境用上游 `make -C share/man` 生成。
---

**编译结束**: 2026-09-09
**最终状态**: built
