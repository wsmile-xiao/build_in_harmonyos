#include <lngs/plurals.hpp>
#include "plural_rule.hpp"

extern "C" int mbits_lngs_shared_consumer() noexcept {
    try {
        auto const rule = lngs::plurals::decode(mbits_lngs_english_plural_rule);
        return rule ? static_cast<int>(rule.eval(2)) : -1;
    } catch (...) {
        return -1;
    }
}
