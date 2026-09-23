// test_package/test_boost_locale.cpp — boost1.84-locale 1.84.0 L1 smoke test.
// Exercises Boost.Locale (std backend + musl built-in iconv):
// generator/locale construction, info facet, encoding conversion
// (UTF-8 <-> ISO-8859-1 via iconv), collation, formatting, format
// interpolation, date_time calendar, message fallback.
#include <boost/locale/conversion.hpp>
#include <boost/locale/date_time.hpp>
#include <boost/locale/encoding.hpp>
#include <boost/locale/format.hpp>
#include <boost/locale/formatting.hpp>
#include <boost/locale/generator.hpp>
#include <boost/locale/gnu_gettext.hpp>
#include <boost/locale/info.hpp>
#include <boost/locale/localization_backend.hpp>
#include <boost/locale/message.hpp>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

int main() {
    using namespace boost::locale;

    // Select the std backend (the backend compiled into this package)
    localization_backend_manager mgr = localization_backend_manager::global();
    mgr.select("std");
    localization_backend_manager::global(mgr);

    // 1. generator + info facet: en_US.UTF-8
    generator gen;
    std::locale l = gen("en_US.UTF-8");
    const info& inf = std::use_facet<info>(l);
    if (inf.language() != "en" || inf.country() != "US") {
        std::cerr << "info facet mismatch: lang=" << inf.language()
                  << " country=" << inf.country() << std::endl;
        return 1;
    }
    std::cout << "info: " << inf.language() << "_" << inf.country()
              << " utf8=" << inf.utf8() << std::endl;

    // 2. encoding conversion via musl iconv: ISO-8859-1 <-> UTF-8
    //    "grüßen" in Latin-1 bytes -> UTF-8
    const std::string latin1 = "gr\xFC\xDF"
                               "en";
    const std::string utf8 = conv::to_utf<char>(latin1, "ISO-8859-1");
    if (utf8 != "gr\xC3\xBC\xC3\x9F"
                 "en")
    {
        std::cerr << "to_utf(ISO-8859-1) failed: len=" << utf8.size() << std::endl;
        return 1;
    }
    const std::string back = conv::from_utf(utf8, "ISO-8859-1");
    if (back != latin1) {
        std::cerr << "from_utf(ISO-8859-1) roundtrip failed" << std::endl;
        return 1;
    }
    std::cout << "encoding: latin1<->utf8 roundtrip OK (" << utf8.size() << " bytes)" << std::endl;

    // 3. invalid charset must throw
    try {
        (void)conv::to_utf<char>("hello", "no-such-charset");
        std::cerr << "invalid_charset_error not thrown" << std::endl;
        return 1;
    } catch (const conv::invalid_charset_error&) {
        std::cout << "encoding: invalid charset throws OK" << std::endl;
    }

    // 4. uppercase conversion (std backend converter facet)
    std::locale lconv = gen("en_US.UTF-8");
    const std::string up = to_upper("hello world", lconv);
    if (up != "HELLO WORLD") {
        std::cerr << "to_upper failed: " << up << std::endl;
        return 1;
    }
    std::cout << "conversion: to_upper OK" << std::endl;

    // 5. collation (std backend collate facet)
    std::locale lcol = gen("en_US.UTF-8");
    const std::collate<char>& col = std::use_facet<std::collate<char>>(lcol);
    static const char kApple[] = "apple";
    static const char kBanana[] = "banana";
    if (col.compare(kApple, kApple + 5, kBanana, kBanana + 6) >= 0) {
        std::cerr << "collate compare failed" << std::endl;
        return 1;
    }
    std::cout << "collation: compare OK" << std::endl;

    // 6. formatting: as::number on classic-style locale
    {
        std::locale lfmt = gen("C");
        std::ostringstream ss;
        ss.imbue(lfmt);
        ss << as::number << std::fixed << std::setprecision(2) << 1045.45;
        if (ss.str() != "1045.45") {
            std::cerr << "number formatting failed: [" << ss.str() << "]" << std::endl;
            return 1;
        }
        std::cout << "formatting: as::number OK (" << ss.str() << ")" << std::endl;
    }

    // 7. format() string interpolation (shared/format.cpp)
    {
        std::locale lfmt = gen("C");
        std::string s = (format("{1} + {2} = {3}") % 2 % 3 % 5).str(lfmt);
        if (s != "2 + 3 = 5") {
            std::cerr << "format interpolation failed: [" << s << "]" << std::endl;
            return 1;
        }
        std::cout << "format: interpolation OK (" << s << ")" << std::endl;
    }

    // 8. date_time calendar (util/gregorian.cpp) — year arithmetic
    {
        std::locale lcal = gen("C");
        calendar cal(lcal);
        date_time now(cal);
        const int cur_year = now / period::year();
        date_time next_year = now + period::year();
        const int nxt_year = next_year / period::year();
        if (nxt_year != cur_year + 1) {
            std::cerr << "calendar year arithmetic failed: " << cur_year
                      << " -> " << nxt_year << std::endl;
            return 1;
        }
        std::cout << "date_time: calendar " << cur_year << " -> " << nxt_year << std::endl;
    }

    // 9. message translation fallback (mo_lambda/message path)
    {
        gnu_gettext::messages_info minfo;
        minfo.language = "en";
        minfo.encoding = "UTF-8";
        // callback_type is a std::function returning the raw .mo bytes;
        // returning an empty vector exercises the no-catalog fallback path
        minfo.callback = [](const std::string&, const std::string&) {
            return std::vector<char>();
        };
        std::locale lmsg(std::locale::classic(),
                         gnu_gettext::create_messages_facet<char>(minfo));
        std::locale lmsg2 = gen("C");
        // translate on a locale without the domain -> returns key unchanged
        const std::string t = translate("unchanged-key").str(lmsg2);
        if (t != "unchanged-key") {
            std::cerr << "message fallback failed: [" << t << "]" << std::endl;
            return 1;
        }
        std::cout << "message: fallback key OK" << std::endl;
    }

    std::cout << "boost1.84-locale smoke test PASSED" << std::endl;
    return 0;
}
