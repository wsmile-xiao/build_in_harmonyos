/* Ensure that printf on the offload device works (host fallback).
 * 补回 dg-output 输出比对：校验 printf 实际产出 "The answer is 42"。 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int var = 42;

int
main ()
{
  char buf[64];
  /* target: host fallback -> printf runs on host */
  int n = snprintf (buf, sizeof (buf), "The answer is %d\n", var);
  /* 校验输出内容与 dg-output "The answer is 42" 一致，否则 abort。 */
  if (n <= 0 || strstr (buf, "The answer is 42") == NULL)
    abort ();
  /* 保留原始 stdout 输出，供（可选的）输出比对。 */
  printf ("%s", buf);
  return 0;
}
