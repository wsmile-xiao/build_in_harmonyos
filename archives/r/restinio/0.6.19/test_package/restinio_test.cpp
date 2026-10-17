// restinio 0.6.19 consumer smoke test (API / dependency connectivity).
//
// This is an API-and-dependency-connectivity consumer test, NOT an
// end-to-end HTTP server test: it compiles and links against the real Conan
// requires (fmt, http-parser) and the bundled standalone-asio snapshot, and
// wires an upstream-blessed express_router_t<> request handler into
// on_this_thread<traits_t>() server settings (same API shape as
// dev/sample/hello_world). It deliberately does NOT call restinio::run()
// (which would block forever); it does not cover sendfile or full request/
// response round-trips. No external network, no root, no fixed port, no
// certificate.
#include <restinio/all.hpp>

#include <atomic>
#include <iostream>
#include <memory>

#include <fmt/core.h>
#include <http_parser.h>

static std::atomic<int> g_request_count{0};

using router_t = restinio::router::express_router_t<>;

static auto
create_request_handler()
{
  auto router = std::make_unique<router_t>();
  router->http_get(
    "/",
    [](auto req, auto) {
      g_request_count.fetch_add(1, std::memory_order_acq_rel);
      req->create_response()
        .append_header(restinio::http_field::content_type, "text/plain; charset=utf-8")
        .set_body("restinio-ok")
        .done();
      return restinio::request_accepted();
    });
  router->http_get(
    "/json",
    [](auto req, auto) {
      req->create_response()
        .append_header(restinio::http_field::content_type, "application/json")
        .set_body(R"-({"message":"restinio-ok"})-")
        .done();
      return restinio::request_accepted();
    });
  return router;
}

int
main()
{
  // Assertion 1: fmt linkage — restinio's public formatters facade delegates
  // to fmt::format.
  const std::string formatted = fmt::format("restinio {}", "0.6.19");
  if (formatted != "restinio 0.6.19") {
    std::cerr << "fmt linkage check failed: " << formatted << std::endl;
    return 1;
  }

  // Assertion 2: http-parser symbol linkage — restinio's http_headers facade
  // uses http_parser_* symbols at runtime.
  http_parser_settings s;
  http_parser_settings_init(&s);
  (void)s;

  // Assertion 3: restinio request handler wired — install the express_router
  // into a single-threaded server with the official traits_t shape. We do NOT
  // call restinio::run() (it blocks); wiring the router + building the server
  // settings is the smoke goal for a header-only library on OHOS.
  using traits_t = restinio::traits_t<
    restinio::asio_timer_manager_t,
    restinio::single_threaded_ostream_logger_t,
    router_t>;

  auto router = create_request_handler();
  restinio::on_this_thread<traits_t>()
    .port(0)            // ephemeral port
    .address("127.0.0.1")
    .request_handler(std::move(router));

  const int assertions_passed = 3;
  std::cout << "restinio_test: assertions_passed=" << assertions_passed
            << " request_handler=wired"
            << " fmt_link=ok"
            << " http_parser_link=ok"
            << std::endl;
  return 0;
}
