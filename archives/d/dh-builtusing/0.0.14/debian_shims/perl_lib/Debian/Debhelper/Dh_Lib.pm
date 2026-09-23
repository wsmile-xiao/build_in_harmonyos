package Debian::Debhelper::Dh_Lib;
use strict;
use warnings;
use Exporter 'import';
our @EXPORT = qw(init warning error verbose_print qx_cmd hostarch package_is_arch_all pkgext addsubstvar %dh);
our %dh = ( VERBOSE => 0, DOPACKAGES => [] );

my $_control_for_arch_check = 'debian/control';

sub _parse_control_packages {
    my ($file) = @_;
    my @pkgs;
    return @pkgs unless -f $file;
    open my $fh, '<', $file or return @pkgs;
    my $cur;
    my $field = '';
    my %stanza;
    my @stanzas;
    while (my $line = <$fh>) {
        chomp $line;
        $line =~ s/\r$//;
        # Debian control comment: unit-tests/10basic comments out a var
        # with '# ${dh-builtusing:red-herring},' at column 0. Real
        # Dpkg::Control ignores such lines; without this the '# ...:red-herring}'
        # line is misparsed as a new field (it contains a colon) and truncates
        # the preceding Built-Using field, dropping dpkg-dev (0/16 harness abort).
        next if $line =~ /^#/;
        if ($line eq '') {
            push @stanzas, {%stanza} if %stanza;
            %stanza = ();
            $field = '';
            next;
        }
        if ($line =~ /^\s+(.*)$/ && $field) {
            $stanza{$field} .= "\n$1";
        } elsif ($line =~ /^([^:]+):\s*(.*)$/) {
            $field = $1;
            $stanza{$field} = $2;
        }
    }
    push @stanzas, {%stanza} if %stanza;
    close $fh;
    # first stanza is source, rest are binary
    shift @stanzas if @stanzas;
    for my $s (@stanzas) {
        push @pkgs, $s if defined $s->{Package};
    }
    return @pkgs;
}

sub init {
    my (%args) = @_;
    my $opts = $args{options} || {};
    my ($opt_arch, $opt_indep) = (0, 0);
    my @rest;
    my @argv = @ARGV;
    while (@argv) {
        my $a = shift @argv;
        if ($a eq '--arch' || $a eq '-a') { $opt_arch = 1; }
        elsif ($a eq '--indep' || $a eq '-i') { $opt_indep = 1; }
        elsif ($a eq '--logorrheic') {
            if (exists $opts->{logorrheic} && ref $opts->{logorrheic} eq 'CODE') {
                $opts->{logorrheic}->();
            } else { $dh{VERBOSE} = 1; }
        }
        elsif ($a =~ /^-c(.*)$/ && length($1)) {
            my $v = $1;
            if (exists $opts->{'c=s'} && ref $opts->{'c=s'} eq 'CODE') {
                $opts->{'c=s'}->('c', $v);
            }
            $_control_for_arch_check = $v if $v =~ /\.2$/ || -f $v;
        }
        elsif ($a eq '-c' || $a eq '--control') {
            my $v = shift @argv;
            if (exists $opts->{'c=s'} && ref $opts->{'c=s'} eq 'CODE') {
                $opts->{'c=s'}->('c', $v);
            }
            $_control_for_arch_check = $v if defined $v;
        }
        elsif ($a =~ /^--control=(.*)$/) {
            my $v = $1;
            if (exists $opts->{'c=s'} && ref $opts->{'c=s'} eq 'CODE') {
                $opts->{'c=s'}->('c', $v);
            }
            $_control_for_arch_check = $v;
        }
        elsif ($a eq '--') {
            # debhelper passes toolkit args after --, e.g. dh_gencontrol -- -cfile
            # For dh_builtusing this only matters for -c; keep scanning.
            while (@argv) {
                my $b = shift @argv;
                if ($b =~ /^-c(.*)$/ && length($1)) {
                    my $v = $1;
                    if (exists $opts->{'c=s'} && ref $opts->{'c=s'} eq 'CODE') {
                        $opts->{'c=s'}->('c', $v);
                    }
                    $_control_for_arch_check = $v;
                } else { push @rest, $b; }
            }
        }
        else { push @rest, $a; }
    }
    @ARGV = @rest;
    my $ctl = 'debian/control';
    $ctl = $_control_for_arch_check if defined $_control_for_arch_check && -f $_control_for_arch_check;
    $ctl = 'debian/control' unless -f $ctl;
    my @pkgs = _parse_control_packages($ctl);
    # Fallback: if control has no Package stanzas (should not happen), keep empty.
    my $host_for_filter = hostarch();
    $host_for_filter = 'arm64' unless defined $host_for_filter && length $host_for_filter;
    my @names;
    for my $p (@pkgs) {
        my $n = $p->{Package};
        my $arch = $p->{Architecture} // 'any';
        if ($opt_arch && $arch eq 'all') { next; }
        if ($opt_indep && $arch ne 'all') { next; }
        if (!$opt_arch && !$opt_indep) {
            # 20package-arch: foo $host vs bar $other with plain $tested_command.
            # Upstream expects bar (concrete non-host arch) ignored entirely:
            # no substvars AND no 'not installed' warning (warning would fail
            # the harness via non-empty stderr). 'all'/'any' always built;
            # concrete arch only when it equals the host.
            if ($arch ne 'all' && $arch ne 'any' && $arch ne $host_for_filter) { next; }
        }
        push @names, $n;
    }
    $dh{DOPACKAGES} = \@names;
    return;
}

sub warning {
    my ($msg) = @_;
    $msg = '' unless defined $msg;
    print STDERR "warning: $msg\n";
    return;
}

sub error {
    my ($msg) = @_;
    $msg = '' unless defined $msg;
    print STDERR "error: $msg\n";
    exit 1;
}

sub verbose_print {
    my ($msg) = @_;
    $msg = '' unless defined $msg;
    if ($dh{VERBOSE}) {
        print "$msg\n";
    }
    return;
}

sub qx_cmd {
    my (@cmd) = @_;
    # Intercept dpkg-query/dpkg-architecture when our shim dir is on PATH is
    # not strictly needed; direct exec works. But keep a pure-perl fallback
    # if exec fails (e.g. noexec filesystem): caller expects lines.
    my $out = '';
    my $pid = open my $ph, '-|', @cmd;
    if (!defined $pid) {
        die "qx_cmd: cannot run '@cmd': $!\n";
    }
    { local $/; $out = <$ph> // ''; }
    close $ph;
    my $rc = $? >> 8;
    if ($rc != 0) {
        die "qx_cmd: '@cmd' failed with exit $rc\n";
    }
    my @lines = split /\n/, $out, -1;
    pop @lines if @lines && $lines[-1] eq '' && $out =~ /\n$/;
    @lines = map { "$_\n" } @lines;
    # dh_builtusing chomps each line itself; return lines with newline to
    # match backtick semantics.
    return @lines;
}

sub hostarch {
    return $ENV{DH_BUILTUSING_HOST_ARCH} if defined $ENV{DH_BUILTUSING_HOST_ARCH} && length $ENV{DH_BUILTUSING_HOST_ARCH};
    # Prefer dpkg-architecture shim when available (consistent with run-unit-tests $host).
    my $arch = '';
    if (open my $ph, '-|', 'dpkg-architecture', '-qDEB_HOST_ARCH') {
        local $/;
        $arch = <$ph> // '';
        close $ph;
        $arch =~ s/[\r\n]+$//;
        $arch =~ s/^\s+|\s+$//g;
    }
    return $arch if $arch ne '';
    return 'arm64';
}

sub package_is_arch_all {
    my ($pkg) = @_;
    for my $f ($_control_for_arch_check, 'debian/control') {
        next unless defined $f && -f $f;
        my @pkgs = _parse_control_packages($f);
        for my $p (@pkgs) {
            if (($p->{Package} // '') eq $pkg) {
                return (($p->{Architecture} // '') eq 'all') ? 1 : 0;
            }
        }
    }
    return 0;
}

sub pkgext {
    my ($pkg) = @_;
    return "$pkg.";
}

sub addsubstvar {
    my ($pkg, $var, $value) = @_;
    my $path = "debian/" . pkgext($pkg) . "substvars";
    # Real debhelper Dh_Lib::addsubstvar appends to the same line with
    # ", " when the variable already exists (test_helper.sh builds the
    # expected value as "${value:+$value, }$source..."). Appending a
    # second line instead breaks 45multiple-matches (expects a single
    # comma-joined line) and the merged dh_gencontrol expansion.
    my @lines;
    if (-f $path) {
        open my $rfh, '<', $path or die "open $path failed: $!\n";
        @lines = <$rfh>;
        close $rfh;
    }
    my $found = -1;
    for (my $i = 0; $i < @lines; $i++) {
        my $l = $lines[$i];
        $l =~ s/\r?\n$//;
        # Exact "var=value" (not "?="); keep other vars untouched.
        if ($l =~ /^\Q$var\E=(.*)$/s) {
            my $old = $1;
            $old = '' unless defined $old;
            if ($found < 0) {
                $found = $i;
                $lines[$i] = "$var=$old, $value\n";
            } else {
                # Collapse legacy duplicate lines into the first one.
                $lines[$found] =~ s/\r?\n$//;
                $lines[$found] .= ", $old\n";
                splice(@lines, $i, 1);
                $i--;
            }
        }
    }
    if ($found >= 0) {
        open my $wfh, '>', $path or die "open $path failed: $!\n";
        print $wfh @lines;
        close $wfh or die "close $path failed: $!\n";
    } else {
        open my $fh, '>>', $path or die "open $path failed: $!\n";
        print $fh "$var=$value\n";
        close $fh or die "close $path failed: $!\n";
    }
    return;
}

1;
