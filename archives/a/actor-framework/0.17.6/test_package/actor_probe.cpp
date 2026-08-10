#include <caf/all.hpp>

#include <chrono>
#include <cstring>
#include <iostream>

using namespace caf;

behavior calculator() {
  return {
    [](int value) -> result<int> {
      if (value < 0)
        return make_error(sec::invalid_argument);
      return value * 2;
    },
  };
}

int main(int argc, char** argv) {
  const bool invalid_mode = argc == 2
                            && std::strcmp(argv[1], "--expect-invalid") == 0;
  actor_system_config config;
  actor_system system{config};
  auto worker = system.spawn(calculator);
  scoped_actor self{system};
  bool passed = false;
  self->request(worker, std::chrono::seconds(2), invalid_mode ? -1 : 21)
    .receive(
      [&](int value) { passed = !invalid_mode && value == 42; },
      [&](const error& err) {
        passed = invalid_mode && err == sec::invalid_argument;
      });
  self->send_exit(worker, exit_reason::user_shutdown);
  if (!passed) {
    std::cerr << "FAIL: actor request scenario did not produce the expected result\n";
    return 1;
  }
  std::cout << (invalid_mode
                  ? "PASS: invalid actor input propagated as invalid_argument\n"
                  : "PASS: actor request/reply returned 42\n");
  return 0;
}
