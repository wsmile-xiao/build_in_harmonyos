#!/usr/bin/env perl
# test_sql_abstract_pg.pl — Consumer-side test for SQL::Abstract::Pg
# Called by test_package/conanfile.py via self.run()
#
# Tests: module load, INSERT, SELECT, ON CONFLICT, LIMIT/OFFSET,
#        GROUP BY/HAVING, JOIN, FOR UPDATE, JSON, error handling
use strict;
use warnings;
use SQL::Abstract::Pg;

my $passed = 0;

sub check {
    my ($name, $cond) = @_;
    if ($cond) {
        print "  PASS: $name\n";
        $passed++;
    } else {
        die "  FAIL: $name\n";
    }
}

# ---- Test 1: Load and version ----
my $version = SQL::Abstract::Pg->VERSION;
check("Module load + version ($version)", defined $version);

# ---- Test 2: Basic INSERT ----
{
    my $a = SQL::Abstract::Pg->new(array_datatypes => 1, name_sep => ".", quote_char => '"');
    my ($sql, @bind) = $a->insert("foo", {bar => "baz"});
    check("INSERT SQL", $sql =~ /INSERT INTO "foo"/ && $sql =~ /VALUES/);
    check("INSERT bind", $bind[0] eq "baz");
}

# ---- Test 3: Basic SELECT ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    my ($sql) = $a->select("foo", "*");
    check("SELECT", $sql eq 'SELECT * FROM "foo"');
}

# ---- Test 4: ON CONFLICT DO NOTHING ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    my ($sql, @bind) = $a->insert("foo", {bar => "baz"}, {on_conflict => undef});
    check("ON CONFLICT DO NOTHING", $sql =~ /ON CONFLICT DO NOTHING/i);
    check("ON CONFLICT DO NOTHING bind", $bind[0] eq "baz");
}

# ---- Test 5: ON CONFLICT DO UPDATE ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    my ($sql, @bind) = $a->insert("foo", {bar => "baz"}, {on_conflict => ["foo" => {foo => "yada"}]});
    check("ON CONFLICT DO UPDATE", $sql =~ /ON CONFLICT.*DO UPDATE SET/i);
    check("ON CONFLICT DO UPDATE bind", $bind[0] eq "baz" && $bind[1] eq "yada");
}

# ---- Test 6: LIMIT/OFFSET ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    my ($sql, @bind) = $a->select("foo", "*", undef, {limit => 10, offset => 5});
    check("LIMIT/OFFSET", $sql =~ /LIMIT \? OFFSET \?/);
    check("LIMIT/OFFSET bind", $bind[0] == 10 && $bind[1] == 5);
}

# ---- Test 7: GROUP BY + HAVING ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    my ($sql, @bind) = $a->select("foo", "*", undef, {group_by => ["bar"], having => {baz => "yada"}});
    check("GROUP BY/HAVING", $sql =~ /GROUP BY/ && $sql =~ /HAVING/);
}

# ---- Test 8: JOIN ----
{
    my $a = SQL::Abstract::Pg->new(name_sep => ".", quote_char => '"');
    my ($sql) = $a->select(["foo", ["bar", foo_id => "id"]]);
    check("JOIN", $sql =~ /JOIN/ && $sql =~ /ON/);
}

# ---- Test 9: FOR UPDATE ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    my ($sql) = $a->select("foo", "*", undef, {for => "update"});
    check("FOR UPDATE", $sql =~ /FOR UPDATE/i);
}

# ---- Test 10: JSON operator ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    my ($sql, @bind) = $a->update("foo", {bar => {-json => [1, 2, 3]}});
    check("JSON UPDATE", $sql =~ /UPDATE.*SET/ && ref($bind[0]) eq "HASH");
}

# ---- Test 11: Error handling ----
{
    my $a = SQL::Abstract::Pg->new(quote_char => '"');
    eval { $a->insert("foo", {bar => "baz"}, {on_conflict => {}}) };
    check("Error: on_conflict hashref", $@ =~ /HASHREF/);
    eval { $a->select("foo", "*", undef, {for => "bad_value"}) };
    check("Error: invalid for value", $@ =~ /not allowed/);
}

my $total = 16;
print "\n$passed/$total tests passed\n";
exit($passed == $total ? 0 : 1);
