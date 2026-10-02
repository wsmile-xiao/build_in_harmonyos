// Consumer-perspective smoke test for belr 5.3.105 on HarmonyOS PC.
//
// It plays the role of a third-party application that installs the Conan
// package and uses only the public headers: compile an ABNF grammar, build a
// parser for it, install rule handlers, parse protocol text and check both the
// matched values and belr's partial-match semantics.
#include <functional>
#include <iostream>
#include <memory>
#include <string>

#include <belr/abnf.h>
#include <belr/grammarbuilder.h>
#include <belr/parser.h>

using namespace belr;

// Element type produced by the handlers. The consumer only needs the produced
// text plus the rule name, which is enough to validate the parse result.
class Element {
public:
  std::string rule;
  std::string text;
  virtual ~Element() = default;
};
using ElementPtr = std::shared_ptr<Element>;
// belr handlers receive the rule name and the matched text.
using Handler = std::function<ElementPtr(const std::string &, const std::string &)>;

static ElementPtr make_element(const std::string &rulename, const std::string &text) {
  auto element = std::make_shared<Element>();
  element->rule = rulename;
  element->text = text;
  return element;
}

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const char *what) {
  ++g_checks;
  if (!ok) {
    ++g_failures;
    std::cerr << "CHECK FAILED: " << what << "\n";
  }
}

int main() {
  static const char *grammar_text =
      "greeting-request = \"HELLO\" SP user 1*(SP param) CRLF\r\n"
      "user             = 1*(ALPHA / DIGIT / \"-\")\r\n"
      "param            = 1*(ALPHA / DIGIT)\r\n";

  ABNFGrammarBuilder builder;
  std::shared_ptr<Grammar> grammar = builder.createFromAbnf(grammar_text, std::make_shared<CoreRules>());
  check(grammar != nullptr, "ABNF grammar description compiles into a Grammar object");

  Parser<ElementPtr> parser(grammar);
  parser.setHandler("user", Handler(&make_element));
  parser.setHandler("param", Handler(&make_element));
  parser.setHandler("greeting-request", Handler(&make_element));

  // ── well-formed protocol message ──
  const std::string message = "HELLO alice-01 42 extra\r\n";
  size_t parsed_size = 0;
  ElementPtr element = parser.parseInput("greeting-request", message, &parsed_size);
  check(element != nullptr, "well-formed message matches the grammar");
  check(parsed_size == message.size(), "parser consumes the complete message");
  check(element != nullptr && element->text == message, "handler receives the matched text");
  check(element != nullptr && element->rule == "greeting-request", "handler receives the rule name");

  // ── parsing a single rule ──
  size_t user_size = 0;
  ElementPtr user = parser.parseInput("user", "alice-01", &user_size);
  check(user != nullptr && user->text == "alice-01", "single rule parse returns the token");
  // belr reports the recognizer stop position (8 for this leaf rule) while the
  // handler above still receives the complete token ("alice-01"): both are part
  // of the documented parse semantics, so both are asserted.
  check(user_size == 8, "recognizer reports its stop position for a leaf rule");

  // ── partial match: belr stops at the first character outside the rule ──
  size_t partial_size = 0;
  ElementPtr partial = parser.parseInput("user", "alice 01", &partial_size);
  check(partial == nullptr || partial_size == 5,
        "grammar stops at the first character that is not part of the rule");

  // ── missing terminator: the top level rule cannot match ──
  size_t bad_size = 0;
  ElementPtr bad = parser.parseInput("greeting-request", "HELLO alice-01 42", &bad_size);
  check(bad == nullptr, "message without CRLF terminator is rejected");

  std::cout << "BELR_CONSUMER_CHECKS=" << g_checks << " FAILURES=" << g_failures << "\n";
  if (g_failures != 0) {
    std::cerr << "BELR_CONSUMER_FAILED\n";
    return 1;
  }
  std::cout << "BELR_CONSUMER_OK" << std::endl;
  return 0;
}
