#include <peglib.h>

#include <iostream>

int main() {
  peg::parser parser(R"(
    Start <- 'hello'
  )");

  if (!parser) {
    std::cerr << "parser construction failed\n";
    return 1;
  }
  if (!parser.parse("hello")) {
    std::cerr << "valid input was rejected\n";
    return 2;
  }
  if (parser.parse("world")) {
    std::cerr << "invalid input was accepted\n";
    return 3;
  }

  std::cout << "cpp-peglib consumer test passed\n";
  return 0;
}
