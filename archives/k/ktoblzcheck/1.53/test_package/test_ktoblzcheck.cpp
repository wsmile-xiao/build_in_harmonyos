// ktoblzcheck 库真实调用测试：
// 加载随包发布的 bankdata，用 AccountNumberCheck_findBank 查询库中真实
// 存在的银行（BLZ 10000000 = Deutsche Bundesbank），再调用
// AccountNumberCheck_check 执行一次真实的校验流程。
// 断言：银行必须存在（findBank 非空），且 check() 返回 0/1/2 之一
// （valid / unknown method / probably mismatch），不允许 3 (bank not found)。
#include <ktoblzcheck.h>

#include <cstdio>

int main(int argc, char** argv) {
    const char* bankdata = (argc > 1) ? argv[1] : "bankdata_20200420.txt";
    AccountNumberCheck* c = AccountNumberCheck_new_file(bankdata);
    if (c == nullptr) {
        std::fprintf(stderr, "ERROR: cannot load bankdata: %s\n", bankdata);
        return 1;
    }
    unsigned int banks = AccountNumberCheck_bankCount(c);
    std::printf("ktoblzcheck v%s encoding=%s banks=%u\n",
                AccountNumberCheck_libraryVersion(),
                AccountNumberCheck_stringEncoding(), banks);
    if (banks == 0) {
        std::fprintf(stderr, "ERROR: empty bank database\n");
        return 1;
    }
    // bankdata 首行：10000000 德意志联邦银行（必然在库中）
    const AccountNumberCheck_Record* rec =
        AccountNumberCheck_findBank(c, "10000000");
    if (rec == nullptr) {
        std::fprintf(stderr, "ERROR: expected bank 10000000 not found\n");
        return 1;
    }
    std::printf("bank found: %lu %s (%s)\n",
                AccountNumberCheck_Record_bankId(rec),
                AccountNumberCheck_Record_bankName(rec),
                AccountNumberCheck_Record_location(rec));
    // 真实校验流程：0=valid, 1=unknown method, 2=probably mismatch,
    // 3=bank not found（不允许）
    AccountNumberCheck_Result r = AccountNumberCheck_check(c, "10000000", "532013000");
    AccountNumberCheck_delete(c);
    if (r == 3) {
        std::fprintf(stderr, "ERROR: bank not found (result=3)\n");
        return 1;
    }
    std::printf("ktoblzcheck check() OK (result=%d)\n", (int)r);
    return 0;
}
