#!/bin/sh
# quicklisp 运行期环境辅助脚本（OpenHarmony PC）
#
# 背景
# ----
# quicklisp.lisp 把 Quicklisp client 的默认安装目录定义为
#     (merge-pathnames "quicklisp/" (user-homedir-pathname))   ; quicklisp.lisp:1571
# 即它依赖 Common Lisp 实现能解析出用户家目录（通常来自 HOME 环境变量）。
#
# OpenHarmony PC 的默认用户目录是 /storage/Users/currentUser，但以沙箱 / 服务方式
# 拉起的进程不一定带 HOME —— 此时 (user-homedir-pathname) 的结果未定义，quicklisp
# 会把 client 装到一个不可预期的位置。
#
# 本脚本把 client 安装目录固定下来并在 HOME 缺失时回退到 OHOS 默认用户目录：
#
#   QUICKLISP_HOME       Quicklisp client 安装目录（默认 ${HOME}/quicklisp）
#   QUICKLISP_BOOTSTRAP  包内 quicklisp.lisp 绝对路径；由 Conan runenv 提供
#                        （package_info -> runenv_info.define_path），此处仅透传导出，
#                        未提供时不臆造路径
#
# 用法
# ----
#   . "<pkg>/share/quicklisp/quicklisp-ohos-env.sh"
#   然后在 Common Lisp 中：
#     (load (uiop:getenv "QUICKLISP_BOOTSTRAP"))
#     (quicklisp-quickstart:install :path (uiop:getenv "QUICKLISP_HOME"))

# HOME 缺失（OHOS 沙箱）时的默认用户目录
QUICKLISP_OHOS_DEFAULT_HOME="${QUICKLISP_OHOS_DEFAULT_HOME:-/storage/Users/currentUser}"

: "${QUICKLISP_HOME:=${HOME:-${QUICKLISP_OHOS_DEFAULT_HOME}}/quicklisp}"
export QUICKLISP_HOME

if [ -n "${QUICKLISP_BOOTSTRAP:-}" ]; then
    export QUICKLISP_BOOTSTRAP
fi
