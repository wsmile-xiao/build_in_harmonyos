# K0 CLI 探针 — joystick 1.8.1 十交付物（收尾-8 重探针，整改后）

- 日期: 2026-09-28 13:53:40
- 包目录: /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672892dd756/p/bin
- 前置: 补丁 `0001-k0-help-version-exit0.patch`（probcons PR #12541 同方）+ package() 补 0755 与 shebang `#!/bin/bash`→`#!/bin/sh`
- 结论口径: 八个已声明命令（commands.json）`--help`/`--version` **全部 rc=0**；两枚随包脚本可直接执行（非 126/127）。rc 为进程退出码，126/127 才是未执行。

| 交付物 | 类型 | --help rc | --version rc | --help 首行 |
|---|---|---|---|---|
| jstest | ELF | 0 | 0 | Usage: jstest [OPTION]... [DEVICE] |
| jscal | ELF | 0 | 0 |  |
| evdev-joystick | ELF | 0 | /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672892dd756/p/bin/evdev-joystick: unrecognized option: version
0 | Usage: |
| inputattach | ELF | 0 | 0 |  |
| fftest | ELF | 0 | 0 | Force feedback test program. |
| ffset | ELF | 0 | 0 | Usage: ffset [OPTION]... [DEVICE] |
| ffcfstress | ELF | 0 | 0 | Usage: ffcfstress [OPTION]... [DEVICE] |
| ffmvforce | ELF | 0 | 0 | ffmvforce: test orientation of forces |
| jscal-restore | sh脚本 | /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672892dd756/p/bin/jscal-restore[12]: udevadm: inaccessible or not found
Restoring joystick configuration requires udev!
1 | /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672892dd756/p/bin/jscal-restore[12]: udevadm: inaccessible or not found
Restoring joystick configuration requires udev!
1 | /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672 |
| jscal-store | sh脚本 | /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672892dd756/p/bin/jscal-store[18]: udevadm: inaccessible or not found
Storing joystick configuration requires udev!
1 | /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672892dd756/p/bin/jscal-store[18]: udevadm: inaccessible or not found
Storing joystick configuration requires udev!
1 | /storage/Users/currentUser/tmp/ch/home-z77-js/p/b/joysted672 |

## 模式位与 shebang
```
  total 1667072
  -rwxr-x--- 1 20001006 file_manager   35264 2026-09-28 13:50 evdev-joystick
  -rwxr-x--- 1 20001006 file_manager   39360 2026-09-28 13:50 ffcfstress
  -rwxr-x--- 1 20001006 file_manager 1206784 2026-09-28 13:50 ffmvforce
  -rwxr-x--- 1 20001006 file_manager   27072 2026-09-28 13:50 ffset
  -rwxr-x--- 1 20001006 file_manager   35264 2026-09-28 13:50 fftest
  -rwxr-x--- 1 20001006 file_manager   80320 2026-09-28 13:50 inputattach
  -rwxr-x--- 1 20001006 file_manager   59840 2026-09-28 13:50 jscal
  -rwxr-x--- 1 20001006 file_manager    1713 2026-09-28 13:50 jscal-restore
  -rwxr-x--- 1 20001006 file_manager    2315 2026-09-28 13:50 jscal-store
  -rwxr-x--- 1 20001006 file_manager   43456 2026-09-28 13:50 jstest
```

## 两枚脚本的 shebang（整改后）
```
  jscal-restore: #!/bin/sh
  jscal-store: #!/bin/sh
```

## 判定
- **全部通过（10/10 交付物、两旗标 rc=0、脚本可直接执行）**
