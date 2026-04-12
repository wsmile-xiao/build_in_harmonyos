#!/usr/bin/perl
# patch-autotools-ohos.pl — 一键为 autotools 项目打 HarmonyOS 补丁
#
# 用法: perl patch-autotools-ohos.pl <config.guess> <config.sub>
# 基于: autotools-patterns.md #2-#3
#
# 铁律: 禁止用 --build/--host 绕过 (autotools-patterns.md #0)

use strict;
use warnings;

my $cg = $ARGV[0] or die "Usage: $0 <config.guess> <config.sub>\n";
my $cs = $ARGV[1] or die "Usage: $0 <config.guess> <config.sub>\n";
-e $cg or die "Not found: $cg\n";
-e $cs or die "Not found: $cs\n";

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

# ====== 1. config.guess ======
print "Patching config.guess...\n";
my $gc = read_file($cg);
my $cg_changed = 0;

# 1.1 Insert __OHOS__ after the __ANDROID__ LIBC detection
unless ($gc =~ /__OHOS__/) {
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
    print "  [skip] __OHOS__ already present\n";
}

# 1.2 Insert HarmonyOS case block before NetBSD
unless ($gc =~ /HarmonyOS/) {
    my $block =
        "    *:HarmonyOS:*:*)\n" .
        "\tcase \"\$UNAME_MACHINE\" in\n" .
        "\t    aarch64|arm64) MACHINE=aarch64 ;;\n" .
        "\t    armv7*|armv8*) MACHINE=arm ;;\n" .
        "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n" .
        "\t    i?86)         MACHINE=i686 ;;\n" .
        "\t    *)            MACHINE=\"\$UNAME_MACHINE\" ;;\n" .
        "\tesac\n" .
        "\tGUESS=\${MACHINE}-unknown-linux-ohos\n" .
        "\t;;\n\n";

    # Match the NetBSD line that starts the NetBSD case in the main switch
    if ($gc =~ s/(^[ \t]+\*\:NetBSD\:\*\:\*\)[ \t]*\n)/$block$1/m) {
        print "  [ok] Added HarmonyOS system identification\n";
        $cg_changed++;
    } else {
        warn "  [warn] Could not find NetBSD insertion point in config.guess\n";
    }
} else {
    print "  [skip] HarmonyOS block already present\n";
}

write_file($cg, $gc) if $cg_changed;

# ====== 2. config.sub ======
print "\nPatching config.sub...\n";
my $sc = read_file($cs);
my $changes = 0;

# 2.1 Add ohos-linux triplet after android-linux
unless ($sc =~ /ohos-linux/) {
    # Match the android-linux block (tabs for indentation)
    if ($sc =~ s{^(\s*android-linux\)\s*\n)(\s*basic_machine=\$field1-unknown\s*\n)(\s*basic_os=linux-android\s*\n)(\s*;;\s*\n)}
                    {$1$2$3$4\tohos-linux)\n${2}basic_machine=\$field1-unknown\n${3}basic_os=linux-ohos\n${4}}m) {
        print "  [ok] Added ohos-linux triplet\n"; $changes++;
    } else {
        warn "  [warn] Could not find android-linux in config.sub\n";
    }
} else {
    print "  [skip] ohos-linux already present\n";
}

# 2.2 Add ohos* to OS type list
# Only check the gnu* | android* line for ohos*
unless ($sc =~ /gnu\*\s*\|\s*android\*\s*\|\s*ohos\*/) {
    if ($sc =~ s{(gnu\*\s*\|\s*android\*)}{$1 | ohos*}) {
        print "  [ok] Added ohos* to OS list\n"; $changes++;
    }
} else {
    print "  [skip] ohos* already in OS list\n";
}

# 2.3 Add linux-ohos to kernel-OS validation list
unless ($sc =~ /linux-ohos/) {
    # Two known variants of the uclibc entry:
    #   linux-uclibc*- )   (xz 5.6.2's config.sub)
    #   linux-uclibc* )    (older versions)
    if ($sc =~ s{(linux-uclibc\*[/-]?\s*)\)}{$1| linux-ohos*)}) {
        print "  [ok] Added linux-ohos to kernel list\n"; $changes++;
    } else {
        warn "  [warn] Could not find linux-uclibc pattern in config.sub\n";
    }
} else {
    print "  [skip] linux-ohos already present\n";
}

write_file($cs, $sc) if $changes;

print "\nDone. cg=$cg_changed sub=$changes change(s).\n";

# ====== Verification (grep-based, avoids execution issues on HarmonyOS) ======
print "\n--- Verification ---\n";
my $ok = 0;
$ok++ if $gc =~ /__OHOS__/;
$ok++ if $gc =~ /HarmonyOS/;
$ok++ if $sc =~ /ohos-linux/;
$ok++ if $sc =~ /android\*\s*\|\s*ohos\*/;  # ohos* in OS list
$ok++ if $sc =~ /linux-ohos/;

printf "config.guess: __OHOS__=%d HarmonyOS=%d\n",
    ($gc =~ /__OHOS__/ ? 1 : 0), ($gc =~ /HarmonyOS/ ? 1 : 0);
printf "config.sub:  ohos-linux=%d ohos*=%d linux-ohos=%d\n",
    ($sc =~ /ohos-linux/ ? 1 : 0), ($sc =~ /android\*.*ohos\*/ ? 1 : 0), ($sc =~ /linux-ohos/ ? 1 : 0);
print "Score: $ok/5\n";

if ($ok >= 4) {
    print "✅ Patching successful.\n";
    exit 0;
} else {
    print "❌ Some patches may have failed.\n";
    exit 1;
}
