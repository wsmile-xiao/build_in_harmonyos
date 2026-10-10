#!/usr/bin/perl
# patch-autotools-ohos.pl — 一键为 autotools 项目打 HarmonyOS 补丁
#
# 用法: perl patch-autotools-ohos.pl <config.guess> <config.sub>
# 基于: autotools-patterns.md #2-#3
#
# 铁律: 禁止用 --build/--host 绕过 (autotools-patterns.md #0)
#
# 判定一律以「执行 helper」为准，不以全文 grep 为准。旧版步骤 2.3 用
# /linux-ohos/ 全文匹配判"已补丁"，会被步骤 2.1 自己写入的 basic_os=linux-ohos
# 抢先满足，kernel-OS 校验列表因此永不修补；自检又用同一条过宽正则，于是
# 报"成功"退出 0 把失败推迟到 ./configure（知识库 E268/E122）。

use strict;
use warnings;

my $cg = $ARGV[0] or die "Usage: $0 <config.guess> <config.sub>\n";
my $cs = $ARGV[1] or die "Usage: $0 <config.guess> <config.sub>\n";
-e $cg or die "Not found: $cg\n";
-e $cs or die "Not found: $cs\n";

# The triplet this recipe must get past config.sub, i.e. what config.guess has
# to report on HarmonyOS and what config.sub has to accept.
my $TARGET = 'aarch64-unknown-linux-ohos';

sub read_file {
    my ($f) = @_;
    open my $h, '<', $f or die "Cannot read $f: $!\n";
    local $/; my $c = <$h>; close $h;
    return $c;
}

sub write_file {
    my ($f, $c) = @_;
    open my $h, '>', $f or die "Cannot write $f: $!\n";
    print $h $c;
    close $h;
}

# Run a GNU config helper without a shell (list-form exec, no word splitting).
# Returns (exit_code, output). 127 + empty output means the helper could not be
# executed at all (no 'sh' on this build host), which callers must treat as
# "probe unavailable", never as pass or fail.
sub run_helper {
    my ($script, @args) = @_;
    my $pid = open my $fh, '-|';
    die "fork failed: $!\n" unless defined $pid;
    if ($pid == 0) {
        open STDERR, '>&', STDOUT or exit 127;
        exec 'sh', $script, @args or exit 127;
    }
    local $/; my $out = <$fh>;
    close $fh;
    return ($? >> 8, defined $out ? $out : '');
}

# config.sub accepts the target triplet only if it echoes it back verbatim.
sub sub_accepts {
    my ($script) = @_;
    my ($rc, $out) = run_helper($script, $TARGET);
    return (undef, "sh unavailable") if $rc == 127;
    $out =~ s/\s+\z//;
    return (1, $out) if $rc == 0 && $out eq $TARGET;
    return (0, "rc=$rc: " . ($out =~ s/\n/ | /gr));
}

# ====== 1. config.guess ======
print "Patching config.guess...\n";
my $gc = read_file($cg);
my $cg_changed = 0;

# 1.1 Insert __OHOS__ after the __ANDROID__ LIBC detection
#     Guard on the inserted effect (LIBC=ohos), not on the macro name, which
#     also appears in unrelated text.
unless ($gc =~ /LIBC=ohos/) {
    # Find '#if defined(__ANDROID__)' followed by 'LIBC=android' on next line
    # Use regex for flexibility with whitespace variations
    if ($gc =~ s{(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)}
                    {$1\n#elif defined(__OHOS__)\n    LIBC=ohos}m) {
        print "  [ok] Added __OHOS__ LIBC detection\n";
        $cg_changed++;
    } else {
        warn "  [warn] Could not find __ANDROID__/LIBC=android in config.guess\n";
    }
} else {
    print "  [skip] __OHOS__ LIBC detection already present\n";
}

# 1.2 Insert HarmonyOS case block before NetBSD
#     Guard on the case label itself (*:HarmonyOS:*:*)), i.e. on the list
#     member form, not on the bare word "HarmonyOS".
unless ($gc =~ /\*\s*:\s*HarmonyOS\s*:\s*\*\s*:\s*\*/) {
    my $block =
        "    *:HarmonyOS:*:*)\n" .
        "\tcase \"\$UNAME_MACHINE\" in\n" .
        "\t    aarch64|arm64) MACHINE=aarch64 ;;\n" .
        "\t    armv7*|armv8*) MACHINE=arm ;;\n" .
        "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n" .
        "\t    i?86)         MACHINE=i686 ;;\n" .
        "\t    *)            MACHINE=\"\$UNAME_MACHINE\" ;;\n" .
        "\tesac\n" .
        "\techo \${MACHINE}-unknown-linux-ohos\n" .
        "\texit 0\n" .
        "\t;;\n\n";

    # Match the NetBSD line that starts the NetBSD case in the main switch
    if ($gc =~ s/(^[ \t]+\*\:NetBSD\:\*\:\*\)[ \t]*\n)/$block$1/m) {
        print "  [ok] Added HarmonyOS system identification\n";
        $cg_changed++;
    } else {
        warn "  [warn] Could not find NetBSD insertion point in config.guess\n";
    }
} else {
    print "  [skip] HarmonyOS case block already present\n";
}

write_file($cg, $gc) if $cg_changed;

# ====== 2. config.sub ======
print "\nPatching config.sub...\n";
my $sc = read_file($cs);
my $changes = 0;

# 2.0 Ask config.sub itself first. Modern GNU config (>= 2023) carries both an
#     `ohos*` OS pattern and a `linux-ohos*-` kernel-OS entry, so nothing has to
#     be rewritten — and rewriting it would only add dead case alternatives.
my ($accepted, $why) = sub_accepts($cs);
if (defined $accepted && $accepted) {
    print "  [skip] config.sub accepts $TARGET (verified by execution)\n";
} else {
    if (defined $accepted) {
        print "  [info] config.sub rejects $TARGET ($why) - patching\n";
    } else {
        warn "  [warn] $why for the pre-patch probe; falling back to static checks\n";
    }

    # 2.1 Add ohos-linux triplet after android-linux
    unless ($sc =~ /^\s*ohos-linux\)\s*$/m) {
        # Match the android-linux block (tabs for indentation)
        if ($sc =~ s{^(\s*android-linux\)\s*\n)((\s*)basic_machine=\$field1-unknown\s*\n)((\s*)basic_os=linux-android\s*\n)(\s*;;\s*\n)}
                        {$1$2$4$6\tohos-linux)\n$3basic_machine=\$field1-unknown\n$5basic_os=linux-ohos\n$6}m) {
            print "  [ok] Added ohos-linux triplet\n"; $changes++;
        } else {
            warn "  [warn] Could not find android-linux in config.sub\n";
        }
    } else {
        print "  [skip] ohos-linux triplet already present\n";
    }

    # 2.2 Add ohos* to the OS type list, guarded on that list's own entry form
    if ($sc =~ /^\s*\|\s*ohos\*\s*\\?\s*$/m) {
        print "  [skip] ohos* already in OS list\n";
    } elsif ($sc =~ s{(gnu\*\s*\|\s*android\*)}{$1 | ohos*}) {
        print "  [ok] Added ohos* to OS list\n"; $changes++;
    } else {
        warn "  [warn] Could not find OS type list anchor in config.sub\n";
    }

    # 2.3 Add linux-ohos*- to the kernel-OS validation list. The guard looks at
    #     that list only, so the `basic_os=linux-ohos` written by 2.1 (or shipped
    #     natively) can no longer satisfy it by accident (E268/E122).
    my @l = split /\n/, $sc, -1;
    my ($start) = grep { $l[$_] =~ /^case \$kernel-\$os-\$obj in\b/ } 0 .. $#l;
    if (defined $start) {
        my ($end) = grep { $l[$_] =~ /^\s*;;\s*$/ } $start + 1 .. $#l;
        $end = $#l unless defined $end;
        my @region = @l[ $start + 1 .. $end ];
        if (grep { /linux-ohos\*-/ } @region) {
            print "  [skip] kernel-OS validation list already has linux-ohos*-\n";
        } elsif (my ($idx) = grep { $region[$_] =~ /linux-uclibc\*-/ } 0 .. $#region) {
            $region[$idx] =~ s/(linux-uclibc\*-)/$1 | linux-ohos*-/;
            print "  [ok] Added linux-ohos*- to kernel-OS validation list\n";
            $changes++;
        } elsif (my ($u2) = grep { $region[$_] =~ /linux-uclibc\*/ } 0 .. $#region) {
            $region[$u2] =~ s/(linux-uclibc\*)/$1 | linux-ohos*-/;
            print "  [ok] Added linux-ohos*- to kernel-OS validation list\n";
            $changes++;
        } else {
            warn "  [warn] kernel-OS validation list found but no insertion anchor\n";
        }
        splice @l, $start + 1, $end - $start, @region if defined $accepted && !$accepted;
        $sc = join "\n", @l;
    } else {
        warn "  [warn] Could not locate the kernel-OS validation list (case \$kernel-\$os-\$obj)\n";
    }

    write_file($cs, $sc) if $changes;
}

print "\nDone. cg=$cg_changed sub=$changes change(s).\n";

# ====== Verification: execute the helpers, do not just grep them ======
print "\n--- Verification ---\n";
my $fatal = 0;

# config.sub is the hard gate: without it, AC_CANONICAL_HOST aborts configure.
my ($ok_sub, $sub_detail) = sub_accepts($cs);
if (!defined $ok_sub) {
    # No 'sh' here - fall back to the region-scoped static checks.
    my $os_list   = $sc =~ /^\s*\|\s*ohos\*\s*\\?\s*$/m || $sc =~ /gnu\*\s*\|\s*android\*\s*\|\s*ohos\*/;
    my @l         = split /\n/, $sc, -1;
    my ($start)   = grep { $l[$_] =~ /^case \$kernel-\$os-\$obj in\b/ } 0 .. $#l;
    my $klist_ok  = 0;
    if (defined $start) {
        my ($end) = grep { $l[$_] =~ /^\s*;;\s*$/ } $start + 1 .. $#l;
        $end = $#l unless defined $end;
        $klist_ok = scalar grep { /linux-ohos\*-/ } @l[ $start + 1 .. $end ];
    }
    printf "config.sub:  [static fallback] os_list=%d kernel_list=%d\n",
        $os_list ? 1 : 0, $klist_ok ? 1 : 0;
    if (!$klist_ok) {
        print "config.sub:  MISSING linux-ohos*- in kernel-OS validation list\n";
        $fatal++;
    }
} elsif ($ok_sub) {
    print "config.sub:  [ok] accepts $TARGET\n";
} else {
    print "config.sub:  [FAIL] rejects $TARGET -> $sub_detail\n";
    $fatal++;
}

# config.guess: only meaningful to run on a HarmonyOS build host.
my $uname_s = `uname -s 2>/dev/null` || '';
chomp $uname_s;
if ($uname_s =~ /HarmonyOS/i) {
    my ($rcg, $outg) = run_helper($cg);
    $outg =~ s/\s+\z//;
    if ($rcg == 127) {
        warn "config.guess: [warn] sh unavailable, cannot probe (static only)\n";
    } elsif ($outg =~ /^[A-Za-z0-9_.+-]+-unknown-linux-ohos$/) {
        print "config.guess: [ok] detects $outg\n";
    } else {
        print "config.guess: [FAIL] returned '$outg' (rc=$rcg)\n";
        $fatal++;
    }
} else {
    printf "config.guess: [n/a] build host is '%s', detection probe skipped\n",
        $uname_s || 'unknown';
}

if ($fatal) {
    print "\n❌ HarmonyOS helper patch incomplete ($fatal item(s) failed).\n";
    exit 1;
}
print "\n✅ HarmonyOS helpers verified.\n";
exit 0;
