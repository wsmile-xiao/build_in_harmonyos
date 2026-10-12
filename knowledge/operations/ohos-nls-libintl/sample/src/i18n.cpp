#include "i18n-demo/i18n.h"

namespace i18n_demo {

std::string tr(const char *domain, const char *msgid) {
  if (domain == nullptr || msgid == nullptr) {
    return std::string();
  }
  return std::string(dgettext(domain, msgid));
}

std::string tr_plural(const char *domain, const char *msgid,
                      const char *msgid_plural, unsigned long n) {
  if (domain == nullptr || msgid == nullptr) {
    return std::string();
  }
  if (msgid_plural == nullptr) {
    return std::string(dgettext(domain, msgid));
  }
  return std::string(dngettext(domain, msgid, msgid_plural, n));
}

} // namespace i18n_demo
