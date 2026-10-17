# DRAFT-device-shadow-ci-repo-source-pruned: 真机隔离 job 的 `--repo-source` 可能是裁剪仓库——runner 以 127 秒败,`zsh: can't open input file: ci/conan/build_and_test.sh`

> 来源:eta 1.0.1 真机 shadow CI(2026-09-27)。知识库只记了「设备无 git → 用已有 repo 作 `--repo-source`」,没记「这个 repo 本身可能是裁剪版」。

## 症状

`sh ~/ohos-users/codex/<job>/run-conan-heavy.sh` 的 ssh 客户端**无任何输出**返回 127。设备端 run 目录日志显示:

```text
logs/command.txt : 'zsh' 'ci/conan/build_and_test.sh' 'archives/e/eta/1.0.1'
logs/stderr.log  : zsh: can't open input file: ci/conan/build_and_test.sh
logs/exit-code.txt: 127
```

锁正常拿到(wait_seconds=0~10)、run 目录正常创建——失败发生在**进入 CI 脚本之前**。

## 根因

`ohos-prepare-isolated-conan-job.sh --repo-source <已有 job 的 repo>` 只是把那个目录**原样复制**为新 job 的仓库。如果选中的源 job 恰好是「裁剪仓库」(实测某个近期 job 的 repo 只剩根目录几个 md + `archives/`,没有 `ci/`、`scripts/` 等),新 job 就继承了缺陷:runner 入口 `zsh ci/conan/build_and_test.sh <包路径>` 找不到脚本 → 127。**127 + 空 stdout = 失败在 runner 外层**,与包本身无关。

## 预检(创建 job 后、首跑前,一条命令)

```sh
ls "$HOME/ohos-users/codex/<job>/repo/build_in_harmonyos/ci/conan/build_and_test.sh" || echo "裁剪仓库,先补齐再跑"
```

## 修复(设备端 cp 补齐,无需重建 job / 重传包)

找一个**已知跑通过**的 job 的完整 repo 作源:

```sh
SRC="$HOME/ohos-users/codex/<完整repo的job>/repo/build_in_harmonyos"
DST="$HOME/ohos-users/codex/<job>/repo/build_in_harmonyos"
for d in ci config docs knowledge references scripts templates; do
  cp -r "$SRC/$d" "$DST/$d"
done
# 只补顶层目录,不要动 archives/<自己的包>;然后原样重跑 run-conan-heavy.sh
```

补齐后同一 job 直接重跑即可,包目录与 conan-home 均不受影响。

## 附带两个真机运维小坑(同会话实测)

1. **nohup 挂住 ssh 通道**:`nohup sh monitor.sh >/dev/null 2>&1 &` 重定向了 stdout/stderr 但没关 stdin,ssh 客户端会一直挂着不返回。加 `</dev/null`。
2. **pkill 后 ssh 退出码 255 不代表失败**:`pkill -f monitor.sh` 杀掉设备端进程时,ssh 客户端可能返回 255 且无输出;先用新连接 `ps -ef | grep "[m]onitor.sh"` 确认,不要盲目重杀。

## 复用面

所有走「真机隔离 job + `--repo-source`」的 shadow CI 会话;设备排队资源宝贵,127 空跑一轮就是浪费一个排队位。
