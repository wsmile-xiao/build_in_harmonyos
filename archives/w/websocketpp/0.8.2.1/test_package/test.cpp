// SPDX-License-Identifier: BSD-3-Clause
// Consumer test for websocketpp 0.8.2.1 (header-only; upstream source is still the
// 0.8.2 tag). HarmonyOS PC / ohos-aarch64.
//
// Two layers:
//
// 1) Pure unit surfaces (no I/O):
//    * websocketpp::uri            — WS/URL parsing (wss default port, resource, query)
//    * base64 encode/decode        — Sec-WebSocket-Key handshake path
//    * utf8_validator              — close-reason / message validation
//    * close::status constants     — RFC6455 status codes
//    * endpoint user-agent round-trip
//
// 2) A real WebSocket session over loopback TCP, in-process, two io_contexts:
//    server<config::asio> + client<config::asio_client>, so the Boost.Asio
//    transport this recipe patches is executed, not merely compiled:
//      * endpoint::listen(host, service) -> synchronous resolver path
//      * client::get_connection("ws://localhost:...") -> async_resolve path
//      * start_perpetual()/stop_perpetual() -> io_service::work replacement
//        (boost::asio::executor_work_guard)
//      * set_timer()                        -> steady_timer + expiry() path
//      * async read/write/close handlers    -> io_context::strand + post path
//    The patched APIs were all removed from Boost 1.88+/Asio 1.31+, so a build
//    that only instantiates the templates proves far less than this does.
//
// The test is self-terminating: a websocketpp timer aborts the client run loop
// after 10 s and SIGALRM kills the process after 60 s, so CI can never hang on
// a transport regression.
#include <websocketpp/client.hpp>
#include <websocketpp/server.hpp>
#include <websocketpp/config/asio_client.hpp>
#include <websocketpp/config/asio.hpp>
#include <websocketpp/uri.hpp>
#include <websocketpp/base64/base64.hpp>
#include <websocketpp/utf8_validator.hpp>
#include <websocketpp/close.hpp>

#include <atomic>
#include <csignal>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>
#include <unistd.h>

typedef websocketpp::server<websocketpp::config::asio> test_server;
typedef websocketpp::client<websocketpp::config::asio_client> test_client;
typedef websocketpp::lib::asio::io_service io_service;

static int failures = 0;

#define CHECK(cond)                                                       \
    do {                                                                  \
        if (!(cond)) {                                                    \
            std::cerr << "FAIL: " #cond " (" << __FILE__ << ":"          \
                      << __LINE__ << ")" << std::endl;                    \
            ++failures;                                                   \
        }                                                                 \
    } while (0)

static void on_alarm(int) {
    std::cerr << "FAIL: test_websocketpp hit the 60 s SIGALRM watchdog"
              << std::endl;
    _exit(3);
}

static void unit_checks() {
    // ---- URI parsing: secure wss default port 443 ----
    websocketpp::uri u("wss://echo.example.org:443/ws/v1?token=abc");
    CHECK(u.get_valid());
    CHECK(u.get_secure());
    CHECK(u.get_host() == "echo.example.org");
    CHECK(u.get_port() == 443);
    // websocketpp exposes the request target (path + "?" + query) as the
    // "resource"; get_query() is the part after the '?'.
    CHECK(u.get_resource() == "/ws/v1?token=abc");
    CHECK(u.get_query() == "token=abc");

    // ---- URI parsing: plain ws explicit port ----
    websocketpp::uri u2("ws://localhost:9001/chat");
    CHECK(u2.get_valid());
    CHECK(!u2.get_secure());
    CHECK(u2.get_host() == "localhost");
    CHECK(u2.get_port() == 9001);
    CHECK(u2.get_resource() == "/chat");

    // ---- base64 round-trip (Sec-WebSocket-Key is a 16-byte base64 value) ----
    const std::string key = "dGhlIHNhbXBsZSBub25jZQ=="; // RFC6455 example
    std::string decoded = websocketpp::base64_decode(key);
    CHECK(decoded == "the sample nonce");
    CHECK(websocketpp::base64_encode(decoded) == key);

    // ---- UTF-8 validation ----
    CHECK(websocketpp::utf8_validator::validate(std::string("ok plain ascii")));
    CHECK(websocketpp::utf8_validator::validate(std::string("\xc3\xa9")));   // é
    CHECK(!websocketpp::utf8_validator::validate(std::string("\xff\xfe")));  // invalid

    // ---- RFC6455 close codes ----
    CHECK(websocketpp::close::status::normal == 1000);
    CHECK(websocketpp::close::status::going_away == 1001);
}

// Real echo session: server and client each own an io_context, exactly the way
// a consumer such as autobahn-cpp drives websocketpp.
static void session_checks() {
    io_service server_ios;
    io_service client_ios;

    std::atomic<int> server_rx(0);
    std::atomic<int> client_rx(0);
    std::atomic<bool> handshake_ok(false);
    std::atomic<bool> got_pong(false);
    std::atomic<bool> got_interrupt(false);
    std::atomic<bool> closed_cleanly(false);
    std::atomic<bool> timed_out(false);
    std::atomic<bool> connect_failed(false);
    std::string connect_error;
    std::atomic<bool> server_ec_ok(false);

    // ---------------- server ----------------
    test_server srv;
    srv.clear_access_channels(websocketpp::log::alevel::all);
    srv.clear_error_channels(websocketpp::log::elevel::all);
    srv.init_asio(&server_ios);
    // start_perpetual() is the io_service::work replacement user.
    srv.start_perpetual();
    srv.set_reuse_addr(true);

    websocketpp::lib::asio::error_code lec;
    // listen(host, service) goes through the resolver: this is the patched
    // lib::asio::resolve_endpoints()/resolve_empty()/resolve_first() path.
    srv.listen(std::string("127.0.0.1"), std::string("0"), lec);
    server_ec_ok = (!lec);
    CHECK(!lec);
    if (lec) {
        std::cerr << "FAIL: server listen failed: " << lec.message() << std::endl;
        return;
    }

    websocketpp::lib::asio::error_code pec;
    int port = srv.get_local_endpoint(pec).port();
    CHECK(!pec);
    CHECK(port > 0);
    if (port <= 0) {
        return;
    }

    srv.set_validate_handler(
        [](websocketpp::connection_hdl) { return true; });
    srv.set_open_handler([](websocketpp::connection_hdl) {});
    srv.set_message_handler(
        [&srv, &server_rx](websocketpp::connection_hdl hdl,
                           test_server::message_ptr msg) {
            ++server_rx;
            srv.send(hdl, "pong:" + msg->get_payload(),
                   websocketpp::frame::opcode::text);
        });
    srv.set_close_handler([](websocketpp::connection_hdl) {});
    srv.start_accept();

    std::thread server_thread([&server_ios] { server_ios.run(); });

    // ---------------- client ----------------
    test_client cli;
    cli.clear_access_channels(websocketpp::log::alevel::all);
    cli.clear_error_channels(websocketpp::log::elevel::all);
    cli.init_asio(&client_ios);
    cli.start_perpetual();
    cli.set_user_agent("websocketpp-ohos-test/0.8.2");
    CHECK(cli.get_user_agent() == "websocketpp-ohos-test/0.8.2");

    cli.set_fail_handler([&cli, &connect_failed, &connect_error](
                              websocketpp::connection_hdl hdl) {
        connect_failed = true;
        connect_error = cli.get_con_from_hdl(hdl)->get_ec().message();
        cli.stop();
    });

    cli.set_interrupt_handler(
        [&got_interrupt](websocketpp::connection_hdl) { got_interrupt = true; });

    cli.set_open_handler([&cli, &handshake_ok](websocketpp::connection_hdl hdl) {
        test_client::connection_ptr con = cli.get_con_from_hdl(hdl);
        handshake_ok = (con->get_response_code()
                        == websocketpp::http::status_code::switching_protocols);
        CHECK(con->send(std::string("ping")) == websocketpp::lib::error_code());
        // interrupt() is transported through the io_service post wrapper.
        con->interrupt();
    });

    cli.set_message_handler(
        [&cli, &got_pong, &client_rx](websocketpp::connection_hdl hdl,
                                      test_client::message_ptr msg) {
            ++client_rx;
            got_pong = (msg->get_payload() == "pong:ping");
            cli.get_con_from_hdl(hdl)->close(
                websocketpp::close::status::normal, std::string("done"));
        });

    cli.set_close_handler([&cli, &closed_cleanly](
                              websocketpp::connection_hdl hdl_unused) {
        closed_cleanly = true;
        cli.stop();
    });

    std::string url = "ws://localhost:" + std::to_string(port) + "/echo";
    websocketpp::lib::error_code gec;
    // "localhost" forces a real async DNS resolution: this is the patched
    // lib::asio::async_resolve_endpoints()/handle_resolve() path.
    test_client::connection_ptr con = cli.get_connection(url, gec);
    CHECK(!gec);
    if (gec) {
        std::cerr << "FAIL: get_connection failed: " << gec.message()
                  << std::endl;
        server_ios.stop();
        server_thread.join();
        return;
    }
    CHECK(con->get_uri()->get_host() == "localhost");
    CHECK(con->get_uri()->get_resource() == "/echo");

    // Watchdog: exercises endpoint::set_timer() (steady_timer + expiry()) and
    // guarantees the client run loop cannot block CI forever.
    cli.set_timer(10000, [&cli, &timed_out](
                             websocketpp::lib::error_code const & tec) {
        if (!tec) {
            timed_out = true;
            cli.stop();
        }
    });

    cli.connect(con);
    client_ios.run();          // returns from the close handler / watchdog
    CHECK(!timed_out);
    if (connect_failed) {
        std::cerr << "FAIL: websocket session failed: " << connect_error << std::endl;
    }
    CHECK(!connect_failed);
    CHECK(handshake_ok);
    CHECK(got_pong);
    CHECK(server_rx.load() == 1);
    CHECK(client_rx.load() == 1);
    CHECK(got_interrupt);
    CHECK(closed_cleanly);
    CHECK(con->get_state() == websocketpp::session::state::closed);
    CHECK(con->get_remote_close_code() == websocketpp::close::status::normal);
    CHECK(con->get_remote_close_reason() == "done");

    // ---------------- shutdown ----------------
    server_ios.stop();
    server_thread.join();
    cli.stop_perpetual();
    srv.stop_perpetual();
    CHECK(server_ec_ok.load());
}

int main() {
    std::signal(SIGALRM, on_alarm);
    alarm(60);

    unit_checks();
    session_checks();

    if (failures == 0) {
        std::cout << "test_websocketpp: all checks passed" << std::endl;
        return 0;
    }
    std::cerr << "test_websocketpp: " << failures << " checks failed"
              << std::endl;
    return 1;
}
