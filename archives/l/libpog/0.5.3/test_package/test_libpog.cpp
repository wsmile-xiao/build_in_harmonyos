// Consumer test for the installed libpog package.
//
// Includes the public pog headers (which pull RE2 and fmt) and exercises a
// small, deterministic part of the API plus the two linked dependencies.
#include <cstdint>
#include <cstdio>
#include <string>

#include <fmt/format.h>
#include <re2/re2.h>

#include <pog/pog.h>
#include <pog/symbol.h>

static int checks;
static int failures;

static void check(bool ok, const char *what)
{
    checks++;
    if (ok) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

int main(void)
{
    using namespace pog;

    Symbol<int> nt(42, SymbolKind::Nonterminal, "testing_nonterminal");
    check(nt.get_index() == 42u && nt.get_name() == "testing_nonterminal",
          "Symbol nonterminal index/name round trip");
    check(nt.is_nonterminal() && !nt.is_terminal() && !nt.is_end(),
          "Symbol nonterminal kind flags");
    check(!nt.has_precedence(), "Symbol has no precedence by default");

    Symbol<int> terminal(7, SymbolKind::Terminal, "testing_terminal");
    check(terminal.is_terminal() && !terminal.is_nonterminal(),
          "Symbol terminal kind flags");

    Symbol<int> end(0, SymbolKind::End, "testing_end");
    check(end.is_end(), "Symbol end kind flag");

    terminal.set_precedence(1, Associativity::Right);
    check(terminal.has_precedence()
              && terminal.get_precedence() == (Precedence{1, Associativity::Right}),
          "Symbol precedence round trip");

    RE2 re("a+b");
    check(RE2::FullMatch("aaab", re), "re2 FullMatch through the linked dependency");
    check(!RE2::FullMatch("abc", re), "re2 negative match");

    check(fmt::format("v={}", 42) == "v=42", "fmt::format through the linked dependency");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures ? 1 : 0;
}
