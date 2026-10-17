#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <brainfuck.h>

/* R34: test must substantively exercise the packaged library.
 * Parse and execute a "Hello World!" brainfuck program through the
 * libbrainfuck C API and assert on the captured output. */

static char output[256];
static int output_len = 0;

static int output_handler(int chr) {
    if (output_len < (int)sizeof(output) - 1)
        output[output_len++] = (char)chr;
    return chr;
}

int main(void) {
    BrainfuckState *state = brainfuck_state();
    if (!state) {
        fprintf(stderr, "FAIL: brainfuck_state() returned NULL\n");
        return EXIT_FAILURE;
    }
    BrainfuckExecutionContext *context = brainfuck_context(BRAINFUCK_TAPE_SIZE);
    if (!context) {
        fprintf(stderr, "FAIL: brainfuck_context() returned NULL\n");
        brainfuck_destroy_state(state);
        return EXIT_FAILURE;
    }
    context->output_handler = output_handler;
    BrainfuckInstruction *instruction = brainfuck_parse_string(
        "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++.");
    if (!instruction) {
        fprintf(stderr, "FAIL: brainfuck_parse_string() returned NULL\n");
        brainfuck_destroy_context(context);
        brainfuck_destroy_state(state);
        return EXIT_FAILURE;
    }
    brainfuck_add(state, instruction);
    brainfuck_execute(state->root, context);
    output[output_len] = '\0';
    brainfuck_destroy_context(context);
    brainfuck_destroy_state(state);
    if (strcmp(output, "Hello World!\n") != 0) {
        fprintf(stderr, "FAIL: unexpected output: '%s'\n", output);
        return EXIT_FAILURE;
    }
    printf("brainfuck API test OK: %s", output);
    return EXIT_SUCCESS;
}
