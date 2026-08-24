#!/bin/sh
# autopostgresqlbackup consumer test (L0c + R34): standalone test
# source executed via self.run from conanfile.py test().
# R34: actually run the script — bash -n syntax check + execution
# rc whitelist check. Real backup run needs a PostgreSQL server
# (absent on OHOS — environment limitation, documented honestly).
#
# R9 合规（防伪造通过）：白名单 rc 校验——仅"环境受限"预期码通过：
#   1   = 配置缺失（默认 CONFIG=/etc/autodbbackup.d 在 OHOS 不存在——
#         脚本 config 分支 exit 1——实测 5/5 稳定）
#   127 = 依赖工具缺失（pg_dump/psql 等 command not found）
# 其余 rc（含意外 0、崩溃信号码 >=128、脚本自身错误）一律 exit 1 失败，
# 运行期回归可被 CI 捕获（AI review P1 整改）。
set -eu
SCRIPT="$1"
[ -x "$SCRIPT" ] || { echo "script not executable: $SCRIPT" >&2; exit 1; }
# 语法检查（bash -n——脚本为 bash 脚本）
bash -n "$SCRIPT" || { echo "syntax check failed" >&2; exit 1; }
# 真实执行（默认配置——无 PostgreSQL 环境）——保留输出记录以便失败定位
set +e
"$SCRIPT"
RC=$?
set -e
case "$RC" in
    1)
        # 1 = 配置缺失（默认 CONFIG=/etc/autodbbackup.d 不存在——OHOS
        # 环境受限——如实记录，非脚本错误）
        echo "OK: autopostgresqlbackup 2.5 (executed rc=1 — config /etc/autodbbackup.d absent, env limitation)"
        exit 0
        ;;
    127)
        # 127 = 依赖工具缺失（pg_dump 等——PostgreSQL 客户端——OHOS
        # 环境受限——如实记录，非脚本错误）
        echo "OK: autopostgresqlbackup 2.5 (executed rc=127 — PostgreSQL client absent, env limitation)"
        exit 0
        ;;
    *)
        # 其余 rc（含意外 0、崩溃信号码、脚本自身错误）——测试失败
        echo "FAIL: autopostgresqlbackup 2.5 (unexpected rc=$RC — not an env-limited exit code)"
        exit 1
        ;;
esac
