// Consumer-side L1 test for reflect-cpp 0.17.0 (conan test_package).
// Exercises the real public API: reflection-based JSON (de)serialization,
// struct/variant handling and error reporting.
#include <rfl.hpp>
#include <rfl/json.hpp>

#include <cstdint>
#include <iostream>
#include <map>
#include <string>
#include <variant>
#include <vector>

namespace {

int failures = 0;

void check(bool cond, const std::string& name) {
  if (cond) {
    std::cout << "[PASS] " << name << std::endl;
  } else {
    std::cout << "[FAIL] " << name << std::endl;
    ++failures;
  }
}

struct Person {
  std::string name;
  std::uint32_t age;
  std::vector<std::string> tags;
};

struct Address {
  std::string city;
  std::int32_t zip;
};

using Item = std::variant<Person, Address>;

}  // namespace

int main() {
  // 1. Write a struct to JSON
  Person homer{.name = "Homer", .age = 45, .tags = {"Moe's", "D'oh!"}};
  const std::string json = rfl::json::write(homer);
  check(json ==
            R"({"name":"Homer","age":45,"tags":["Moe's","D'oh!"]})",
        "json::write struct");

  // 2. Read JSON back into the same struct (round-trip)
  const auto read_res = rfl::json::read<Person>(json);
  check(static_cast<bool>(read_res), "json::read struct parses");
  if (read_res) {
    const Person& p = read_res.value();
    check(p.name == "Homer", "round-trip name");
    check(p.age == 45, "round-trip age");
    check(p.tags.size() == 2 && p.tags[1] == "D'oh!", "round-trip tags");
  } else {
    check(false, "read error: " + read_res.error().value().what());
  }

  // 3. std::map serialization
  std::map<std::string, std::int64_t> scores{{"a", 1}, {"b", 2}};
  const std::string scores_json = rfl::json::write(scores);
  check(scores_json == R"({"a":1,"b":2})", "json::write std::map");

  // 4. Variant resolution (type dispatch on a field)
  const std::string item_json = R"({"city":"Springfield","zip":97401})";
  const auto item_res = rfl::json::read<Item>(item_json);
  check(static_cast<bool>(item_res), "json::read variant parses");
  if (item_res) {
    const Item& item = item_res.value();
    check(std::holds_alternative<Address>(item),
          "variant resolves to Address");
    if (std::holds_alternative<Address>(item)) {
      const auto& addr = std::get<Address>(item);
      check(addr.city == "Springfield" && addr.zip == 97401,
            "variant field values");
    }
  } else {
    check(false, "variant read error");
  }

  // 5. Error reporting on malformed JSON
  const auto bad_res = rfl::json::read<Person>("{not json");
  check(!static_cast<bool>(bad_res), "malformed JSON reported as error");
  if (bad_res.error()) {
    check(!bad_res.error().value().what().empty(), "error carries message");
  }

  // 6. Error reporting on wrong shape (missing required field)
  const auto miss_res = rfl::json::read<Person>(R"({"name":"x"})");
  check(!static_cast<bool>(miss_res), "missing field reported as error");

  if (failures == 0) {
    std::cout << "test_reflect_cpp: ALL OK" << std::endl;
    return 0;
  }
  std::cout << "test_reflect_cpp: " << failures << " check(s) FAILED"
            << std::endl;
  return 1;
}
