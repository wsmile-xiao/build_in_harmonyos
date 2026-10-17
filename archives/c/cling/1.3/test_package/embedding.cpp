#include <cling/Interpreter/Interpreter.h>
#include <cling/Interpreter/Value.h>

#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: cling_embedding <package-cling> <package-prefix>\n";
    return 2;
  }

  const std::string include_arg = std::string("-I") + argv[2] + "/include";
  const char* interpreter_args[] = {
      argv[1], "-std=c++17", include_arg.c_str()};
  cling::Interpreter interpreter(3, interpreter_args, argv[2]);
  if (!interpreter.isValid()) {
    std::cerr << "embedded interpreter is invalid\n";
    return 3;
  }

  cling::Value value;
  if (interpreter.evaluate("6 * 7", value) != cling::Interpreter::kSuccess) {
    std::cerr << "embedded evaluation failed\n";
    return 4;
  }
  if (value.castAs<long long>() != 42) {
    std::cerr << "embedded result mismatch\n";
    return 5;
  }

  std::cout << "CLING_EMBED_RESULT=42\n";
  return 0;
}
