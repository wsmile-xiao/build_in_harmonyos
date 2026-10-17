#include <stdio.h>
#include <assert.h>

#include <dynamic.h>

static int compare(void *p1, void *p2)
{
  return *(int *) p1 - *(int *) p2;
}

int main(void)
{
  list list;
  int *p;

  list_construct(&list);

  list_push_back(&list, (int[]) {4}, sizeof(int));
  list_push_back(&list, (int[]) {5}, sizeof(int));
  list_push_front(&list, (int[]) {3}, sizeof(int));
  list_push_front(&list, (int[]) {1}, sizeof(int));
  assert(list_size(&list) == 4);

  p = list_find(&list, compare, (int[]) {4});
  assert(p != NULL && *p == 4);

  p = list_find(&list, compare, (int[]) {42});
  assert(p == NULL);

  list_destruct(&list, NULL);

  printf("test libdynamic 2.3.0: OK\n");
  return 0;
}
