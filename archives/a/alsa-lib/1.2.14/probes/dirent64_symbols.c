#define _GNU_SOURCE
#include <dirent.h>
#include <stdio.h>
#include <sys/types.h>

static int filt(const struct dirent64 *d) { (void)d; return 1; }

int main(void)
{
	struct dirent64 **list = NULL;
	int n;
	int (*s1)(const void *, const void *) = alphasort64;
#ifdef HAVE_VERSIONSORT64
	int (*s2)(const void *, const void *) = versionsort64;
	printf("versionsort64=%p\n", (void *)s2);
#endif
	printf("alphasort64=%p scandir64=%p\n", (void *)s1, (void *)scandir64);
	n = scandir64(".", &list, filt, alphasort64);
	printf("scandir64 rc=%d\n", n);
	return 0;
}
