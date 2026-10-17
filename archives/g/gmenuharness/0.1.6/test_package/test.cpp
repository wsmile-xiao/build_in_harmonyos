// Consumer test for gmenuharness 0.1.6.
// Exercises the real library API: MatchResult (failure/merge/concat) and
// MenuItemMatcher (builder chain, no D-Bus needed).
#include <lomiri/gmenuharness/MatchResult.h>
#include <lomiri/gmenuharness/MenuItemMatcher.h>

#include <cstdio>
#include <string>

namespace mh = lomiri::gmenuharness;

static int checks_passed = 0;
static int checks_total = 0;

static int check(bool condition, const char *message) {
    ++checks_total;
    if (!condition) {
        std::printf("FAIL: %s\n", message);
        return 0;
    }
    ++checks_passed;
    return 1;
}

// Test 1: MatchResult records failures, merges, and concatenates messages.
static int test_match_result() {
    int ok = 1;
    mh::MatchResult result;
    ok &= check(result.success(), "fresh MatchResult must succeed");
    result.failure({1, 2, 3}, "the message");
    result.failure({1, 3, 4}, "the other message");
    ok &= check(!result.success(), "MatchResult with failures must not succeed");
    std::string text = result.concat_failures();
    ok &= check(!text.empty(), "concat_failures must be non-empty");
    ok &= check(text.find("the message") != std::string::npos,
                "concat_failures must contain first message");
    ok &= check(text.find("1 3 4") != std::string::npos,
                "concat_failures must contain second location");

    mh::MatchResult other;
    other.failure({2, 0}, "merged message");
    result.merge(other);
    ok &= check(!result.success(), "merged MatchResult must not succeed");
    ok &= check(result.concat_failures().find("merged message") != std::string::npos,
                "merged failures must be visible");

    mh::MatchResult child = result.createChild();
    ok &= check(child.success(), "fresh child MatchResult must succeed");
    return ok;
}

// Test 2: MenuItemMatcher builder chain links against the real library.
static int test_menu_item_matcher() {
    int ok = 1;
    mh::MenuItemMatcher item;
    item.label("Main").action("app.main").enabled(true).toggled(false);
    item.string_attribute("description", "Main description");
    item.boolean_attribute("visible", true);
    item.int32_attribute("count", 3);
    item.attribute_not_set("never-set");
    item.mode(mh::MenuItemMatcher::Mode::all);
    item.submenu();
    item.item(mh::MenuItemMatcher().label("First").action("app.first"));
    item.item(mh::MenuItemMatcher().label("Second").action("app.second"));
    item.has_exactly(2);

    mh::MenuItemMatcher check_item = mh::MenuItemMatcher::checkbox().label("Check");
    mh::MenuItemMatcher radio_item = mh::MenuItemMatcher::radio().label("Radio");
    (void)check_item;
    (void)radio_item;

    // Copy/assign must work (exercises the real Priv implementation).
    mh::MenuItemMatcher copy = item;
    mh::MenuItemMatcher moved = std::move(copy);
    (void)moved;
    ok &= check(true, "MenuItemMatcher builder chain must not crash");
    return ok;
}

int main() {
    int ok = 1;
    ok &= test_match_result();
    ok &= test_menu_item_matcher();
    std::printf("gmenuharness consumer tests: %d/%d checks passed\n",
                checks_passed, checks_total);
    if (!ok || checks_passed != checks_total || checks_total == 0) {
        return 1;
    }
    std::puts("gmenuharness 0.1.6 consumer test: OK");
    return 0;
}
