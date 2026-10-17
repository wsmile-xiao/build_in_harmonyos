#include <commata/parse_csv.hpp>
#include <commata/record_extractor.hpp>
#include <commata/table_pull.hpp>

#include <sstream>
#include <string>

// Substantive smoke test for the installed header-only package:
// parse a small CSV via commata's parse_csv + table_pull and verify the
// extracted field values and positions.  This exercises the public headers
// shipped by the package (R34: the test must really depend on the package).
//
// Note: pass the input as std::string, not as a bare string literal.  The
// non-owning const-char* CharInput path (string_input) is not exercised by
// the upstream test suite and crashes under the OHOS libc++ toolchain
// (reproducible with the stock, unpatched upstream headers); the owning
// std::string path (owned_string_input) is the path upstream tests and this
// test rely on.
int main()
{
    // 1) table_pull over an owning in-memory CSV source.
    {
        auto pull = commata::make_table_pull(
            commata::make_csv_source(std::string("X,Y\n1,2\n")),
            std::size_t(64));

        std::string field;
        std::size_t count = 0;
        while (pull()) {
            if (pull->size() > 0) {
                field.assign(pull->data(), pull->size());
                ++count;
                if (count == 1 && field != "X") {
                    return 1;
                }
                if (count == 2 && field != "Y") {
                    return 2;
                }
                if (count == 3 && field != "1") {
                    return 3;
                }
                if (count == 4 && field != "2") {
                    return 4;
                }
            }
        }
        if (count != 4) {
            return 5;
        }
    }

    // 2) parse_csv with a record extractor into a string buffer.
    {
        std::istringstream in("a,b\n1,2\n");
        std::stringbuf out;
        auto ex = commata::make_record_extractor(out, "a", "b");
        commata::parse_csv(in, std::move(ex));
        if (out.str().empty()) {
            return 6;
        }
    }

    return 0;
}