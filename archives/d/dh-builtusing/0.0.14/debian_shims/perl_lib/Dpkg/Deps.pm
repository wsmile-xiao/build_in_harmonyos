package Dpkg::Deps;
use strict;
use warnings;
use Exporter 'import';
our @EXPORT = qw(deps_parse);

package Dpkg::Deps::Simple;
use strict;
use warnings;

sub new {
    my ($class, $str) = @_;
    $str = '' unless defined $str;
    $str =~ s/^\s+|\s+$//g;
    my $self = {
        raw => $str,
        package => '',
        relation => undef,
        version => undef,
        arch_qual => undef,
        arches => undef,
        profiles => undef,
    };
    bless $self, $class;
    # Split off [arch] and <profile> trailers.
    my $s = $str;
    if ($s =~ s/\s*\[([^\]]*)\]\s*//) {
        my $a = $1;
        $a =~ s/^\s+|\s+$//g;
        $self->{arches} = [ split /\s+/, $a ] if length $a;
    }
    if ($s =~ s/\s*<([^>]*)>\s*//) {
        my $p = $1;
        $p =~ s/^\s+|\s+$//g;
        $self->{profiles} = [ split /\s+/, $p ] if length $p;
    }
    # Version relation in parens.
    if ($s =~ s/\s*\(\s*([<>=]+)\s*([^\)]+?)\s*\)\s*//) {
        $self->{relation} = $1;
        $self->{version} = $2;
    } elsif ($s =~ /\(.*\)/) {
        # Any other parens content counts as a relation for the
        # dh_builtusing "carries a version relation" guard.
        $self->{relation} = 'unknown';
    }
    $s =~ s/^\s+|\s+$//g;
    # Package with optional :arch-qual.
    if ($s =~ /^([A-Za-z0-9][A-Za-z0-9+.\-]*)(?::([A-Za-z0-9]+))?$/) {
        $self->{package} = $1;
        $self->{arch_qual} = $2;
    } else {
        # Fallback: first token is the package name (e.g. "fake").
        my ($first) = split /\s+/, $s;
        $first = '' unless defined $first;
        $first =~ s/:.*$//;
        $self->{package} = $first;
    }
    return $self;
}

sub get_deps {
    my ($self) = @_;
    return ($self);
}

sub arch_is_concerned {
    my ($self, $host) = @_;
    my $a = $self->{arches};
    return 1 unless defined $a && @$a;
    my (@pos, @neg);
    for my $e (@$a) {
        if ($e =~ /^!(.+)$/) { push @neg, $1; }
        else { push @pos, $e; }
    }
    if (@neg) {
        for my $n (@neg) {
            return 0 if $host eq $n;
        }
        return 1 if !@pos;
        for my $p (@pos) {
            return 1 if $host eq $p;
        }
        return 1;
    } else {
        for my $p (@pos) {
            return 1 if $host eq $p;
        }
        return 0;
    }
}

sub profile_is_concerned {
    my ($self, $active) = @_;
    my $p = $self->{profiles};
    return 1 unless defined $p && @$p;
    $active = [] unless defined $active;
    my %has = map { $_ => 1 } @$active;
    my (@pos, @neg);
    for my $e (@$p) {
        if ($e =~ /^!(.+)$/) { push @neg, $1; }
        else { push @pos, $e; }
    }
    # Debian semantics: <a b> means active if ANY listed profile is active;
    # <!a> means active if NONE of the negated profiles is active.
    if (@neg && !@pos) {
        for my $n (@neg) {
            return 0 if $has{$n};
        }
        return 1;
    }
    if (@pos) {
        for my $x (@pos) {
            # A negated entry inside a positive list disables that entry.
            next if grep { $_ eq $x } @neg && 0;
            return 1 if $has{$x};
        }
        # If list has negations mixed with positives, evaluate negations.
        for my $n (@neg) {
            return 0 if $has{$n};
        }
        return 0;
    }
    return 1;
}

package Dpkg::Deps::OR;
use strict;
use warnings;
sub new {
    my ($class, @alts) = @_;
    bless { alts => \@alts }, $class;
}
sub get_deps {
    my ($self) = @_;
    return @{$self->{alts}};
}

package Dpkg::Deps::AND;
use strict;
use warnings;
sub new {
    my ($class, @items) = @_;
    bless { items => \@items }, $class;
}
sub get_deps {
    my ($self) = @_;
    return @{$self->{items}};
}

package Dpkg::Deps;
use strict;
use warnings;

sub deps_parse {
    my ($str, %opts) = @_;
    $str = '' unless defined $str;
    my @or_items;
    # Top-level comma split (brackets/parens in these tests never contain commas).
    my @comma = split /,/, $str;
    for my $c (@comma) {
        $c =~ s/^\s+|\s+$//g;
        next if $c eq '';
        my @alts = split /\|/, $c;
        my @simples;
        for my $a (@alts) {
            $a =~ s/^\s+|\s+$//g;
            next if $a eq '';
            my $s = Dpkg::Deps::Simple->new($a);
            if ($opts{reduce_restrictions}) {
                my $profiles = $opts{build_profiles} // [];
                # Need host arch for arch filtering; use env-consistent default.
                my $host = $ENV{DH_BUILTUSING_HOST_ARCH} // 'arm64';
                if (exists $ENV{DH_BUILTUSING_HOST_ARCH_DETECTED}) {
                    $host = $ENV{DH_BUILTUSING_HOST_ARCH_DETECTED};
                } else {
                    # Best effort: ask dpkg-architecture shim.
                    if (open my $ph, '-|', 'dpkg-architecture', '-qDEB_HOST_ARCH') {
                        local $/;
                        my $o = <$ph>;
                        close $ph;
                        if (defined $o) {
                            $o =~ s/[\r\n]+$//;
                            $o =~ s/^\s+|\s+$//g;
                            $host = $o if $o ne '';
                        }
                    }
                }
                next unless $s->arch_is_concerned($host);
                next unless $s->profile_is_concerned($profiles);
            }
            push @simples, $s;
        }
        next unless @simples;
        if (@simples == 1) {
            push @or_items, $simples[0];
        } else {
            push @or_items, Dpkg::Deps::OR->new(@simples);
        }
    }
    return Dpkg::Deps::AND->new(@or_items);
}

1;
