// mmap capability probe for jellyfish1.
//
// include/jellyfish/mapped_file.hpp maps an existing k-mer database read only
// with mmap(0, size, PROT_READ, MAP_PRIVATE, fd, 0) and is what every jellyfish
// consumer command (query / dump / stat) uses to open a .mer file.  This probe
// calls mmap(2) with the identical argument list on a real file so the OHOS
// kernel capability is measured directly, not inferred from the CLI passing.
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
  if(argc < 2) { fprintf(stderr, "usage: mmap_probe FILE\n"); return 2; }
  struct stat st;
  memset(&st, 0, sizeof(st));
  if(stat(argv[1], &st) != 0) { fprintf(stderr, "stat errno=%d\n", errno); return 2; }
  int fd = open(argv[1], O_RDONLY);
  if(fd < 0) { fprintf(stderr, "open errno=%d\n", errno); return 2; }
  void *p = mmap(0, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
  if(p == MAP_FAILED) {
    printf("MMAP_RESULT=FAILED errno=%d size=%ld\n", errno, (long)st.st_size);
    close(fd);
    return 1;
  }
  volatile unsigned char first = ((unsigned char *)p)[0];
  printf("MMAP_RESULT=OK size=%ld first_byte=%d\n", (long)st.st_size, (int)first);
  if(munmap(p, (size_t)st.st_size) != 0)
    printf("MUNMAP errno=%d\n", errno);
  else
    printf("MUNMAP=OK\n");
  close(fd);
  return 0;
}
