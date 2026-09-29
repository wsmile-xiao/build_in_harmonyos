# test_package/test-script.zeek — P1 consumer test policy (4 assertions).
#
# Explicit minimal policy: loads only the conn/ssl/dns/http analyzers the
# assertions need. Deliberately does NOT load packet-protocols (igmp), whose
# base load fatals at zeek_init on DISABLE_SPICY builds ("Failed to register
# IGMP Spicy analyzer."); on Spicy-on builds the base context loads cleanly,
# so these @load lines are simply idempotent there.
#
# The handlers print tagged lines to stderr (captured by test.sh). They
# assert at the event level, independent of the 8.2.1 C++-side log schemas;
# test.sh additionally checks that the four protocol logs are written.

@load base/protocols/conn
@load base/protocols/ssl
@load base/protocols/dns
@load base/protocols/http

event connection_state_remove(c: connection) &priority=5
	{
	print "P1-CONN=%s %s %s %s %s\n", c$id$orig_h, c$id$orig_p,
		c$id$resp_h, c$id$resp_p, c$id$proto;
	}

event ssl_extension_server_name(c: connection, is_client: bool,
                                names: string_vec) &priority=10
	{
	if ( is_client )
		print "P1-SNI=%s\n", names[0];
	}

event dns_request(c: connection, msg: dns_msg, query: string,
                  qtype: count, qclass: count) &priority=10
	{
	print "P1-DNS=%s\n", query;
	}

event http_request(c: connection, method: string, original_URI: string,
                   unescaped_URI: string, version: string) &priority=10
	{
	print "P1-HTTP=%s %s\n", method, original_URI;
	}
