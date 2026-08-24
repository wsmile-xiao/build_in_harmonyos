/* test_package/test.cpp — bogofilter 1.2.5 consumer test (R34)
 *
 * 真正调用包内二进制做端到端贝叶斯验证（非空壳）：
 *   1) bogofilter -n 训练 ham 词库（meeting/thanks），断言退出码 0
 *   2) bogofilter -s 训练 spam 词库（viagra/casino），断言退出码 0
 *   3) bogofilter -p 分类 spam 特征邮件，断言输出含 "X-Bogosity: Spam"
 *      （-p 是分类模式输出 X-Bogosity 分类行；-s 是登记模式不分类。
 *      分类器损坏/分类逻辑回归时该断言失败——真实覆盖分类功能）
 * 任一步骤失败返回非 0，使"测试通过"可捕获回归。
 *
 * 用法: test_bogofilter <bogofilter路径> <词库路径>
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/wait.h>
#include <unistd.h>

/* 运行命令并返回子进程退出码（-1 = system 失败） */
static int run(const std::string & cmd) {
    int rc = system(cmd.c_str());
    if (rc == -1) {
        printf("[FAIL] system() failed: %s\n", cmd.c_str());
        return -1;
    }
    if (WIFEXITED(rc))
        return WEXITSTATUS(rc);
    return 1;
}

/* 运行命令并用 popen 捕获 stdout 输出（避免 /tmp 只读，鸿蒙安全框架
 * 拦截 mkstemp 写 /tmp——用管道读取无需临时文件） */
static int run_capture(const std::string & cmd, std::string & out) {
    FILE * fp = popen(cmd.c_str(), "r");
    if (!fp) {
        printf("[FAIL] popen() failed: %s\n", cmd.c_str());
        return -1;
    }
    char buf[1024];
    while (fgets(buf, sizeof(buf), fp))
        out += buf;
    int rc = pclose(fp);
    if (WIFEXITED(rc))
        return WEXITSTATUS(rc);
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        printf("[FAIL] usage: test_bogofilter <bogofilter> <wordlist.db>\n");
        return 1;
    }
    const char * bogofilter = argv[1];
    const char * bd = argv[2];

    /* 1) 训练 ham（-n register-ham）*/
    std::string train_ham =
        std::string("printf 'meeting\\nthanks\\n' | '") + bogofilter + "' -d '" + bd + "' -n";
    int rc = run(train_ham);
    if (rc != 0) {
        printf("[FAIL] ham training rc=%d\n", rc);
        return 1;
    }
    printf("[ok] ham training (bogofilter -n)\n");

    /* 2) 训练 spam（-s register-spam）*/
    std::string train_spam =
        std::string("printf 'viagra\\ncasino\\n' | '") + bogofilter + "' -d '" + bd + "' -s";
    rc = run(train_spam);
    if (rc != 0) {
        printf("[FAIL] spam training rc=%d\n", rc);
        return 1;
    }
    printf("[ok] spam training (bogofilter -s)\n");

    /* 3) 分类：-p 模式输出 X-Bogosity 分类行，spam 特征邮件应判 Spam */
    std::string classify =
        std::string("printf 'viagra casino offer\\n' | '") + bogofilter + "' -d '" + bd + "' -p";
    std::string out;
    rc = run_capture(classify, out);
    if (rc != 0) {
        printf("[FAIL] classification rc=%d\n", rc);
        return 1;
    }
    if (out.find("X-Bogosity: Spam") == std::string::npos) {
        printf("[FAIL] classification output missing 'X-Bogosity: Spam':\n%s\n", out.c_str());
        return 1;
    }
    printf("[ok] classification (bogofilter -p) -> X-Bogosity: Spam\n");

    printf("PASS: bogofilter 1.2.5 consumer test (train ham/spam + classify)\n");
    return 0;
}
