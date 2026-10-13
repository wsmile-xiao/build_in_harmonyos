// openbabel 消费者测试：SMILES→InChI 转换硬断言
// 覆盖被测包核心链路：OBConversion 实例化 → 格式插件 dlopen + 注册表查找
// (smi/inchi) → 分子解析 → InChI 生成（经 libinchi）→ 输出断言
#include <openbabel/obconversion.h>
#include <openbabel/mol.h>
#include <iostream>
#include <string>

using namespace OpenBabel;

static int failures = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (!(cond)) {                                                \
            std::cerr << "FAIL: " << msg << std::endl;                \
            ++failures;                                               \
        } else {                                                      \
            std::cout << "ok: " << msg << std::endl;                  \
        }                                                             \
    } while (0)

int main()
{
    OBConversion conv;
    OBMol mol;

    CHECK(conv.SetInAndOutFormats("smi", "inchi"),
          "SetInAndOutFormats(smi, inchi)（插件加载 + 注册表查找）");
    if (failures) {
        return 1;
    }

    CHECK(conv.ReadString(&mol, "CCO"), "ReadString(CCO)（SMILES 解析）");

    std::string result = conv.WriteString(&mol, true);
    CHECK(!result.empty(), "WriteString 产出非空（InChI 生成，经 libinchi）");
    CHECK(result.find("InChI=1S/C2H6O") != std::string::npos,
          "乙醇 InChI 含 InChI=1S/C2H6O");
    if (!result.empty()) {
        std::cout << "InChI: " << result << std::endl;
    }

    if (failures) {
        std::cerr << "test_package: " << failures << " 项断言失败" << std::endl;
        return 1;
    }
    std::cout << "test_package: 全部断言通过" << std::endl;
    return 0;
}
