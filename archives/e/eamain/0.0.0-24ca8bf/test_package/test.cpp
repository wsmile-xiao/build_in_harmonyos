///////////////////////////////////////////////////////////////////////////////
// test_package 消费者测试 — 通过 EAMain 已安装/导出的公开头文件与库，
// 验证第三方使用者能编译、链接、调用并正常运行 EAMain 公开 API：
//   - EA::EAMain::CommandLine 命令行解析（Argc/Arg/FindSwitch）
//   - EA::EAMain::Report 报告输出
//   - EA::EAMain::PlatformStartup / PlatformShutdown
///////////////////////////////////////////////////////////////////////////////
#include <EAMain/EAMain.h>

#include <stdio.h>
#include <string.h>

int main()
{
    int nErrors = 0;

    EA::EAMain::PlatformStartup();

    EA::EAMain::Report("test_eamain: Report() ok\n");

    {
        const char* commandLineString = "consumer.elf -mode:release -verbose";
        EA::EAMain::CommandLine cmdLine(commandLineString);

        if(cmdLine.Argc() != 3)
        {
            printf("test_eamain FAIL: Argc=%d expect 3\n", cmdLine.Argc());
            ++nErrors;
        }

        const char* pParam = NULL;
        const int idx = cmdLine.FindSwitch("-mode", false, &pParam);
        if(idx != 1 || pParam == NULL || strcmp(pParam, "release") != 0)
        {
            printf("test_eamain FAIL: FindSwitch(-mode)\n");
            ++nErrors;
        }

        if(cmdLine.FindSwitch("-verbose") != 2)
        {
            printf("test_eamain FAIL: FindSwitch(-verbose)\n");
            ++nErrors;
        }
    }

    EA::EAMain::PlatformShutdown(nErrors);

    if(nErrors == 0)
    {
        printf("test_eamain: PASS\n");
        return 0;
    }

    printf("test_eamain: FAIL (%d errors)\n", nErrors);
    return 1;
}
