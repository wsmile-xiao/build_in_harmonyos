# DRAFT-14402：dbus-test-runner 测试 harness 的等价翻译层——多任务并行 shim（libdbusmenu-gtk3 16.04.0）

- **触发实例**：libdbusmenu-gtk3 16.04.0 适配（任务 contrib-13120，2026-09-30 MateBook 真机）
- **错误签名**：`dbus-test-runner: not found` / `make: *** [test-glib-events] Error 127` / wrapper 无 gtester 输出即退出
- **类别**：ohos / testing / dbus / autotools / launchpad
- **严重度**：2（不崩溃，但上游整个 D-Bus 测试子集无法运行；有可行等价方案）

## 症状（真机实测）

`tests/Makefile.am` 的 TESTS 全是生成的 wrapper 脚本，内部调用 **dbus-test-runner**
（Launchpad autobuilder 工具链成员，从未移植、制品仓无）。工具缺失时 automake 并行
harness 下每个测试目标 Error 127，上游 13 个测试一个都跑不了。

## 根因

wrapper 有**两种调用形态**（同一条会话总线上运行）：

1. **单任务 gtester 形态**（6 个 glib 测试）：

```
dbus-test-runner --task gtester --task-name test \
    --parameter --keep-going --parameter ./test-glib-properties
```

2. **多任务形态**（events 两个测试，client/server 共享总线，启动顺序不保证）：

```
dbus-test-runner --max-wait=0 --task ./test-glib-events-client --task-name Client \
                 --task ./test-glib-events-server --task-name Server --ignore-return
```

退出语义（必须如实实现，否则测试结果失真）：

- 默认：**任一**任务非零退出 → 整体失败
- `--ignore-return`：**全部**任务退出即成功（各任务退出码忽略）

隐含前置：测试需要 D-Bus session bus。OHOS 沙箱无 passwd DB，默认 EXTERNAL 认证
起不了总线 → 必须匿名 TCP 会话配置
（**前置组件**：`DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime`，本条目不重复其内容）。

## 翻译层设计（配方 build() 生成两个文件）

**(a) `dbus-test-runner` shim**（POSIX sh，前置到 PATH）：

```sh
#!/bin/sh
tasks=; expect=; sep=; noret=0
for a in "$@"; do
    if [ -n "$expect" ]; then
        case "$expect" in
            task)     tasks="$tasks$sep$a"; sep=$'\n' ;;
            taskname) ;;
            param)    tasks="$tasks $a" ;;
        esac
        expect=; continue
    fi
    case "$a" in
        --task) expect=task ;;
        --task-name) expect=taskname ;;
        --parameter) expect=param ;;
        --ignore-return) noret=1 ;;
        --*) ;;
    esac
done
DBUS_TR_TASKS="$tasks" DBUS_TR_NORET="$noret" \
  exec dbus-run-session --config-file=<构建树>/dbus-session.conf -- sh <shim目录>/run-tasks.sh
```

**(b) `run-tasks.sh`**（并行执行 + 语义保真）：

```sh
#!/bin/sh
rc=0; old=$IFS; IFS=$'\n'
for t in $DBUS_TR_TASKS; do IFS=$old; sh -c "exec $t" & done
IFS=$old
if [ "$DBUS_TR_NORET" = 1 ]; then wait; exit 0; fi
for p in $(jobs -p); do wait $p || rc=1; done
exit $rc
```

**配套四件**（均为已归档模式，组合即可）：

| 件 | 模式出处 |
|---|---|
| dbus/1.14.10.2 tool 包 bin/ 手动入 PATH（tool 型包不经 VirtualRunEnv 暴露） | gtk wrapper 模式 |
| `dbus-run-session --config-file` 匿名 TCP + ANONYMOUS | DRAFT-dbus-1.14.10.1（前置组件） |
| `make check TESTS="<列表>"` 整体加引号（否则 make 把测试名拆成独立目标） | 本任务实证 |
| `LOG_COMPILER = $(SHELL)` + wrapper shebang 改 `/system/bin/sh` | 0004 补丁（直接 shebang 执行被拒） |

## 实测结果（MateBook，OHOS aarch64）

`make check -j1 TESTS="<8 个 glib 测试>"` → gtester XML 全部 `status="0"`，**8/8 PASS**
（6 个走单任务 gtester 形态，test-glib-events / test-glib-events-nogroup 走多任务并行形态）。
消费者测试 14/14（顺带暴露上游 `menuitem.c:929` child_find 循环条件写反，补丁 0005 修复）。

## 语义对照表

| dbus-test-runner | shim 等价实现 |
|---|---|
| `--task <prog>`（可重复） | 任务列表，换行分隔，并行启动 |
| `--task-name <val>` | 不翻译（仅日志用） |
| `--parameter <val>` | 追加到最近一个任务后 |
| `--ignore-return` | 全部任务退出即 exit 0 |
| 默认退出语义 | 逐 job wait，任一非零 → rc=1 |
| `--max-wait` | 未实现（dbus-run-session 在 wait 结束后退出；测试无超时依赖） |

## 适用边界

- 适用于**一切**上游测试 wrapper 调 dbus-test-runner 的包：grep `tests/Makefile.am`
  见 `DBUS_RUNNER` 即命中——libdbusmenu、libindicator、ayatana-indicator-*、
  indicator-* 整族同构。
- 翻译层模式可泛化到其他"轻量 harness 未移植但语义简单"的场景。
- **不适用**：调度/超时/日志聚合语义复杂的 harness 仍需移植本体；参数含空格/换行的
  任务（本 shim 假定构建树路径无空白）。
- 会话总线本身起不来的环境（dbus 工具包缺失）走 fallback：按"无法运行"如实记录，
  不伪造通过。

## 关联

- **前置组件**：`DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime`（匿名 TCP 会话总线运行时）
- 同场景互补：E463（GTK broadway 无显示消费者探针）、E530（X11 库无 server 测试）、
  `DRAFT-clipboard_lite-3.4-headless-x11-consumer`（显示依赖库的确定性崩溃断言）
- 配方实现：`archives/l/libdbusmenu-gtk3/16.04.0/conanfile.py`
  （`_shim_script` / `_run_tasks_helper` / `_write_session_conf`）
- 上游 bug 副产品：`patches/0005-upstream-child-find-loop-fix.patch`
