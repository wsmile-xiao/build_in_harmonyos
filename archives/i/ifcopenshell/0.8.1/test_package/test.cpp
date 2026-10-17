// test_ifcopenshell — L1 consumer test (R34: substantively exercises the library)
// Uses the installed IfcParse API to parse a minimal IFC4 STEP file.
#include <iostream>
#include <sstream>
#include <string>

#include "ifcparse/IfcParse.h"
#include "ifcparse/IfcFile.h"

int main() {
    // A minimal IFC4 file with one IfcProject entity.
    const std::string step =
        "ISO-10303-21;\n"
        "HEADER;\n"
        "FILE_DESCRIPTION((''),'2;1');\n"
        "FILE_NAME('test.ifc','2026-01-01T00:00:00',('tester'),('org'),'','','');\n"
        "FILE_SCHEMA(('IFC4'));\n"
        "ENDSEC;\n"
        "DATA;\n"
        "#1=IFCPROJECT('3Mw6pDqb52ExmpG4gH1mQ2',#2,'Test Project',"
        "'A minimal IFC4 project used for the ifcopenshell smoke test.',"
        "$,$,$,$,$);\n"
        "#2=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$, $, $, 0);\n"
        "#3=IFCPERSON($,'tester',$,$,$,$,$,$);\n"
        "#4=IFCORGANIZATION($,'org',$,$,$);\n"
        "ENDSEC;\n"
        "END-ISO-10303-21;\n";

    try {
        std::stringstream ss(step);
        IfcParse::IfcFile file(ss, static_cast<int>(step.size()));

        if (!file.good()) {
            std::cerr << "FAIL: file_open_status not good after parse" << std::endl;
            return 1;
        }

        // Count parsed instances by iterating the file.
        size_t count = 0;
        for (auto it = file.begin(); it != file.end(); ++it) {
            ++count;
        }
        std::cout << "ifcopenshell parse OK: entities=" << count << std::endl;

        // Look up the IfcProject instance by GUID.
        auto project = file.instance_by_guid("3Mw6pDqb52ExmpG4gH1mQ2");
        if (!project) {
            std::cerr << "FAIL: instance_by_guid did not find IfcProject" << std::endl;
            return 1;
        }
        std::cout << "ifcopenshell lookup OK: found project instance" << std::endl;
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: exception while parsing: " << e.what() << std::endl;
        return 1;
    }
}