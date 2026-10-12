#include "i18n-demo/i18n.h"

#include <iostream>

int main() {
  const std::string one = i18n_demo::tr("demo", "singular message");
  const std::string many = i18n_demo::tr_plural("demo", "one file", "many files", 3);

  if (one.empty() || many.empty()) {
    std::cerr << "FAILED: empty translation result\n";
    return 1;
  }
  std::cout << "tr=" << one << " | tr_plural=" << many << "\n";
  return 0;
}
