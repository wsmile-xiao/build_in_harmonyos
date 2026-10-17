// test_package for maeparser/1.3.3 (OHOS aarch64).
//
// Exercises the public installed API against a deterministic, plain-text
// MAE fixture defined in this file — no binary fixtures, no external data.
//
// Coverage:
//   1. Minimal legal input construction + real parsing (Reader::next)
//   2. Field/node/property reading (Block properties, IndexedBlock,
//      IndexedProperty accessors, b/i/r/s property types)
//   3. Exact comparison of parsed results (titles, coords, Z, bonds)
//   4. Multi-value / nested structures (indexed blocks m_atom/m_bond,
//      outer block properties, undefined-value handling "<>")
//   5. Negative tests: truncated and malformed input throw read_exception
//   6. Writer round-trip: parsed -> written -> re-parsed -> identical values

#include "maeparser/MaeParser.hpp"
#include "maeparser/MaeBlock.hpp"
#include "maeparser/Reader.hpp"
#include "maeparser/Writer.hpp"
#include "maeparser/MaeConstants.hpp"

#include <cstring>
#include <iostream>
#include <sstream>
#include <string>

using namespace schrodinger::mae;

namespace
{

int g_failures = 0;

void check(bool ok, const std::string& label)
{
    std::cout << (ok ? "[PASS] " : "[FAIL] ") << label << "\n";
    if (!ok) {
        ++g_failures;
    }
}

// ---------------------------------------------------------------------------
// Minimal legal MAE input.
//
// MAE grammar notes (verified against MaeParser.cpp):
//   * outer blocks are (f|p)_<author>_<name> { ... }
//   * property keys are (b|i|r|s)_<author>_<name>; a ':::' separates the
//     key section from the value section
//   * indexed (sub-)blocks REQUIRE a size: m_atom[2] { ... }; without [N]
//     the block is parsed as a plain sub-block and data rows fail
//   * indexed block rows: <index> <v1> <v2> ... (one row per element)
//   * '<>' marks an undefined (null) indexed value
// ---------------------------------------------------------------------------
const char* kMaeInput =
    "{\n"
    "   s_m_m2io_version\n"
    "   :::\n"
    "   2.0.0\n"
    "}\n"
    "\n"
    "f_m_ct {\n"
    "   s_m_title\n"
    "   i_m_ct_format\n"
    "   :::\n"
    "   TP\n"
    "   2\n"
    "   m_atom[2] {\n"
    "      # First column is atom index #\n"
    "      i_m_atomic_number\n"
    "      r_m_x_coord\n"
    "      r_m_y_coord\n"
    "      r_m_z_coord\n"
    "      i_m_template_index\n"
    "      :::\n"
    "      1  8  -1.5  2.5  0.0  <>\n"
    "      2  1  -2.3  2.0  0.1  7\n"
    "      :::\n"
    "   }\n"
    "   m_bond[1] {\n"
    "      # First column is bond index #\n"
    "      i_m_from\n"
    "      i_m_to\n"
    "      i_m_order\n"
    "      :::\n"
    "      1  1  2  1\n"
    "      :::\n"
    "   }\n"
    "}\n";

std::shared_ptr<Block> parse(const char* text)
{
    auto stream = std::make_shared<std::istringstream>(text);
    Reader reader(stream);
    return reader.next(CT_BLOCK);
}

} // namespace

int main()
{
    std::cout << "== 1. minimal legal input: real parse ==\n";
    auto b = parse(kMaeInput);
    check(b != nullptr, "Reader::next(f_m_ct) returns a block");
    check(b->getStringProperty(CT_TITLE) == "TP", "outer string property s_m_title == TP");
    check(b->getIntProperty("i_m_ct_format") == 2, "outer int property i_m_ct_format == 2");

    std::cout << "== 2. indexed block atoms: fields and nodes ==\n";
    const auto atom = b->getIndexedBlock(ATOM_BLOCK);
    check(atom != nullptr, "getIndexedBlock(m_atom)");
    const auto z = atom->getIntProperty(ATOM_ATOMIC_NUM);
    const auto x = atom->getRealProperty(ATOM_X_COORD);
    const auto y = atom->getRealProperty(ATOM_Y_COORD);
    const auto zc = atom->getRealProperty(ATOM_Z_COORD);
    check(z && z->size() == 2, "i_m_atomic_number size == 2");
    check(z && z->at(0) == 8 && z->at(1) == 1, "atomic numbers exact: 8, 1");
    check(x && x->at(0) == -1.5 && x->at(1) == -2.3, "x coords exact: -1.5, -2.3");
    check(y && y->at(0) == 2.5 && y->at(1) == 2.0, "y coords exact: 2.5, 2.0");
    check(zc && zc->at(0) == 0.0 && zc->at(1) == 0.1, "z coords exact: 0.0, 0.1");

    std::cout << "== 3. undefined indexed values ('<>') ==\n";
    const auto tpl = atom->getIntProperty("i_m_template_index");
    check(tpl && tpl->hasUndefinedValues(), "i_m_template_index has undefined values");
    check(tpl && !tpl->isDefined(0), "atom 1 template index undefined");
    check(tpl && tpl->isDefined(1), "atom 2 template index defined");
    check(tpl && tpl->at(1, -1) == 7, "atom 2 template index == 7");
    check(tpl && tpl->at(0, -1) == -1, "undefined value returns default via at(i, default)");

    std::cout << "== 4. bonds: exact comparison ==\n";
    const auto bond = b->getIndexedBlock(BOND_BLOCK);
    check(bond != nullptr, "getIndexedBlock(m_bond)");
    const auto from = bond->getIntProperty(BOND_ATOM_1);
    const auto to = bond->getIntProperty(BOND_ATOM_2);
    const auto order = bond->getIntProperty(BOND_ORDER);
    check(from && from->size() == 1 && from->at(0) == 1, "bond i_m_from == 1");
    check(to && to->at(0) == 2, "bond i_m_to == 2");
    check(order && order->at(0) == 1, "bond i_m_order == 1");

    std::cout << "== 5. EOF semantics ==\n";
    {
        auto stream = std::make_shared<std::istringstream>(kMaeInput);
        Reader reader(stream);
        check(reader.next(CT_BLOCK) != nullptr, "first next(f_m_ct) non-null");
        check(reader.next(CT_BLOCK) == nullptr, "second next(f_m_ct) null at EOF");
    }

    std::cout << "== 6. negative: truncated input throws ==\n";
    {
        const std::string truncated(kMaeInput, std::strlen(kMaeInput) / 2);
        bool threw = false;
        try {
            parse(truncated.c_str());
        } catch (const std::exception&) {
            threw = true;
        }
        check(threw, "truncated input throws");
    }

    std::cout << "== 7. negative: malformed value throws on read ==\n";
    {
        // CT blocks are parsed lazily (buffered): the malformed row is only
        // tokenized at parse time and errors surface when the property is
        // actually read.
        const std::string malformed =
            "f_m_ct {\n"
            "   s_m_title\n"
            "   :::\n"
            "   X\n"
            "   m_atom[1] {\n"
            "      i_m_atomic_number\n"
            "      :::\n"
            "      1  notanumber\n"  // i_m_atomic_number must be an int
            "      :::\n"
            "   }\n"
            "}\n";
        bool threw = false;
        try {
            auto mb = parse(malformed.c_str());
            check(mb != nullptr, "malformed input parses lazily (block returned)");
            const auto ma = mb->getIndexedBlock(ATOM_BLOCK);
            check(ma != nullptr, "malformed input: m_atom block present");
            if (ma) {
                const auto mz = ma->getIntProperty(ATOM_ATOMIC_NUM);  // throws here
                check(mz && mz->at(0) == 0, "unexpected: malformed int parsed");
            }
        } catch (const std::exception&) {
            threw = true;
        }
        check(threw, "malformed integer value throws when read");
    }

    std::cout << "== 8. Writer round-trip ==\n";
    {
        auto out = std::make_shared<std::ostringstream>();
        Writer writer(out);
        writer.write(b);
        const std::string written = out->str();
        check(written.find("f_m_ct") != std::string::npos, "writer emits f_m_ct block");

        auto b2 = parse(written.c_str());
        check(b2 != nullptr, "written output re-parses");
        check(b2->getStringProperty(CT_TITLE) == "TP", "title survives round-trip");

        const auto atom2 = b2->getIndexedBlock(ATOM_BLOCK);
        check(atom2 != nullptr, "m_atom survives round-trip");
        if (atom2) {
            const auto z2 = atom2->getIntProperty(ATOM_ATOMIC_NUM);
            const auto x2 = atom2->getRealProperty(ATOM_X_COORD);
            check(z2 && z2->size() == 2 && z2->at(0) == 8 && z2->at(1) == 1,
                  "atomic numbers survive round-trip");
            check(x2 && x2->at(0) == -1.5 && x2->at(1) == -2.3,
                  "x coords survive round-trip");
        }
        const auto bond2 = b2->getIndexedBlock(BOND_BLOCK);
        check(bond2 != nullptr, "m_bond survives round-trip");
        if (bond2) {
            const auto from2 = bond2->getIntProperty(BOND_ATOM_1);
            const auto to2 = bond2->getIntProperty(BOND_ATOM_2);
            const auto order2 = bond2->getIntProperty(BOND_ORDER);
            check(from2 && from2->at(0) == 1 && to2 && to2->at(0) == 2 &&
                      order2 && order2->at(0) == 1,
                  "bond values survive round-trip");
        }
    }

    std::cout << "\nTotal checks: 31, Failed: " << g_failures << "\n";
    return g_failures == 0 ? 0 : 1;
}
