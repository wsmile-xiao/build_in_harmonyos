#include <cstdio>
#include <cstring>
#include <string>

#include "gdcmReader.h"
#include "gdcmWriter.h"
#include "gdcmDataSet.h"
#include "gdcmElement.h"
#include "gdcmTag.h"
#include "gdcmGlobal.h"
#include "gdcmDicts.h"
#include "gdcmDict.h"
#include "gdcmAttribute.h"
#include "gdcmVersion.h"

int main() {
    // 1) 版本信息
    printf("GDCM version: %s\n", gdcm::Version::GetVersion());

    // 2) 核心字典能力：通过公共 Dicts 查询 Transfer Syntax UID 标签
    const gdcm::Global &g = gdcm::Global::GetInstance();
    const gdcm::Dicts &dicts = g.GetDicts();
    const gdcm::Tag tsuid(0x0002, 0x0010);
    const gdcm::DictEntry &entry = dicts.GetDictEntry(tsuid);
    std::string name = entry.GetName();
    if (name.empty()) {
        fprintf(stderr, "FAIL: DictEntry for TransferSyntaxUID (0002,0010) is empty\n");
        return 1;
    }
    printf("Dict lookup (0002,0010) => %s\n", name.c_str());

    // 3) Attribute 强类型访问：构造 Media Storage SOP Class UID (0008,0016)
    gdcm::Attribute<0x0008, 0x0016> sopclass;
    sopclass.SetValue("1.2.840.10008.5.1.4.1.1.7");  // Secondary Capture Image Storage
    if (strncmp(sopclass.GetValue().c_str(), "1.2.840.10008", 13) != 0) {
        fprintf(stderr, "FAIL: Attribute<0008,0016> roundtrip (got %s)\n", sopclass.GetValue().c_str());
        return 1;
    }
    printf("Attribute SOPClassUID roundtrip OK\n");

    // 4) Element VR 语义：group/element 组合
    gdcm::Tag t2(0x7fe0, 0x0010);  // Pixel Data
    if (t2.GetElement() != 0x0010 || t2.GetGroup() != 0x7fe0) {
        fprintf(stderr, "FAIL: Tag composition\n");
        return 1;
    }
    const gdcm::DictEntry &pdEntry = dicts.GetDictEntry(t2);
    if (std::string(pdEntry.GetName()).empty()) {
        fprintf(stderr, "FAIL: PixelData dict entry empty\n");
        return 1;
    }
    printf("PixelData (%s) dict entry OK\n", pdEntry.GetName());

    // 5) Reader/Writer/DataSet 链接（不实际打开文件——无 DICOM 样本时最小链接验证）
    gdcm::Reader reader;
    if (reader.GetFile().GetDataSet().IsEmpty()) {
        printf("Reader/Writer/DataSet linkage OK (empty dataset as expected)\n");
    }

    printf("gdcm test_package: ALL OK\n");
    return 0;
}
