/*
 * dbus-cxx 2.5.1 消费者测试（test_package）——真实调用上游公开 API：
 *   - DBus::Path（继承 std::string）构造/校验/分解/追加
 *   - DBus::Signature 构造/校验
 *   - DBus::CallMessage::create + MessageAppendIterator 追加参数（编组链）
 *   - DBus::Validator 总线名校验
 *   - 错误路径：非法路径/非法签名 is_valid()==false 断言
 * 断言失败即非零退出；全部通过打印 consumer test: PASS。
 */
#include <dbus-cxx.h>
#include <dbus-cxx/path.h>
#include <dbus-cxx/signature.h>
#include <dbus-cxx/validator.h>
#include <iostream>
#include <string>

int main()
{
    // ---- DBus::Path：构造 + 校验 + 分解 + 追加 ----
    DBus::Path p("/org/example");
    if (!p.is_valid()) { std::cerr << "FAIL: valid path rejected\n"; return 1; }

    DBus::Path bad("no-leading-slash");
    if (bad.is_valid()) { std::cerr << "FAIL: invalid path accepted\n"; return 1; }
    std::cout << "ok: path valid/invalid checks\n";

    std::vector<std::string> parts = p.decomposed();
    if (parts.size() != 2 || parts[0] != "org" || parts[1] != "example") {
        std::cerr << "FAIL: path decompose\n"; return 1;
    }
    std::cout << "ok: path decompose (" << parts.size() << " elements)\n";

    p.append_element("child");
    if (p != "/org/example/child") {
        std::cerr << "FAIL: append_element -> " << p << "\n"; return 1;
    }
    std::cout << "ok: append_element -> " << p << "\n";

    // ---- DBus::Signature ----
    DBus::Signature sig("is");
    if (!sig.is_valid()) { std::cerr << "FAIL: valid signature rejected\n"; return 1; }
    DBus::Signature badsig("xx");
    if (badsig.is_valid()) { std::cerr << "FAIL: invalid signature accepted\n"; return 1; }
    std::cout << "ok: signature valid/invalid checks\n";

    // ---- CallMessage + MessageAppendIterator（编组链）----
    std::shared_ptr<DBus::CallMessage> msg = DBus::CallMessage::create(
        "/org/example", "org.example.If", "Method");
    if (!msg) { std::cerr << "FAIL: CallMessage::create\n"; return 1; }
    DBus::MessageAppendIterator iter(msg);
    iter << int32_t(42) << std::string("consumer");
    if (msg->signature().str() != "is") {
        std::cerr << "FAIL: signature after append = " << msg->signature().str() << "\n";
        return 1;
    }
    std::cout << "ok: callmessage create+append (signature=" << msg->signature().str() << ")\n";

    // ---- Validator ----
    if (!DBus::Validator::validate_bus_name("org.example.service")) {
        std::cerr << "FAIL: valid bus name rejected\n"; return 1;
    }
    if (DBus::Validator::validate_bus_name("-invalid-")) {
        std::cerr << "FAIL: invalid bus name accepted\n"; return 1;
    }
    std::cout << "ok: validator bus name checks\n";

    std::cout << "consumer test: PASS\n";
    return 0;
}
