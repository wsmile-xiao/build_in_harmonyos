/**
 * HarmonyOS-specific test for ismrmrd 1.7.0.
 *
 * Exercises the public C++ API (IsmrmrdHeader XML serialization round-trip)
 * on the OHOS platform. This is a business-meaningful public API: the XML
 * interchange format is the primary way MRI applications exchange ismrmrd
 * headers. It is NOT part of the upstream unit test suite and complements:
 *   - test.c (consumer test, C API)
 *   - upstream tests/ (Boost.Test C API coverage)
 */
#include <sstream>
#include <string>
#include <iostream>
#include <cassert>
#include "ismrmrd/xml.h"

using namespace ISMRMRD;

int main() {
    // Build a header using the public struct API.
    // ISMRMRD_XMLHDR_VERSION is the schema version (= minor version 7 for
    // 1.7.0); serialize()/deserialize() reject any other value.
    IsmrmrdHeader h;
    h.version = 7;

    SubjectInformation subj;
    subj.patientName = "OHOS-Test-Patient";
    h.subjectInformation = subj;

    AcquisitionSystemInformation sys;
    sys.systemVendor = "HarmonyOS";
    sys.systemModel = "PC-aarch64";
    h.acquisitionSystemInformation = sys;

    Encoding e;
    e.trajectory = TrajectoryType::CARTESIAN;
    e.encodedSpace.matrixSize.x = 256;
    e.encodedSpace.matrixSize.y = 128;
    e.encodedSpace.matrixSize.z = 1;
    e.encodedSpace.fieldOfView_mm.x = 256.0f;
    e.encodedSpace.fieldOfView_mm.y = 128.0f;
    e.encodedSpace.fieldOfView_mm.z = 1.0f;
    e.reconSpace.matrixSize.x = 256;
    e.reconSpace.matrixSize.y = 128;
    e.reconSpace.matrixSize.z = 1;
    e.encodingLimits.kspace_encoding_step_0 = Limit(0, 255, 128);
    h.encoding.push_back(e);

    // Serialize to XML
    std::ostringstream oss;
    serialize(h, oss);
    std::string xml = oss.str();
    if (xml.empty()) {
        std::cerr << "FAIL: serialized XML is empty" << std::endl;
        return 1;
    }

    // Round-trip: deserialize and verify key fields
    IsmrmrdHeader h2;
    deserialize(xml.c_str(), h2);

    bool ok = true;
    if (!h2.version || *h2.version != 7) { std::cerr << "FAIL: version mismatch" << std::endl; ok = false; }
    if (!h2.subjectInformation || !h2.subjectInformation->patientName.has_value()
        || h2.subjectInformation->patientName.value() != "OHOS-Test-Patient") {
        std::cerr << "FAIL: patientName mismatch" << std::endl; ok = false;
    }
    if (!h2.acquisitionSystemInformation || !h2.acquisitionSystemInformation->systemVendor.has_value()
        || h2.acquisitionSystemInformation->systemVendor.value() != "HarmonyOS") {
        std::cerr << "FAIL: systemVendor mismatch" << std::endl; ok = false;
    }
    if (h2.encoding.size() != 1) { std::cerr << "FAIL: encoding count mismatch" << std::endl; ok = false; }
    if (h2.encoding.size() == 1) {
        const Encoding &e2 = h2.encoding[0];
        if (e2.trajectory != TrajectoryType::CARTESIAN) { std::cerr << "FAIL: trajectory mismatch" << std::endl; ok = false; }
        if (e2.encodedSpace.matrixSize.x != 256 || e2.encodedSpace.matrixSize.y != 128) {
            std::cerr << "FAIL: matrixSize mismatch" << std::endl; ok = false;
        }
        if (!e2.encodingLimits.kspace_encoding_step_0 || e2.encodingLimits.kspace_encoding_step_0->maximum != 255) {
            std::cerr << "FAIL: kspace limit mismatch" << std::endl; ok = false;
        }
    }

    if (ok) {
        std::cout << "ismrmrd OHOS C++ XML round-trip PASSED (" << xml.size() << " bytes XML)" << std::endl;
        return 0;
    }
    return 1;
}