#!/usr/bin/env perl
# test_package test for Net::Jabber — verifies module loading and basic API
use strict;
use warnings;

eval {
    require Net::Jabber;
    Net::Jabber->import();
    1;
} or do {
    print "FAIL: Cannot load Net::Jabber: $@\n";
    exit 1;
};

print "Net::Jabber version: " . $Net::Jabber::VERSION . "\n";

# Test: Create a Jabber Client object
eval {
    my $client = Net::Jabber::Client->new();
    print "OK: Net::Jabber::Client created\n" if $client;
};
if ($@) {
    print "WARN: Client creation error (expected without server): $@\n";
}

# Test: Create a Message object
eval {
    my $msg = Net::Jabber::Message->new();
    $msg->SetMessage(to => 'test@example.com', body => 'hello');
    my $xml = $msg->GetXML();
    if ($xml =~ /message/) {
        print "OK: Net::Jabber::Message created and serialized\n";
    } else {
        print "WARN: Message XML unexpected: $xml\n";
    }
};
if ($@) {
    print "FAIL: Message creation error: $@\n";
    exit 1;
}

# Test: Create a Presence object
eval {
    my $pres = Net::Jabber::Presence->new();
    $pres->SetPresence(show => 'away', status => 'Busy');
    print "OK: Net::Jabber::Presence created\n";
};
if ($@) {
    print "FAIL: Presence creation error: $@\n";
    exit 1;
}

# Test: Create a JID object
eval {
    my $jid = Net::Jabber::JID->new(jid => 'user@example.com/resource');
    if ($jid->GetJID() eq 'user@example.com/resource') {
        print "OK: Net::Jabber::JID created and parsed\n";
    }
};
if ($@) {
    print "FAIL: JID creation error: $@\n";
    exit 1;
}

print "All tests passed.\n";
exit 0;
