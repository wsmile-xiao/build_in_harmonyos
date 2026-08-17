#include "dcmdata/dcfilefo.h"
#include "dcmdata/dcuid.h"
#include "dcmdata/dcdeftag.h"
#include <iostream>

int main(int argc, char *argv[])
{
    char uid[100];
    unsigned char data[256];
    for (unsigned i = 0; i < sizeof(data); ++i) {
        data[i] = i;
    }

    DcmFileFormat fileformat;
    DcmDataset *dataset = fileformat.getDataset();
    dataset->putAndInsertString(DCM_SOPClassUID, UID_SecondaryCaptureImageStorage);
    dataset->putAndInsertString(DCM_SOPInstanceUID, dcmGenerateUniqueIdentifier(uid, SITE_INSTANCE_UID_ROOT));
    dataset->putAndInsertString(DCM_PatientName, "Doe^John");
    dataset->putAndInsertUint8Array(DCM_PixelData, data, sizeof(data));
    OFCondition status = fileformat.saveFile("test.dcm", EXS_LittleEndianExplicit);
    if (status.bad()) {
        std::cerr << "Error: cannot write DICOM file (" << status.text() << ")\n";
        return 1;
    }

    // Read it back and verify
    DcmFileFormat readback;
    status = readback.loadFile("test.dcm");
    if (status.bad()) {
        std::cerr << "Error: cannot read back DICOM file (" << status.text() << ")\n";
        return 2;
    }
    OFString patientName;
    readback.getDataset()->findAndGetOFString(DCM_PatientName, patientName);
    if (patientName != "Doe^John") {
        std::cerr << "Error: patient name mismatch: " << patientName << "\n";
        return 3;
    }

    // Negative assertion: loading a non-existent file must fail
    DcmFileFormat missing;
    OFCondition missingStatus = missing.loadFile("nonexistent.dcm");
    if (missingStatus.good()) {
        std::cerr << "Error: loading nonexistent file should fail\n";
        return 4;
    }

    std::cout << "test_package: PASS - DICOM file created, read back, patient name verified\n";
    return 0;
}
