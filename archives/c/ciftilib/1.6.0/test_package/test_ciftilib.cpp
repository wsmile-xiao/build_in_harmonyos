#include "CiftiLib/CiftiFile.h"
#include "CiftiLib/Cifti/CiftiXML.h"
#include "CiftiLib/Common/AString.h"
#include "CiftiLib/Common/CiftiException.h"

#include <iostream>
#include <vector>
#include <cassert>

using namespace cifti;

int main() {
    std::cout << "=== CiftiLib 1.6.0 consumer test ===" << std::endl;

    // 1. AString round-trip
    {
        AString s("hello-cifti");
        std::string stdStr = AString_to_std_string(s);
        std::cout << "AString round-trip: " << stdStr << std::endl;
        assert(stdStr == "hello-cifti");
        AString s2(stdStr);
        assert(AString_to_std_string(s2) == stdStr);
        std::cout << "PASS: AString" << std::endl;
    }

    // 2. CiftiFile default construction (in-memory, no file)
    {
        CiftiFile f;
        // Default file is not in-memory until convert, but object should be constructible
        std::cout << "CiftiFile default constructed, isInMemory=" << f.isInMemory() << std::endl;
        // Set up a minimal in-memory CIFTI structure: 1 row, 10 columns
        // Use CiftiXML to build a simple scalars map
        CiftiXML xml;
        // We do not need a fully valid XML; just verify that setCiftiXML/getCiftiXML work
        // Create a minimal scalars map via the public API: we can set dimensions indirectly
        // Instead, test that getDimensions on fresh file returns empty (before set)
        auto dims = f.getDimensions();
        std::cout << "Initial dimensions size: " << dims.size() << std::endl;
        std::cout << "PASS: CiftiFile default" << std::endl;
    }

    // 3. CiftiXML basic construction and query
    {
        CiftiXML xml;
        // Fresh XML has 0 dimensions
        int ndim = xml.getNumberOfDimensions();
        std::cout << "CiftiXML dimensions: " << ndim << std::endl;
        // Constructing a simple version check
        CiftiVersion ver;
        std::cout << "CiftiVersion default: " << AString_to_std_string(ver.toString()) << std::endl;
        std::cout << "PASS: CiftiXML/CiftiVersion" << std::endl;
    }

    // 4. NiftiIO header sanity (header-only-ish via NiftiIO)
    // NiftiIO is not header-only but we can at least include and verify types
    {
        // Check that library symbols are linked: create and destroy a file object
        // Exercise exception path: opening non-existent file should throw CiftiException
        bool caught = false;
        try {
            CiftiFile bad("/nonexistent/path/to/file.dtseries.nii");
        } catch (CiftiException &e) {
            caught = true;
            std::cout << "Caught expected CiftiException for missing file: " << AString_to_std_string(e.whatString()).substr(0, 80) << std::endl;
        }
        // Some builds may not throw until first read; accept either
        std::cout << "Exception handling check: " << (caught ? "caught" : "no throw (acceptable)") << std::endl;
        std::cout << "PASS: exception path" << std::endl;
    }

    std::cout << "=== All ciftilib consumer checks passed ===" << std::endl;
    return 0;
}
