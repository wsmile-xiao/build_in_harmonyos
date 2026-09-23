// smoke.thrift — minimal IDL for the thrift1 functional smoke test.
namespace cpp2 smoke

enum Color {
  RED = 1,
  GREEN = 2,
  BLUE = 3,
}

struct Point {
  1: i32 x,
  2: i32 y,
  3: Color color,
}

service EchoService {
  Point echo(1: Point p),
}
