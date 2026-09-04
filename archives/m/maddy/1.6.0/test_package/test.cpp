// test_package consumer test for maddy 1.6.0
// Real consumer usage: parse a small Markdown snippet to HTML via maddy::Parser.
#include <memory>
#include <sstream>
#include <string>

#include "maddy/parser.h"

int main()
{
  std::shared_ptr<maddy::Parser> parser = std::make_shared<maddy::Parser>();

  std::stringstream markdownStream;
  markdownStream << "# Hello World\n"
                 << "This is a **bold** text and this is *italic* text.\n";

  std::string html = parser->Parse(markdownStream);

  bool ok = !html.empty();
  ok = ok && (html.find("<h1>") != std::string::npos);
  ok = ok && (html.find("Hello World") != std::string::npos);

  return ok ? 0 : 1;
}