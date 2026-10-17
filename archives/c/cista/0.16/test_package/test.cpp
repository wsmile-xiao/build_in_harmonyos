#include "cista/serialization.h"
#include "cista/containers.h"

#include <cassert>
#include <string>

struct serialize_me {
  int a_{0};
  struct inner {
    int b_{0};
    int c_{0};
    cista::raw::string d_;
  } j_;
};

int main() {
  cista::byte_buf buf;
  {
    serialize_me obj{1, {2, 3, cista::raw::string{"testtes"}}};
    buf = cista::serialize(obj);
  }  // EOL obj

  assert(buf.size() == sizeof(serialize_me));

  auto const serialized =
      cista::deserialize<serialize_me>(&buf[0], &buf[0] + buf.size());
  assert(serialized->a_ == 1);
  assert(serialized->j_.b_ == 2);
  assert(serialized->j_.c_ == 3);
  assert(serialized->j_.d_ == cista::raw::string{"testtes"});

  return 0;
}