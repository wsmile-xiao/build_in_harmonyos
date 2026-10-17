#!/bin/sh
# test.sh — ondir 0.2.4 功能性测试（7 项断言式检查）
# 用法: sh test.sh <ondir-binary> <writable-workdir>
# ondir 语义：`ondir <old> [new]` 按 ~/.ondirrc 的 enter/leave 正则规则
# 把待 eval 的 shell 命令打印到 stdout（shell 钩子 eval，ondir 自身不执行）。
# HOME 隔离到 workdir（HMFS /etc 只读，不写全局配置；/tmp 只读，调用方
# 须以 TMPDIR=<workdir> 运行本脚本——here-doc 临时文件走 TMPDIR）。
set -e

BIN="$1"
WORK="$2"
fail=0

check() {
    # check <描述> <输出文件> <grep 模式>
    if grep -q "$3" "$2"; then
        echo "ok - $1"
    else
        echo "FAIL - $1"
        fail=1
    fi
}

mkdir -p "$WORK/home"
cat > "$WORK/home/.ondirrc" <<'EOF'
enter /odtest/sub
	echo entered $ONDIRWD
leave /odtest/sub
	echo left $ONDIRWD
enter /odtest/rx/(.*)
	echo got:$1
enter ~/odtest/tilde
	echo tilde:$ONDIRWD
EOF

export HOME="$WORK/home"

# 1) -V 版本输出
"$BIN" -V > "$WORK/v.out"
check "-V 输出版本号 0.2.4" "$WORK/v.out" "0.2.4"

# 2) enter 规则触发 + $ONDIRWD 展开为被遍历路径
"$BIN" / /odtest/sub > "$WORK/enter.out"
check "enter 规则输出且 \$ONDIRWD=/odtest/sub" "$WORK/enter.out" "echo entered /odtest/sub"

# 3) leave 规则触发（从 /odtest/sub 离开到 /）
"$BIN" /odtest/sub / > "$WORK/leave.out"
check "leave 规则输出且 \$ONDIRWD=/odtest/sub" "$WORK/leave.out" "echo left /odtest/sub"

# 4) POSIX 正则捕获组 $1 展开
"$BIN" / /odtest/rx/xyz > "$WORK/rx.out"
check "捕获组 \$1 展开为 xyz" "$WORK/rx.out" "got:xyz"

# 5) 无匹配规则的目录遍历无输出
"$BIN" / /other/place > "$WORK/none.out"
if [ -s "$WORK/none.out" ]; then
    echo "FAIL - 无匹配规则时应无输出"
    fail=1
else
    echo "ok - 无匹配规则时无输出"
fi

# 6) 鸿蒙特有：规则路径里的 `~` 必须经 getenv("HOME") 展开为 $HOME。
#    conf.c:95 对 `tok[0]=='~'` 的分支做 home+tok+1 拼接（home 取自
#    getenv("HOME")）；HMFS 的 /etc 只读且无 /etc/ondirrc，$HOME/.ondirrc
#    是唯一可用的配置通道，因此该展开分支在 OHOS 上是实际生效路径而非
#    可选特性。上游无测试套件，此判据为适配新增。
"$BIN" / "$HOME/odtest/tilde" > "$WORK/tilde.out"
check "鸿蒙特有：规则 \`~/...\` 经 \$HOME 展开为绝对路径" \
      "$WORK/tilde.out" "echo tilde:$HOME/odtest/tilde"

# 7) 鸿蒙特有：省略第二个参数时 ondir 以 getcwd() 补全目的目录并正常退出。
#    该分支依赖 OHOS bionic 的 getcwd() 在 CI 工作目录下可用；上游无断言，
#    若 getcwd 失败会走 usage 错误路径而非退出码 0。
set +e
( cd "$WORK/home" && "$BIN" / ) > "$WORK/cwd.out" 2> "$WORK/cwd.err"
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
    echo "ok - 鸿蒙特有：单参数形式经 getcwd() 补全 dst 后退出码 0"
else
    echo "FAIL - 鸿蒙特有：单参数形式应经 getcwd() 正常退出（rc=$rc）"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "ondir test_package: FAILED"
    exit 1
fi
echo "ondir test_package: all 7 checks passed"
