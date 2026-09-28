// test_package 消费者验证：通过 miniscript-cpp 公开 API 运行一段 MiniScript
// 脚本并校验可观察输出（R34：必须实质调用被测包 API，禁止空壳打印）。
#include <MiniScript/MiniscriptInterpreter.h>
#include <MiniScript/MiniscriptTypes.h>
#include <cstdio>
#include <cstring>

using namespace MiniScript;

static String captured;

static void CaptureOutput(String text, bool addLineBreak) {
    captured = captured + text + (addLineBreak ? "\n" : "");
}

int main() {
    Interpreter interp;
    interp.standardOutput = CaptureOutput;

    // 公开 API：加载脚本、运行到结束、读取全局变量
    interp.Reset("x = 6 * 7\nprint \"answer is \" + x\n");
    interp.RunUntilDone();

    if (captured != "answer is 42\n") {
        fprintf(stderr, "FAIL: unexpected output: %s\n", captured.c_str());
        return 1;
    }

    // 校验全局变量可从宿主侧读取（Interpreter::GetGlobalValue）
    Value v = interp.GetGlobalValue("x");
    if (v.IntValue() != 42) {
        fprintf(stderr, "FAIL: x != 42\n");
        return 2;
    }

    printf("test miniscript 1.6.2 consumer: OK (output=%s, x=%d)\n",
           captured.c_str(), v.IntValue());
    return 0;
}
