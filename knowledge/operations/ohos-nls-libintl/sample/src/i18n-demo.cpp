// 样例 CLI：i18n-demo-cli <domain> <msgid> [n]
// 无可用翻译目录时返回 msgid 原样（gettext 语义），便于在无 locale 目录的
// 设备/CI 上做确定性校验。
#include "i18n-demo/i18n.h"

#include <cstdlib>
#include <iostream>

int main(int argc, char **argv) {
  if (argc < 3) {
    std::cerr << "usage: i18n-demo-cli <domain> <msgid> [n]\n";
    return 1;
  }
  const char *domain = argv[1];
  const char *msgid = argv[2];
  if (argc >= 4) {
    unsigned long n = std::strtoul(argv[3], nullptr, 10);
    std::cout << i18n_demo::tr_plural(domain, msgid, msgid, n) << "\n";
  } else {
    std::cout << i18n_demo::tr(domain, msgid) << "\n";
  }
  return 0;
}
