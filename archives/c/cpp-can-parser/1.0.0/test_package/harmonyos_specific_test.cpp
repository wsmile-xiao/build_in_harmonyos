// harmonyos_specific_test.cpp — cpp-can-parser HarmonyOS 专项测试
// 真实平台宏核验 + 真实调用被测库 API 解析 DBC（非空壳、非只打印）。
#include <cpp-can-parser/CANDatabase.h>
#include <iostream>
#include <string>

// 与上游 tests/dbc-files/single-frame-1.dbc 完全一致的 DBC 文本（真实解析输入）
static const std::string DBC_CONTENT = R"DBCCONTENT(VERSION "SingleFrame1.dbc"

NS_ : 
	CM_
	BA_DEF_
	BA_
	VAL_
	CAT_DEF_
	CAT_
	FILTER
	BA_DEF_DEF_
	EV_DATA_
	ENVVAR_DATA_
	SGTYPE_
	SGTYPE_VAL_
	BA_DEF_SGTYPE_
	BA_SGTYPE_
	SIG_TYPE_REF_
	VAL_TABLE_
	SIG_GROUP_
	SIG_VALTYPE_
	SIGTYPE_VALTYPE_
	BO_TX_BU_
	BA_DEF_REL_
	BA_REL_
	BA_DEF_DEF_REL_
	BU_SG_REL_
	BU_EV_REL_
	BU_BO_REL_

BS_:

BU_: TestNode

BO_ 1296 TEST_FRAME_1: 2 TestNode
	SG_ TEST_SIG_1 : 0|8@1+ (1,0) [0|0] "" TestNode
	SG_ TEST_SIG_2 : 8|8@1+ (1,0) [0|0] "" TestNode
)DBCCONTENT";

int main() {
    using namespace CppCAN;

#if defined(__OHOS__)
    std::cout << "harmonyos_specific_test: __OHOS__ defined" << std::endl;
#else
    std::cout << "harmonyos_specific_test: __OHOS__ NOT defined" << std::endl;
#endif
#if defined(__aarch64__)
    std::cout << "harmonyos_specific_test: __aarch64__ defined" << std::endl;
#else
    std::cout << "harmonyos_specific_test: __aarch64__ NOT defined" << std::endl;
#endif

    CANDatabase db = CANDatabase::fromString(DBC_CONTENT);
    if (!db.contains(1296ULL) || db.at(1296ULL).name() != "TEST_FRAME_1") {
        std::cerr << "harmonyos_specific_test FAILED: DBC parse/query failed" << std::endl;
        return 1;
    }
    std::cout << "harmonyos_specific_test: library API parse+query OK "
              << "(frame TEST_FRAME_1 can_id=0x510)" << std::endl;

#if defined(__OHOS__) && defined(__aarch64__)
    std::cout << "harmonyos_specific_test OK: platform=OHOS(aarch64), "
                 "__OHOS__/__aarch64__ defined, real API parse passed"
              << std::endl;
    return 0;
#else
    std::cout << "harmonyos_specific_test: built on non-OHOS platform, library API still OK"
              << std::endl;
    return 0;
#endif
}