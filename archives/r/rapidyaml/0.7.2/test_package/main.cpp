// test_package consumer test for rapidyaml 0.7.2 — HarmonyOS/PC real test.
//
// Parses a non-trivial YAML document through the packaged rapidyaml API,
// walks the resulting tree, mutates a node, and re-emits it, asserting
// round-trip correctness. This is a real executable test that consumes the
// installed headers and libryml (R34: must actually use the library API).
#include <c4/yml/yml.hpp>
#include <c4/yml/emit.hpp>
#include <c4/yml/std/std.hpp>
#include <cstdio>
#include <string>

int main() {
    using namespace c4::yml;
    const char yaml[] = R"(
receipt:
  date: 2015-01-05
  user:
    given: James
    family: Bond
    age: 38
  items:
    - name: Widget
      qty: 3
      price: 19.99
    - name: Gadget
      qty: 1
      price: 299.99
)";

    Tree tree = parse_in_arena(c4::to_csubstr(yaml));
    ConstNodeRef root = tree.rootref();
    if (!root.is_map()) {
        std::printf("FAIL: root is not a map\n");
        return 1;
    }

    ConstNodeRef receipt = root.find_child("receipt");
    if (!receipt.readable()) {
        std::printf("FAIL: missing 'receipt' key\n");
        return 1;
    }
    ConstNodeRef date = receipt.find_child("date");
    if (date.val() != c4::to_csubstr("2015-01-05")) {
        std::printf("FAIL: wrong date scalar\n");
        return 1;
    }
    ConstNodeRef user = receipt.find_child("user");
    ConstNodeRef given = user.find_child("given");
    if (given.val() != c4::to_csubstr("James")) {
        std::printf("FAIL: wrong 'given' scalar\n");
        return 1;
    }
    ConstNodeRef items = receipt.find_child("items");
    if (!items.is_seq() || items.num_children() != 2) {
        std::printf("FAIL: items is not a 2-element seq\n");
        return 1;
    }
    ConstNodeRef first = items.child(0);
    ConstNodeRef qty = first.find_child("qty");
    if (qty.val() != c4::to_csubstr("3")) {
        std::printf("FAIL: wrong qty scalar\n");
        return 1;
    }

    // Mutate and re-emit: bump age, check emitted output contains it.
    Tree edit = tree;              // copyable tree
    NodeRef euser = edit.rootref().find_child("receipt").find_child("user");
    euser.find_child("age") = c4::to_csubstr("39");
    std::string out;
    emitrs_yaml(edit, &out);
    if (out.find("39") == std::string::npos) {
        std::printf("FAIL: emitted YAML does not contain updated age\n");
        return 1;
    }
    if (out.find("James") == std::string::npos) {
        std::printf("FAIL: emitted YAML lost user.given\n");
        return 1;
    }

    std::printf("PASS: rapidyaml 0.7.2 consumer test OK (parse/walk/mutate/emit)\n");
    return 0;
}