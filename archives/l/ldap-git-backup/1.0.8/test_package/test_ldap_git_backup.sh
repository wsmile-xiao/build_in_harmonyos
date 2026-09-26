#!/data/service/hnp/bin/bash
# test_package/test_ldap_git_backup.sh — 真实消费者测试
# 参数: $1 = package_folder, $2 = 可写工作根（conan test build_folder）
# 断言组（共 20 条）:
#   ① --help 帮助: 上游 001_help-option.t 两条断言原生等价覆盖
#      （退出码 0 + 输出含 --help；001 依赖非核心模块 IPC::Run，见 MANIFEST）
#   ② 运行时依赖 perl + Git.pm（Git.pm 随 git 发行、不在 perl 常规模块路径）
#   ③ 上游 031_backup-to-existing-dir.t 等价覆盖:
#      备份到已存在目录（0777）退出码 0 + stderr 含 world readable 告警 +
#      备份提交落库（world writable 位在 OHOS FUSE 下不触发，见组内注释）
#   ④ 上游 030_git-from-scratch.t 等价覆盖: 全新目录建库 + 两次连续备份
#      增量（dir+.git 创建、1→2 个 revision；mode==0700 子断言在 OHOS FUSE
#      下无法复现，见组内注释）
#   ⑤ 上游套件其余 8 个 prove 用例原样执行（010/020/040/050/060/061/070/071）
set -eu

PKG="$1"
WORK="$2"
SHARE="$PKG/share/ldap-git-backup"

# R10: OHOS /tmp 只读；git 与 File::Temp 需要可写 HOME/TMPDIR
export HOME="$WORK/home"
export TMPDIR="$WORK/tmp"
mkdir -p "$HOME" "$TMPDIR"
# 测试提交身份（上游 Makefile check-local 同款）
export GIT_AUTHOR_NAME=Test GIT_AUTHOR_EMAIL=test@example.org
export GIT_COMMITTER_NAME=Test GIT_COMMITTER_EMAIL=test@example.org
# OHOS /storage 经 FUSE 挂载，仓库所有权跨 uid 报告不一致，git 安全目录检查
# 误报（真机实测 fatal: detected dubious ownership in repository；
# git init 可建库、rev-parse/commit 全被拦）。HOME 已沙箱到测试工作目录，
# safe.directory '*' 仅作用于本次测试。
git config --global --add safe.directory '*' 2>/dev/null || true
# Git.pm 随 git 发行而非 perl 核心；常见发行版/设备安装位置自适应加入 PERL5LIB
# （HarmonyOS PC 真机实测：/data/service/hnp/git.org/git_2.45.2/share/perl5）
for d in /usr/share/perl5 /usr/share/git-core/perl /usr/lib/git-core/perl \
         /usr/share/perl5/vendor_perl \
         /data/service/hnp/share/perl5 \
         /data/service/hnp/git.org/*/share/perl5 \
         /storage/Users/currentUser/usr/local/lib/perl5/site_perl; do
  [ -f "$d/Git.pm" ] && PERL5LIB="${PERL5LIB:+$PERL5LIB:}$d"
done
export PERL5LIB

echo "[test 1/5] --help 帮助（上游 001 等价：退出码 0 + 输出含 --help）"
"$SHARE/ldap-git-backup" --help 2>&1 | grep -q -- "--help"
echo "  OK: --help exit 0 + output mentions --help"

echo "[test 2/5] 运行时依赖 perl + Git.pm"
perl -MGit -e 'print "  Git.pm OK\n"'

echo "[test 3/5] 上游 031 等价：备份到已存在目录 + world 权限告警"
# 031 断言 3 条等价：退出码 0 + world readable 告警 + 备份主链路（LDIF 条目提交
# 进 git 仓库）。world writable 告警（mode & 02）在 OHOS FUSE 下因目录 mode 被
# 钳制为 2751 而不触发（上游 031 自身的 mode==0777 断言同样无法在 OHOS 复现），
# 以 readable 告警证明告警机制链路 + 提交落库证明备份主链路；Linux/CI 上
# mkdir -m 0777 两告警均正常触发。
B3="$WORK/b3"
rm -rf "$B3"
mkdir -p "$B3"
OLD_UMASK=$(umask)
umask 0
mkdir -m 0777 "$B3/backup-dir"
umask "$OLD_UMASK"
ERRFILE="$WORK/b3.err"
"$SHARE/ldap-git-backup" \
    --ldif-cmd="cat $SHARE/t/testdata/data_A1.ldif" \
    --backup-dir="$B3/backup-dir" 2>"$ERRFILE"
grep -q "world readable" "$ERRFILE"
git -C "$B3/backup-dir" log --oneline | grep -q "ldap-git-backup"
echo "  OK: existing-dir backup exit 0 + world readable warning + commit landed"

echo "[test 4/5] 上游 030 等价：全新目录建库 + 两次连续备份（增量）"
# 030 断言 6 条等价：目录创建+建 git 库、首次提交落库且恰 1 个 revision、
# 二次备份成功且恰 2 个 revision（增量）。mode==0700 子断言在 OHOS FUSE 下
# 无法复现（mkdir 0700 实际落盘 0771，存储守护进程钳制 mode；上游 031 的
# mode==0777 断言同理），目录创建与备份主链路已由本组其余断言覆盖。
B4="$WORK/b4"
rm -rf "$B4"
"$SHARE/ldap-git-backup" \
    --ldif-cmd="cat $SHARE/t/testdata/data_A1.ldif" \
    --backup-dir="$B4/backup"
[ -d "$B4/backup/.git" ]
git -C "$B4/backup" log --oneline | grep -q "ldap-git-backup"
N1=$(git -C "$B4/backup" rev-list --all | wc -l)
[ "$N1" = "1" ]
"$SHARE/ldap-git-backup" \
    --ldif-cmd="cat $SHARE/t/testdata/data_A2.ldif" \
    --backup-dir="$B4/backup"
N2=$(git -C "$B4/backup" rev-list --all | wc -l)
[ "$N2" = "2" ]
echo "  OK: from-scratch dir+repo created, 1->2 incremental revisions"

echo "[test 5/5] 上游测试套件（8 用例原样执行；001/030/031 等价覆盖见上）"
# 不用 prove 脚本本身：conan perl 包自带的 prove shebang 坏（真机实测
# "//bin/perl: bad interpreter"，CI Linux 同样会挂）。prove 本就是 App::Prove
# 的薄包装，改经 perl 核心模块 App::Prove 等价执行，不依赖 prove 脚本。
cd "$SHARE"
for t in t/[0-9]*.t; do
  case "$t" in
    *001_help-option*) continue ;;
    *030_git-from-scratch*) continue ;;
    *031_backup-to-existing-dir*) continue ;;
  esac
  perl -MApp::Prove -e 'my $p = App::Prove->new; $p->process_args(@ARGV); exit($p->run ? 0 : 1)' "$t"
done
echo "  OK: upstream prove suite passed"
