/* reverse-offload-sm30.c — 完全等价改写 (host-only)
 * 原为 dg-do link (offload nvptx) + #pragma omp requires reverse_offload + 空 target。
 * host 上: requires 为编译期 no-op，空 target body 无副作用。
 */
int
main (void)
{
  return 0;
}
