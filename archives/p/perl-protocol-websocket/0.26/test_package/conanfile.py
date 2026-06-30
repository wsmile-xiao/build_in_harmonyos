#!/usr/bin/env python3
"""Conan test_package — perl-protocol-websocket 0.26

Tests that Protocol::WebSocket can be loaded, version verified, and
core WebSocket protocol functions work correctly on HarmonyOS.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlProtocolWebSocketTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find WebSocket.pm in the package folder
        pkg = self.dependencies["perl-protocol-websocket"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "WebSocket.pm"), recursive=True)
        if not pm_files:
            raise Exception("WebSocket.pm not found in package")
        # Get the lib directory (parent of Protocol/ directory)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Set PERL5LIB to include both the package lib and system-installed Perl deps
        deps_lib = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + deps_lib + ":" + env.get("PERL5LIB", "")

        test_script = r'''
use strict;
use warnings;
use Test::More;

# Test 1: Module loading
BEGIN {
    use_ok("Protocol::WebSocket");
    use_ok("Protocol::WebSocket::Frame");
    use_ok("Protocol::WebSocket::Handshake::Client");
    use_ok("Protocol::WebSocket::Handshake::Server");
    use_ok("Protocol::WebSocket::URL");
    use_ok("Protocol::WebSocket::Cookie");
}
pass("All modules loaded");

# Test 2: Version
is($Protocol::WebSocket::VERSION, "0.26", "Version is 0.26");

# Test 3: Text frame round-trip
{
    my $f = Protocol::WebSocket::Frame->new(buffer => "Hello WS");
    my $enc = $f->to_bytes;
    ok(defined $enc, "Text frame encoded");
    my $f2 = Protocol::WebSocket::Frame->new($enc);
    is($f2->next, "Hello WS", "Text frame decoded");
}

# Test 4: Binary frame
{
    my $f = Protocol::WebSocket::Frame->new(buffer => "\x00\x01\x02");
    my $enc = $f->to_bytes;
    my $f2 = Protocol::WebSocket::Frame->new($enc);
    is($f2->next_bytes, "\x00\x01\x02", "Binary frame decoded");
}

# Test 5: Close frame
{
    my $f = Protocol::WebSocket::Frame->new(type => "close", buffer => "");
    my $enc = $f->to_bytes;
    my $f2 = Protocol::WebSocket::Frame->new($enc);
    $f2->next;
    ok($f2->is_close, "Close frame type detected");
}

# Test 6: Ping/Pong
{
    my $ping = Protocol::WebSocket::Frame->new(type => "ping", buffer => "ping");
    my $enc = $ping->to_bytes;
    my $f2 = Protocol::WebSocket::Frame->new($enc);
    is($f2->next, "ping", "Ping frame decoded");
    ok($f2->is_ping, "Ping type detected");
}

# Test 7: Masked frame
{
    my $f = Protocol::WebSocket::Frame->new(buffer => "masked", masked => 1);
    my $enc = $f->to_bytes;
    my $f2 = Protocol::WebSocket::Frame->new($enc);
    is($f2->next, "masked", "Masked frame decoded");
}

# Test 8: Client handshake
{
    my $hs = Protocol::WebSocket::Handshake::Client->new(url => "ws://example.com:8080/chat");
    my $req = $hs->to_string;
    like($req, qr/GET/, "Client handshake has GET");
    like($req, qr/Upgrade:\s*websocket/i, "Client handshake has Upgrade");
    like($req, qr/Sec-WebSocket-Key/i, "Client handshake has Key");
}

# Test 9: Server handshake
{
    my $hs = Protocol::WebSocket::Handshake::Server->new;
    my $client_req = "GET /chat HTTP/1.1\r\nHost: example.com\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n";
    $hs->parse($client_req);
    ok($hs->is_done, "Server handshake parsed");
    my $res = $hs->to_string;
    like($res, qr/101/, "Server response 101");
    like($res, qr/Sec-WebSocket-Accept/i, "Server response has Accept");
}

# Test 10: URL parsing
{
    my $url = Protocol::WebSocket::URL->new->parse("ws://example.com:8080/chat");
    is($url->host, "example.com", "URL host");
    is($url->port, "8080", "URL port");
    ok(!$url->secure, "URL not secure");
}

# Test 11: WSS URL
{
    my $url = Protocol::WebSocket::URL->new->parse("wss://secure.example.com/wss");
    ok($url->secure, "WSS URL secure");
}

# Test 12: Cookie
{
    my $c = Protocol::WebSocket::Cookie->new;
    $c->parse("name=value; foo=bar");
    is(scalar @{$c->pairs}, 2, "Cookie 2 pairs");
}

# Test 13: Full round-trip
{
    my $client = Protocol::WebSocket::Handshake::Client->new(url => "ws://localhost:3000/echo");
    my $req = $client->to_string;
    my $server = Protocol::WebSocket::Handshake::Server->new;
    $server->parse($req);
    ok($server->is_done, "Round-trip: server parsed client");
    my $res = $server->to_string;
    $client->parse($res);
    ok($client->is_done, "Round-trip: client parsed server");
}

done_testing();
'''

        # Write test script to temp file
        test_file = os.path.join(self.build_folder, "test_ws.pl")
        with open(test_file, "w") as f:
            f.write(test_script)

        # Test 1: Load Protocol::WebSocket and check version
        result = subprocess.run(
            ['perl', '-MProtocol::WebSocket', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.output.error(f"Protocol::WebSocket load test failed: {result.stderr}")
            raise Exception(f"Protocol::WebSocket load test failed with exit code {result.returncode}")

        self.output.success(f"Protocol::WebSocket loaded successfully: {result.stdout}")

        # Test 2: Verify version
        result2 = subprocess.run(
            ['perl', '-MProtocol::WebSocket', '-e',
             'die unless $Protocol::WebSocket::VERSION eq "0.26"; print "Version OK\n"'],
            env=env, capture_output=True, text=True
        )

        if result2.returncode != 0:
            self.output.warning(f"Version check had issues: {result2.stderr}")
        else:
            self.output.success(result2.stdout)

        # Test 3: Run comprehensive functional tests
        result3 = subprocess.run(
            ['perl', test_file],
            env=env, capture_output=True, text=True
        )

        if result3.returncode != 0:
            self.output.error(f"Functional tests failed:\n{result3.stdout}\n{result3.stderr}")
            raise Exception(f"Functional tests failed with exit code {result3.returncode}")

        self.output.success(f"Functional tests passed:\n{result3.stdout}")
