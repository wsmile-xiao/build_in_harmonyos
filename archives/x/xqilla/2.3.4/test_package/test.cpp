#include <iostream>
#include <string>
#include <xqilla/xqilla-simple.hpp>

int main(int argc, char *argv[]) {
  // Initialise Xerces-C and XQilla by creating the factory object
  XQilla xqilla;

  // Parse an XQuery expression (AutoDelete deletes at end of scope)
  AutoDelete<XQQuery> query(xqilla.parse(X("1 to 100")));

  // Create a context object
  AutoDelete<DynamicContext> context(query->createDynamicContext());

  // Execute the query, using the context
  Result result = query->execute(context);

  // Iterate over the results, printing them; count and verify 1..100
  Item::Ptr item;
  int count = 0;
  long first = 0;
  long last = 0;
  while((item = result->next(context)).notNull()) {
    // Item has no asInt(); official simple-basic example only uses
    // asString(). Transcode and parse so first/last/count checks stay real.
    std::string s((const char *)UTF8(item->asString(context)));
    long v = 0;
    try {
      v = std::stol(s);
    } catch(...) {
      std::cerr << "non-integer item" << std::endl;
      return 2;
    }
    if(count == 0) first = v;
    last = v;
    std::cout << UTF8(item->asString(context)) << std::endl;
    ++count;
  }
  if(count != 100) {
    std::cerr << "want 100 items, got " << count << std::endl;
    return 3;
  }
  if(first != 1 || last != 100) {
    std::cerr << "want first=1 last=100, got first=" << first << " last=" << last << std::endl;
    return 4;
  }
  return 0;
}
