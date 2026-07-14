// test_marisa.cpp — marisa 0.3.1 consumer test (Conan L1).
//
// Exercises the real libmarisa C++ API: builds a Keyset, builds a Trie,
// saves it to disk, reloads it, and runs lookup / predictive_search /
// reverse_lookup through a marisa::Agent. Fails (returns non-zero) if any
// check does not hold.
#include <marisa.h>

#include <cstdio>
#include <string>

namespace {

int failures = 0;

void check(bool cond, const char *label) {
    if (cond) {
        std::printf("PASS: %s\n", label);
    } else {
        std::printf("FAIL: %s\n", label);
        ++failures;
    }
}

}  // namespace

int main() {
    marisa::Keyset keyset;
    keyset.push_back("apple");
    keyset.push_back("application");
    keyset.push_back("apply");
    keyset.push_back("banana");

    marisa::Trie trie;
    trie.build(keyset);

    // 1. All four keys are registered.
    check(trie.size() == 4, "trie holds 4 keys");

    marisa::Agent agent;

    // 2. lookup() finds an inserted key.
    agent.set_query("apple");
    check(trie.lookup(agent), "lookup(apple) found");

    // 3. lookup() finds another inserted key.
    agent.set_query("banana");
    check(trie.lookup(agent), "lookup(banana) found");

    // 4. lookup() rejects a key that was never inserted.
    agent.set_query("cherry");
    check(!trie.lookup(agent), "lookup(cherry) not found");

    // 5. predictive_search("app") returns apple, application, apply.
    agent.set_query("app");
    int predictive_hits = 0;
    while (trie.predictive_search(agent)) {
        ++predictive_hits;
    }
    check(predictive_hits == 3, "predictive_search(app) yields 3 keys");

    // 6. common_prefix_search("application") walks its prefixes.
    agent.set_query("application");
    int prefix_hits = 0;
    while (trie.common_prefix_search(agent)) {
        ++prefix_hits;
    }
    check(prefix_hits >= 1, "common_prefix_search(application) >= 1");

    // 7. reverse_lookup() recovers a stored key by its id.
    marisa::Agent rev_agent;
    rev_agent.set_query(keyset[1].id());  // id assigned during build()
    trie.reverse_lookup(rev_agent);
    {
        std::string recovered(rev_agent.key().ptr(), rev_agent.key().length());
        check(recovered == "application", "reverse_lookup(id) returns application");
    }

    // 8. save() then load() round-trips the trie to a second instance.
    const char *trie_file = "marisa_test.trie";
    trie.save(trie_file);

    marisa::Trie loaded;
    loaded.load(trie_file);
    check(loaded.size() == 4, "loaded trie holds 4 keys");

    agent.set_query("apply");
    check(loaded.lookup(agent), "loaded lookup(apply) found");

    if (failures > 0) {
        std::printf("\n%d test(s) FAILED\n", failures);
        return 1;
    }
    std::printf("\nAll marisa tests passed.\n");
    return 0;
}
