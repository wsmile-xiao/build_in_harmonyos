package Dpkg::Control::Info;
use strict;
use warnings;

sub new {
    my ($class, $file) = @_;
    my $self = { file => $file };
    bless $self, $class;
    $self->_parse();
    return $self;
}

sub _parse {
    my ($self) = @_;
    my $file = $self->{file};
    my @stanzas;
    if (open my $fh, '<', $file) {
        my %cur;
        my $field = '';
        while (my $line = <$fh>) {
            $line =~ s/\r?\n$//;
            # Debian control comment (see Dh_Lib.pm): skip '# ...' at column 0
            # so a commented-out substvar does not truncate Built-Using.
            next if $line =~ /^#/;
            if ($line eq '') {
                push @stanzas, {%cur} if %cur;
                %cur = ();
                $field = '';
                next;
            }
            if ($line =~ /^\s+(.*)$/ && $field ne '') {
                $cur{$field} .= "\n$1";
            } elsif ($line =~ /^([^:]+):\s*(.*)$/) {
                $field = $1;
                $cur{$field} = $2;
            }
        }
        push @stanzas, {%cur} if %cur;
        close $fh;
    }
    $self->{stanzas} = \@stanzas;
    return;
}

sub get_source {
    my ($self) = @_;
    return $self->{stanzas}[0] // {};
}

sub get_pkg_by_name {
    my ($self, $name) = @_;
    for my $s (@{$self->{stanzas}}) {
        next unless defined $s->{Package};
        if ($s->{Package} eq $name) {
            return $s;
        }
    }
    return {};
}

1;
