/* cbp2make 147 消费者测试驱动：
 * 1) 生成最小 Code::Blocks 工程 hello.cbp 与源码 hello.c
 * 2) 用包内 cbp2make 将 hello.cbp 转换为 Makefile.hello
 * 3) 断言生成的 Makefile 包含 hello.c 的编译规则与 -O2 选项
 * 4) 用系统 make 按生成的 Makefile 完成编译，断言产物存在
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char g_out[16384];

static char *read_all(const char *path) {
    FILE *f = fopen(path, "r");
    size_t n;
    if (!f) return NULL;
    n = fread(g_out, 1, sizeof(g_out) - 1, f);
    g_out[n] = '\0';
    fclose(f);
    return g_out;
}

static int write_all(const char *path, const char *content) {
    FILE *f = fopen(path, "w");
    if (!f) return 1;
    fputs(content, f);
    fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    int fails = 0;
    const char *cbp2make;
    char cmd[4096];
    char *mk;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-cbp2make> <cc>\n", argv[0]);
        return 2;
    }
    cbp2make = argv[1];

    /* 最小 Code::Blocks 工程：hello.c 编译为 hello（带 -O2） */
    if (write_all("hello.cbp",
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<CodeBlocks_project_file>\n"
        "\t<FileVersion major=\"1\" minor=\"6\"/>\n"
        "\t<Project>\n"
        "\t\t<Option title=\"hello\"/>\n"
        "\t\t<Build>\n"
        "\t\t\t<Target title=\"default\">\n"
        "\t\t\t\t<Option output=\"hello\" prefix_auto=\"0\" extension_auto=\"0\"/>\n"
        "\t\t\t\t<Option type=\"1\"/>\n"
        "\t\t\t\t<Option compiler=\"gcc\"/>\n"
        "\t\t\t</Target>\n"
        "\t\t</Build>\n"
        "\t\t<Compiler>\n"
        "\t\t\t<Add option=\"-O2\"/>\n"
        "\t\t</Compiler>\n"
        "\t\t<Unit filename=\"hello.c\">\n"
        "\t\t\t<Option compilerVar=\"CC\"/>\n"
        "\t\t</Unit>\n"
        "\t</Project>\n"
        "</CodeBlocks_project_file>\n")) {
        fprintf(stderr, "FAIL: write hello.cbp\n");
        return 1;
    }
    if (write_all("hello.c",
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "    printf(\"HELLO-FROM-CBP2MAKE\\n\");\n"
        "    return 0;\n"
        "}\n")) {
        fprintf(stderr, "FAIL: write hello.c\n");
        return 1;
    }

    /* 用被测工具执行真实转换 */
    snprintf(cmd, sizeof(cmd), "\"%s\" -in hello.cbp -out Makefile.hello -unix > convert.log 2>&1", cbp2make);
    if (system(cmd) != 0) {
        fprintf(stderr, "FAIL: cbp2make conversion exit != 0\n");
        return 1;
    }
    mk = read_all("Makefile.hello");
    if (!mk) {
        fprintf(stderr, "FAIL: Makefile.hello not generated\n");
        return 1;
    }

    /* 断言 1：生成的 Makefile 含 hello.c 的编译规则 */
    if (!strstr(mk, "hello.o: hello.c")) {
        fprintf(stderr, "FAIL: compile rule for hello.c missing\n");
        fails++;
    }
    /* 断言 2：cbp 中的 -O2 选项被传递 */
    if (!strstr(mk, "-O2")) {
        fprintf(stderr, "FAIL: -O2 option not propagated\n");
        fails++;
    }

    /* 断言 3：生成的 Makefile 可真实完成编译（生成的 Makefile 硬编码 gcc，
       用 argv[2] 传入的 profile 编译器显式覆盖；命令行变量优先级高于
       makefile 内赋值） */
    if (argc < 3) {
        fprintf(stderr, "FAIL: missing cc argument\n");
        return 2;
    }
    snprintf(cmd, sizeof(cmd),
             "make -f Makefile.hello default CC=\"%s\" LD=\"%s\" > make_out.log 2>&1",
             argv[2], argv[2]);
    if (system(cmd) != 0) {
        fprintf(stderr, "FAIL: generated makefile build failed\n");
        fails++;
    } else {
        /* 断言 4：编译产物存在 */
        FILE *f = fopen("hello", "r");
        if (!f) {
            fprintf(stderr, "FAIL: hello binary not produced\n");
            fails++;
        } else {
            fclose(f);
        }
    }

    remove("hello.cbp");
    remove("hello.c");
    remove("Makefile.hello");
    remove("hello");
    remove("convert.log");
    remove("make_out.log");

    if (fails) {
        fprintf(stderr, "%d consumer check(s) failed\n", fails);
        return 1;
    }
    printf("cbp2make consumer test PASSED: cbp-to-makefile conversion, option "
           "propagation, generated makefile build (4 checks)\n");
    return 0;
}
