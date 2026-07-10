#!/usr/bin/perl
# Smoke test for SQL::Abstract — verifies basic SQL generation
use strict;
use warnings;
use SQL::Abstract;

my $sqla = SQL::Abstract->new;
my ($sql, @bind) = $sqla->where({
    name => 'John',
    age => { '>=' => 18 },
});

# Verify the SQL contains expected parts
die "Test failed: no WHERE clause" unless $sql =~ /WHERE/i;
die "Test failed: no name placeholder" unless $sql =~ /name.*\?/i;
die "Test failed: no age comparison" unless $sql =~ /age.*>=.*\?/i;

# Verify bind values
die "Test failed: wrong bind count" unless scalar(@bind) == 2;

# Test select generation
my ($sel_sql, $sel_bind) = $sqla->select('users', '*', { name => 'Jane' });
die "Test failed: no SELECT" unless $sel_sql =~ /SELECT/i;
die "Test failed: no FROM" unless $sel_sql =~ /FROM/i;
die "Test failed: no WHERE" unless $sel_sql =~ /WHERE/i;

# Test insert generation
my ($ins_sql, $ins_bind) = $sqla->insert('users', { name => 'Bob', age => 25 });
die "Test failed: no INSERT" unless $ins_sql =~ /INSERT/i;
die "Test failed: no VALUES" unless $ins_sql =~ /VALUES/i;

# Test update generation
my ($upd_sql, $upd_bind) = $sqla->update('users', { age => 26 }, { name => 'Bob' });
die "Test failed: no UPDATE" unless $upd_sql =~ /UPDATE/i;
die "Test failed: no SET" unless $upd_sql =~ /SET/i;

# Test delete generation
my ($del_sql, $del_bind) = $sqla->delete('users', { name => 'Bob' });
die "Test failed: no DELETE" unless $del_sql =~ /DELETE/i;

# Test complex WHERE with OR
my ($or_sql, @or_bind) = $sqla->where({
    -or => [
        { name => 'Alice' },
        { name => 'Bob' },
    ],
});
die "Test failed: no OR in complex WHERE" unless $or_sql =~ /\bOR\b/i;

print "OK: SQL::Abstract smoke test passed\n";
