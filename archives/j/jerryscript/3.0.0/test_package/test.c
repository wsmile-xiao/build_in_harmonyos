#include <stdio.h>
#include <string.h>

#include "jerryscript.h"
#include "jerryscript-ext/handlers.h"
#include "jerryscript-ext/properties.h"

static int
run_number_script (const jerry_char_t *source_p, double expected)
{
  jerry_value_t result = jerry_eval (source_p, strlen ((const char *) source_p), JERRY_PARSE_NO_OPTS);

  if (jerry_value_is_exception (result) || !jerry_value_is_number (result)
      || jerry_value_as_number (result) != expected)
  {
    jerry_value_free (result);
    return 1;
  }

  jerry_value_free (result);
  return 0;
}

int
main (void)
{
  jerry_init (JERRY_INIT_EMPTY);

  if (run_number_script ((const jerry_char_t *) "1 + 2", 3.0) != 0)
  {
    fprintf (stderr, "core API evaluation failed\n");
    jerry_cleanup ();
    return 1;
  }

  jerryx_register_global ("print", jerryx_handler_print);
  if (run_number_script ((const jerry_char_t *) "print('jerryscript'); 4", 4.0) != 0)
  {
    fprintf (stderr, "extension API evaluation failed\n");
    jerry_cleanup ();
    return 2;
  }

  jerry_cleanup ();
  puts ("jerryscript 3.0.0 API assertions: 4 passed");
  return 0;
}
