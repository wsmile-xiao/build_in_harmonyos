// test_consumer.cpp — cpp-can-parser 消费者验证（真实调用库 API 并断言）
#include <cpp-can-parser/CANDatabase.h>
#include <iostream>
#include <string>

// 与上游 tests/dbc-files/single-frame-1.dbc 完全一致的 DBC 文本（真实解析输入，
// 上游 cpc-test-parsing 已证明可被库解析）
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
    int failures = 0;

    CANDatabase db = CANDatabase::fromString(DBC_CONTENT);

    if (db.contains(1296ULL)) {
        std::cout << "consumer_check: frame 1296 present (can_id=0x510)" << std::endl;
    } else {
        std::cerr << "consumer_check FAILED: frame 1296 missing" << std::endl;
        ++failures;
    }

    const CANFrame& frame = db.at(1296ULL);
    std::cout << "consumer_check: frame name=\"" << frame.name()
              << "\" dlc=" << frame.dlc() << " signal_count=" << frame.size()
              << std::endl;
    if (frame.name() != "TEST_FRAME_1" || frame.dlc() != 2 || frame.size() != 2) {
        std::cerr << "consumer_check FAILED: frame attributes mismatch" << std::endl;
        ++failures;
    }

    if (db.contains("TEST_FRAME_1")) {
        std::cout << "consumer_check: frame lookup by name works" << std::endl;
    } else {
        std::cerr << "consumer_check FAILED: lookup by name failed" << std::endl;
        ++failures;
    }

    if (failures == 0) {
        std::cout << "consumer_check: ALL PASSED" << std::endl;
        return 0;
    }
    std::cout << "consumer_check: FAILURES=" << failures << std::endl;
    return 1;
}