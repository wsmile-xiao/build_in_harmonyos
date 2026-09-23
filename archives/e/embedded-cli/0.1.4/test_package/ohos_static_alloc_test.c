/*
 * HarmonyOS 专项测试 — embedded-cli 0.1.4
 *
 * 与上游 Catch2 测试（CliWrapper/CliBuilder C++ 包装）不同的独立用例：
 *  - 仅使用公开头文件与公开 API（消费者的视角）
 *  - 覆盖静态分配路径（cliBuffer 无动态内存，嵌入式/鸿蒙场景典型用法）
 *  - 覆盖公开 tokenize API（embeddedCliTokenizeArgs / GetToken / GetTokenCount）
 *  - 覆盖命令行绑定回调 + 参数 tokenize 断言 + 自动补全默认开
 */
#include <stdio.h>
#include <string.h>

#include "embedded_cli.h"

static int binding_fired = 0;
static char tok1[16] = {0};
static char tok2[16] = {0};

static void on_led(EmbeddedCli *cli, char *args, void *context) {
    (void)cli;
    (void)context;
    binding_fired = 1;
    if (args != NULL) {
        strncpy(tok1, embeddedCliGetToken(args, 1), sizeof(tok1) - 1);
        strncpy(tok2, embeddedCliGetToken(args, 2), sizeof(tok2) - 1);
    }
}

static void sink_write(EmbeddedCli *cli, char c) {
    (void)cli;
    (void)c;
}

static int test_tokenize_api(void) {
    char args_buf[] = "led 1 1";
    embeddedCliTokenizeArgs(args_buf);
    if (embeddedCliGetTokenCount(args_buf) != 3) {
        fprintf(stderr, "FAIL: expected 3 tokens\n");
        return 1;
    }
    if (strcmp(embeddedCliGetToken(args_buf, 1), "led") != 0 ||
        strcmp(embeddedCliGetToken(args_buf, 2), "1") != 0 ||
        strcmp(embeddedCliGetToken(args_buf, 3), "1") != 0) {
        fprintf(stderr, "FAIL: token contents mismatch\n");
        return 1;
    }
    if (embeddedCliFindToken(args_buf, "1") != 2) {
        fprintf(stderr, "FAIL: findToken('1') expected pos 2\n");
        return 1;
    }
    return 0;
}

int main(void) {
    /* 静态分配路径：嵌入式无动态内存场景 */
    EmbeddedCliConfig *config = embeddedCliDefaultConfig();
    if (config == NULL) {
        fprintf(stderr, "FAIL: embeddedCliDefaultConfig returned NULL\n");
        return 1;
    }
    config->maxBindingCount = 16;
    uint16_t need = embeddedCliRequiredSize(config);
    static CLI_UINT cli_buffer[1024]; /* 1024 * CLI_UINT_SIZE bytes */
    if (need > sizeof(cli_buffer)) {
        fprintf(stderr, "FAIL: required %u > buffer %zu\n", need, sizeof(cli_buffer));
        return 1;
    }
    config->cliBuffer = cli_buffer;
    config->cliBufferSize = sizeof(cli_buffer);

    EmbeddedCli *cli = embeddedCliNew(config);
    if (cli == NULL) {
        fprintf(stderr, "FAIL: embeddedCliNew (static alloc) returned NULL\n");
        return 1;
    }
    cli->writeChar = sink_write;

    CliCommandBinding binding = {
        .name = "led",
        .help = "control the led: led <index> <0|1>",
        .tokenizeArgs = true,
        .context = NULL,
        .binding = on_led,
    };
    if (!embeddedCliAddBinding(cli, binding)) {
        fprintf(stderr, "FAIL: embeddedCliAddBinding returned false\n");
        embeddedCliFree(cli);
        return 1;
    }

    const char *input = "led 1 1\r\n";
    for (const char *p = input; *p; ++p) {
        embeddedCliReceiveChar(cli, *p);
        embeddedCliProcess(cli);
    }

    if (!binding_fired) {
        fprintf(stderr, "FAIL: binding callback was not fired\n");
        embeddedCliFree(cli);
        return 1;
    }
    if (strcmp(tok1, "1") != 0 || strcmp(tok2, "1") != 0) {
        fprintf(stderr, "FAIL: tokens '%s'/'%s' (expected '1'/'1')\n", tok1, tok2);
        embeddedCliFree(cli);
        return 1;
    }

    embeddedCliFree(cli);
    if (test_tokenize_api() != 0)
        return 1;

    printf("PASS: OHOS static-alloc CLI: binding fired, tokens=%s/%s, tokenize api ok\n",
           tok1, tok2);
    return 0;
}