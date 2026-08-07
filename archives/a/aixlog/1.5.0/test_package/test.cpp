/* test_package/test.cpp — aixlog 消费者测试
   验证可包含 aixlog.hpp 并调用 AixLog::Log::init + LOG 宏记录日志。
   上游无独立测试套件（仅 example），本测试为补充消费者测试。
*/
#include <aixlog.hpp>
#include <cstdio>

int main() {
    // 初始化日志：SinkCout 写 std::clog（无需终端）
    AixLog::Log::init<AixLog::SinkCout>(AixLog::Severity::trace);

    // LOG 宏记录 debug/info/warning/error 级别日志。
    // severity 用大写枚举（aixlog.hpp 第 85 行 LOG 宏定义：
    // static_cast<AixLog::Severity>(SEVERITY_)，enum SEVERITY 有
    // 大写 DEBUG/INFO/WARNING/ERROR 可转；小写 error 与
    // std::codecvt_base::error 冲突编译失败，实测 RC=1）。
    LOG(DEBUG) << "debug msg 42";
    LOG(INFO) << "info msg";
    LOG(WARNING) << "warn msg";
    LOG(ERROR) << "error msg";

    // 到达此处说明 init + LOG 宏正常编译链接运行（未崩溃）
    printf("aixlog smoke test: PASS (init + LOG macro OK)\n");
    return 0;
}
