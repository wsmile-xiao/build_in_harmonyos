# nq

Unix 轻量任务队列工具（上游 [leahneukirchen/nq](https://github.com/leahneukirchen/nq)，CC0 / public domain）。

提供三个命令：
- `nq CMD...` — 把命令入队并在后台顺序执行（flock(2) 保证顺序，输出写入每任务日志文件）
- `nqtail` — 跟踪/展示当前与最近任务输出
- `nqterm` — 在 tmux/screen 新窗口里运行 `nq` + `nqtail`

仅依赖 POSIX.1-2008 + `flock(2)`，无任何第三方库，适合作为 `nohup`/`at` 的轻量替代。

## 版本

- `1.0` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8），见 [1.0/notes.md](1.0/notes.md)
