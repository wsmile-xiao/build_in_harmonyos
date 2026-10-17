#include <cassert>
#include <string>

#include <strict_variant/variant.hpp>

struct string_visitor {
  using result_type = std::string;

  std::string operator()(int value) const { return std::to_string(value); }
  std::string operator()(const std::string & value) const { return value; }
};

int main() {
  strict_variant::variant<int, std::string> value;
  assert(value.which() == 0);
  assert(value.get<int>() != nullptr);

  value = 42;
  assert(value.get<int>() != nullptr && *value.get<int>() == 42);

  value = std::string("HarmonyOS");
  assert(value.which() == 1);
  assert(value.get<std::string>() != nullptr);
  assert(value.get<std::string>() != nullptr &&
         *value.get<std::string>() == "HarmonyOS");
  assert(strict_variant::apply_visitor(string_visitor{}, value) == "HarmonyOS");

  value.emplace<int>(7);
  assert(value.get<int>() != nullptr && *value.get<int>() == 7);
  return 0;
}
