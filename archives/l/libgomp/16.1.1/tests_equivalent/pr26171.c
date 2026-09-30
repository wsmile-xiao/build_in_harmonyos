/* PR c/26171 - equiv rewrite. #pragma omp threadprivate(thrv) -> __thread TLS.
 * No parallel region; thrv = 1, return 0.
 */
__thread int thrv = 0;

int
main (void)
{
  thrv = 1;
  return 0;
}
