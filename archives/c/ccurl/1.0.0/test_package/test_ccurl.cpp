#include "curl.hh"

#include <cassert>
#include <string>

int main() {
  curl::global global;
  std::string body;
  curl::callback::string callback(body);
  assert(callback.fn("ccurl", 5));
  assert(body == "ccurl");

  curl::handle handle(global, callback);
  handle.set_timeout(2);
  handle.set_useragent("ccurl-test");

  curl::tag first;
  first.set_etag("etag");
  curl::tag second;
  second.set_etag("etag");
  assert(first == second);
  return 0;
}
