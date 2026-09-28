# DRAFT-ohos-pc-local-ci-zsh-heredoc-tmpprefix-exec-domain

## 现象（HarmonyOS PC 开发机，ohc-run.py finish 的 W3 步骤）
- zsh 报 `can't create temp file for here document: read-only file system`
  ——CI 脚本的 heredoc 临时文件落在 /tmp（只读 EROFS）。
- 设备 /usr/bin/zsh 是真 zsh 但 conan/W3 python 域 exec 报 EACCES；
  域内唯一可达的 zsh（pi-agent 自带 5.9）对 heredoc 硬编码 `/tmp/zsh`
  且**无视 TMPDIR**。
- bash 无法替代：CI 脚本使用 zsh glob 限定符 `(N)`，bash 解析 RC=2。

## 根因
- /tmp 只读 + 设备 zsh 的 TMPPREFIX 默认值硬编码（不读 TMPDIR）。
- 沙箱按**进程域**授予 exec：python 域可 exec /system/bin/*（toybox 全套）、
  /data/service/hnp/*、.pi/agent/bin/*；不可 exec /usr/bin/*、$HOME/tmp、
  $HOME/usr/local/bin 下**新创建**的脚本；域内 exec 无转移 → 链式 exec
  （bash → zsh 等）无法借权，植入包装脚本的方案全部不可行。

## 解法（零 CI 脚本改动）
- `$HOME/.zshenv`：
  ```sh
  TMPPREFIX="$HOME/tmp/zsh"; export TMPPREFIX
  ```
  zsh 对非交互 `-c` 调用也无条件 source .zshenv，覆盖硬编码默认。
  toybox applet 经 PATH 首位 /system/bin 正常解析；CI worker 无此文件、
  行为不变。
- junk_check 命中他人包遗留状态文件 = 全仓 full 模式：把本包改动 commit
  到分支（origin/main...HEAD 非空）即走 incremental 模式（等价 CI prdiff）。

## 验证
- kio-kwallet/6.28.0 finish：setup.sh ✅ + build_and_test.sh ✅（W3 全绿），
  heredoc 由 EROFS 报错转为正常落 $HOME/tmp/zsh。

## 关联
- E002（/tmp 只读设 TMPDIR）；DRAFT-kio-kwallet-6.28.0-cmake-version-soversion-symlink-e018
  （同设备 symlink 域隔离）。
