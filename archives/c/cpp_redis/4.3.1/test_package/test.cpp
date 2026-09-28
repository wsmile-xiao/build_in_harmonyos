// test_package for cpp_redis 4.3.1 — exercises the public API (R34)
#include <cpp_redis/cpp_redis>
#include <cstdint>
#include <iostream>
#include <string>

int
main() {
  int failures = 0;

  // reply: integer type
  {
    cpp_redis::reply r((int64_t)42);
    if (!r.is_integer() || r.as_integer() != 42) {
      std::cerr << "FAIL: integer reply" << std::endl;
      ++failures;
    }
  }

  // reply: simple string type
  {
    cpp_redis::reply r("OK", cpp_redis::reply::string_type::simple_string);
    if (!r.is_simple_string() || r.as_string() != "OK") {
      std::cerr << "FAIL: simple string reply" << std::endl;
      ++failures;
    }
  }

  // reply: bulk string + as_string
  {
    cpp_redis::reply r("value", cpp_redis::reply::string_type::bulk_string);
    if (!r.is_bulk_string() || r.as_string() != "value") {
      std::cerr << "FAIL: bulk string reply" << std::endl;
      ++failures;
    }
  }

  // client constructible and disconnectable without a server
  {
    cpp_redis::client c;
    c.disconnect();  // no-op when not connected
  }

  if (failures == 0) {
    std::cout << "cpp_redis 4.3.1 test_package: OK" << std::endl;
    return 0;
  }
  std::cerr << "cpp_redis 4.3.1 test_package: " << failures << " failure(s)"
            << std::endl;
  return 1;
}
