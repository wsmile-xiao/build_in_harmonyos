// SPDX-License-Identifier: BSD-2-Clause
// Test package for libcifpp - tests actual API usage (R34 compliant)

#include <cif++.hpp>

#include <sstream>
#include <iostream>
#include <string>

int main()
{
    // Create a simple mmCIF data string
    std::string mmcif_data = R"(data_test
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
ATOM   1 N 1.0 2.0 3.0
ATOM   2 C 4.0 5.0 6.0
)";

    // Parse the mmCIF data using libcifpp API
    std::istringstream is(mmcif_data);
    cif::file f;
    f.load(is);

    // Verify we have at least one datablock
    if (f.empty())
    {
        std::cerr << "Error: no datablock found" << std::endl;
        return 1;
    }

    // Access the first datablock
    auto &db = f.front();

    // Access a category by name (without underscore prefix)
    auto &cat = db["atom_site"];

    // Verify category has data
    if (cat.empty())
    {
        std::cerr << "Error: atom_site category is empty" << std::endl;
        return 1;
    }

    // Check the number of rows
    std::cout << "Number of atom sites: " << cat.size() << std::endl;
    if (cat.size() != 2)
    {
        std::cerr << "Error: expected 2 atom sites, got " << cat.size() << std::endl;
        return 1;
    }

    // Access data in the first row
    auto row = cat.front();
    auto symbol = row["type_symbol"].as<std::string>();
    std::cout << "First atom type: " << symbol << std::endl;
    if (symbol != "N")
    {
        std::cerr << "Error: expected 'N', got '" << symbol << "'" << std::endl;
        return 1;
    }

    std::cout << "All tests passed!" << std::endl;
    return 0;
}
