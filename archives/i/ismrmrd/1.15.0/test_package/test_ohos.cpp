/**
 * HarmonyOS-specific consumer test for ismrmrd 1.15.0 (test_package).
 *
 * Exercises the public C++ XML interchange API — the primary way MRI
 * applications exchange ISMRMRD headers — by building an IsmrmrdHeader through
 * the public struct API, serialising it, deserialising it back and comparing
 * the two headers. This is a business-meaningful end-to-end use of the library
 * as a downstream application would perform it, and is NOT part of the upstream
 * unit test suite.
 */
#include <iostream>
#include <sstream>
#include <string>

#include "ismrmrd/version.h"
#include "ismrmrd/xml.h"

using namespace ISMRMRD;

int main()
{
    IsmrmrdHeader h;
    // Serialisation round-trips require the schema version to match the
    // library's compiled-in XML header version.
    h.version = ISMRMRD_XMLHDR_VERSION;

    SubjectInformation subj;
    subj.patientName = "OHOS-Test-Patient";
    h.subjectInformation = subj;

    AcquisitionSystemInformation sys;
    sys.systemVendor = "HarmonyOS";
    sys.systemModel = "PC-aarch64";
    h.acquisitionSystemInformation = sys;

    h.experimentalConditions.H1resonanceFrequency_Hz = 123200000; // 2.89 T

    Encoding e;
    e.trajectory = TrajectoryType::CARTESIAN;
    e.encodedSpace.matrixSize = MatrixSize(256, 128, 1);
    e.encodedSpace.fieldOfView_mm.x = 256.0f;
    e.encodedSpace.fieldOfView_mm.y = 128.0f;
    e.encodedSpace.fieldOfView_mm.z = 1.0f;
    e.reconSpace.matrixSize = MatrixSize(256, 128, 1);
    e.reconSpace.fieldOfView_mm.x = 256.0f;
    e.reconSpace.fieldOfView_mm.y = 128.0f;
    e.reconSpace.fieldOfView_mm.z = 1.0f;
    e.encodingLimits.kspace_encoding_step_0 = Limit(0, 255, 128);
    e.encodingLimits.kspace_encoding_step_1 = Limit(0, 127, 64);
    h.encoding.push_back(e);

    // --- serialise ---
    std::ostringstream oss;
    serialize(h, oss);
    const std::string xml = oss.str();
    if (xml.empty()) {
        std::cerr << "FAIL: serialized XML is empty" << std::endl;
        return 1;
    }

    // --- deserialise and verify ---
    IsmrmrdHeader h2;
    deserialize(xml.c_str(), h2);

    bool ok = true;
    if (!h2.version || h2.version.get() != ISMRMRD_XMLHDR_VERSION) {
        std::cerr << "FAIL: version mismatch" << std::endl;
        ok = false;
    }
    if (!h2.subjectInformation || !h2.subjectInformation->patientName
        || h2.subjectInformation->patientName.get() != "OHOS-Test-Patient") {
        std::cerr << "FAIL: patientName mismatch" << std::endl;
        ok = false;
    }
    if (!h2.acquisitionSystemInformation || !h2.acquisitionSystemInformation->systemVendor
        || h2.acquisitionSystemInformation->systemVendor.get() != "HarmonyOS") {
        std::cerr << "FAIL: systemVendor mismatch" << std::endl;
        ok = false;
    }
    if (h2.experimentalConditions.H1resonanceFrequency_Hz != 123200000) {
        std::cerr << "FAIL: H1resonanceFrequency_Hz mismatch" << std::endl;
        ok = false;
    }
    if (h2.encoding.size() != 1) {
        std::cerr << "FAIL: encoding count mismatch" << std::endl;
        ok = false;
    } else {
        const Encoding &e2 = h2.encoding[0];
        if (e2.trajectory != TrajectoryType::CARTESIAN) {
            std::cerr << "FAIL: trajectory mismatch" << std::endl;
            ok = false;
        }
        if (e2.encodedSpace.matrixSize.x != 256 || e2.encodedSpace.matrixSize.y != 128) {
            std::cerr << "FAIL: encodedSpace matrixSize mismatch" << std::endl;
            ok = false;
        }
        if (!e2.encodingLimits.kspace_encoding_step_0
            || e2.encodingLimits.kspace_encoding_step_0->maximum != 255) {
            std::cerr << "FAIL: kspace_encoding_step_0 limit mismatch" << std::endl;
            ok = false;
        }
    }

    // Round-trip equality is the strongest available check.
    if (ok && h != h2) {
        std::cerr << "FAIL: header round-trip is not equal" << std::endl;
        ok = false;
    }

    if (!ok) {
        return 1;
    }
    std::cout << "ismrmrd OHOS C++ XML round-trip PASSED (" << xml.size()
              << " bytes XML)" << std::endl;
    return 0;
}
