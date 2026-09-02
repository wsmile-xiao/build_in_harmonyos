/* Consumer test: exercise Elk's public API and a real evaluation result. */
#include <stddef.h>
#include <elk.h>

#include <stdio.h>
#include <string.h>

int main(void) {
  char mem[2048];
  struct js *js = js_create(mem, sizeof(mem));
  if (js == NULL) {
    fprintf(stderr, "FAIL: js_create returned NULL\n");
    return 1;
  }

  const char arithmetic[] = "1 + 2 * 3";
  jsval_t result = js_eval(js, arithmetic, strlen(arithmetic));
  const char *text = js_str(js, result);
  if (text == NULL || strcmp(text, "7") != 0) {
    fprintf(stderr, "FAIL: arithmetic result was '%s'\n", text ? text : "(null)");
    return 1;
  }

  const char stateful[] = "let x = 6; x * 7;";
  result = js_eval(js, stateful, strlen(stateful));
  text = js_str(js, result);
  if (text == NULL || strcmp(text, "42") != 0) {
    fprintf(stderr, "FAIL: stateful evaluation result was '%s'\n",
            text ? text : "(null)");
    return 1;
  }

  printf("Elk %s API smoke test: PASS (usage=%d%%)\n", JS_VERSION,
         js_usage(js));
  return 0;
}
