#!/bin/bash
# 选择性安装 GNU coreutils - 只安装完全可用的命令
# 
# 用法：
#   cd coreutils-9.10-work
#   ./install-selected.sh [PREFIX]
#
# PREFIX 默认为 $HOME/usr/local

set -e

PREFIX=${1:-$HOME/usr/local}
SRC_DIR=$(dirname "$0")

# 如果在 work 目录外运行，尝试找到 src 目录
if [ ! -d "$SRC_DIR/src" ]; then
    if [ -d "./src" ]; then
        SRC_DIR="."
    else
        echo "错误：请在 coreutils-9.10-work 目录中运行此脚本"
        exit 1
    fi
fi

echo "========================================"
echo "GNU Coreutils 选择性安装脚本"
echo "========================================"
echo "目标目录: $PREFIX/bin"
echo "源目录: $SRC_DIR/src"
echo ""

# 推荐安装的命令列表（共 64 个）
# ========================================

# 文本处理（19个）- 替代 toybox 功能限制
# 注意：sed 不在 coreutils 中，是独立的 GNU sed 包
TEXT_CMDS="expr sort cut tr uniq comm csplit expand fold join nl paste pr printf ptx tac unexpand fmt od"

# 已修复管道处理（6个）
PIPE_CMDS="head tail wc cat dd split"

# 文件操作（10个）- 不涉及软链接
FILE_CMDS="touch mkdir rmdir mkfifo mknod mktemp tee truncate sync shred"

# 目录/路径操作（4个）
PATH_CMDS="basename dirname pwd pathchk"

# 系统信息（13个）- 注意：uptime 编译失败
SYS_CMDS="date df du id logname nproc uname users who whoami tty stty printenv"

# 其他功能正常（10个）
OTHER_CMDS="echo env sleep seq test true false factor numfmt shuf tsort"

# 进程控制（4个）
PROC_CMDS="nice nohup timeout groups"

# 安装工具（3个）- 注意：install 命名为 ginstall
INSTALL_CMDS="ginstall dircolors stdbuf"

# 其他工具（2个）
TOOL_CMDS="getlimits yes"

# 用户信息（1个）
USER_CMDS="pinky"

# 特权命令（1个）
PRIV_CMDS="chroot"

# 合并所有推荐安装的命令
ALL_INSTALL_CMDS="$TEXT_CMDS $PIPE_CMDS $FILE_CMDS $PATH_CMDS $SYS_CMDS $OTHER_CMDS $PROC_CMDS $INSTALL_CMDS $USER_CMDS $PRIV_CMDS $TOOL_CMDS"

# 不推荐安装的命令（受 SELinux 限制）
SKIP_CMDS="ls rm cp mv stat chmod chown readlink ln link unlink realpath"

# 创建安装目录
mkdir -p "$PREFIX/bin"

# 安装命令
installed=0
skipped=0
not_found=0

echo "正在安装命令..."
echo ""

for cmd in $ALL_INSTALL_CMDS; do
    src_path="$SRC_DIR/src/$cmd"
    if [ -x "$src_path" ]; then
        cp -f "$src_path" "$PREFIX/bin/"
        echo "  ✓ $cmd"
        ((installed++))
    else
        echo "  - $cmd (未找到)"
        ((not_found++))
    fi
done

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo "已安装: $installed 个命令"
echo "未找到: $not_found 个命令"
echo ""

# 提示不安装的命令
echo "以下命令建议使用系统 toybox（软链接相关限制）："
echo ""
for cmd in $SKIP_CMDS; do
    echo "  $cmd → /bin/$cmd"
done
echo ""
echo "建议在 ~/.zshrc 中添加别名："
echo ""
echo '  # 使用 toybox 处理软链接相关操作'
echo '  alias ls="/bin/ls"'
echo '  alias rm="/bin/rm"'
echo '  alias cp="/bin/cp"'
echo '  alias mv="/bin/mv"'
echo '  alias stat="/bin/stat"'
echo '  alias chmod="/bin/chmod"'
echo '  alias chown="/bin/chown"'
echo '  alias readlink="/bin/readlink"'
echo '  alias ln="/bin/ln"'
echo '  alias link="/bin/link"'
echo '  alias unlink="/bin/unlink"'
echo '  alias realpath="/bin/realpath"'
echo ""

# 验证安装
echo "验证关键命令..."
echo ""

if [ -x "$PREFIX/bin/expr" ]; then
    # 测试 expr 是否支持复合正则
    if "$PREFIX/bin/expr" "abc" : "a\|b" >/dev/null 2>&1; then
        echo "  ✓ expr 支持复合正则表达式"
    else
        echo "  ? expr 可能有问题"
    fi
fi

if [ -x "$PREFIX/bin/wc" ]; then
    # 测试 wc 管道输出
    if echo "test" | "$PREFIX/bin/wc" -l >/dev/null 2>&1; then
        echo "  ✓ wc 管道输出正常"
    else
        echo "  ? wc 可能有问题"
    fi
fi

if [ -x "$PREFIX/bin/sed" ]; then
    echo "  ✓ sed 已安装"
fi

if [ -x "$PREFIX/bin/sort" ]; then
    echo "  ✓ sort 已安装"
fi

echo ""
echo "========================================"
echo "请将以下内容添加到 PATH："
echo "========================================"
echo ""
echo "  export PATH=\"$PREFIX/bin:\$PATH\""
echo ""
echo "注意：以下工具不在 coreutils 中，如需使用请单独安装："
echo "  diff, patch → diffutils, patch 包"
echo "  find, xargs → findutils 包"
echo "  awk → gawk 包"