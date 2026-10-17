/* shm_lifecycle_test.c — POSIX shared memory lifecycle verification.
 *
 * Verifies that shm_open + ftruncate + mmap(MAP_SHARED) can replace SysV
 * shmget/shmat for Zabbix's cross-process shared memory, including the resize
 * path that MAP_SHARED|MAP_ANONYMOUS cannot support: the parent grows the
 * segment AFTER fork(), and the child then re-opens it by name and reads the
 * grown data. This is the concept test for the diskstat/procstat dynamic
 * shared-data adaptation.
 *
 * The parent and child are explicitly synchronized with a pipe so the child
 * never races ahead of the parent's ftruncate+write (which would make the test
 * flaky). No sleeps are used.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>

#define NAME		"/zbx_shm_lifecycle_test"
#define INIT_SIZE	64
#define GROWN_SIZE	4096

int main(void)
{
	int		fd, status, sync_pipe[2];
	char		*base;
	pid_t		pid;

	shm_unlink(NAME);

	/* 1. create the initial segment */
	fd = shm_open(NAME, O_CREAT | O_EXCL | O_RDWR, 0600);
	if (fd < 0) { perror("shm_open(create)"); return 1; }
	if (0 != ftruncate(fd, INIT_SIZE)) { perror("ftruncate(init)"); close(fd); return 1; }
	base = mmap(NULL, INIT_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
	if (MAP_FAILED == base) { perror("mmap(init)"); close(fd); return 1; }
	strcpy(base, "initial");
	close(fd);

	/* 2. create a pipe for explicit parent->child handshake */
	if (0 != pipe(sync_pipe)) { perror("pipe"); return 1; }

	pid = fork();
	if (pid < 0) { perror("fork"); return 1; }

	if (0 == pid)
	{
		/* child: block until the parent has grown and written the segment,
		 * then re-open the grown segment by name (cross-process reattach). */
		int		fd_child;
		char		*child_base;
		char		ready;

		close(sync_pipe[1]);			/* close write end */

		if (1 != read(sync_pipe[0], &ready, 1))
		{
			perror("child read");
			close(sync_pipe[0]);
			_exit(1);
		}
		close(sync_pipe[0]);

		fd_child = shm_open(NAME, O_RDWR, 0600);
		if (fd_child < 0) { perror("child shm_open"); _exit(1); }
		child_base = mmap(NULL, GROWN_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd_child, 0);
		if (MAP_FAILED == child_base) { perror("child mmap"); close(fd_child); _exit(1); }

		if (0 != strcmp(child_base, "grown data from parent"))
		{
			fprintf(stderr, "child saw unexpected data: %s\n", child_base);
			_exit(1);
		}

		strcpy(child_base + 32, " child-updated");
		if (0 != munmap(child_base, GROWN_SIZE)) { perror("child munmap"); _exit(1); }
		close(fd_child);
		_exit(0);
	}

	/* parent: grow the segment, remap it, write the grown data, then signal
	 * the child that the grown segment is ready to be re-attached by name. */
	close(sync_pipe[0]);				/* close read end */

	if (0 != munmap(base, INIT_SIZE)) { perror("munmap(init)"); return 1; }

	fd = shm_open(NAME, O_RDWR, 0600);
	if (fd < 0) { perror("parent shm_open"); return 1; }
	if (0 != ftruncate(fd, GROWN_SIZE)) { perror("ftruncate(grow)"); close(fd); return 1; }
	base = mmap(NULL, GROWN_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
	if (MAP_FAILED == base) { perror("parent mmap(grown)"); close(fd); return 1; }
	strcpy(base, "grown data from parent");
	close(fd);

	if (1 != write(sync_pipe[1], "x", 1)) { perror("parent write"); return 1; }
	close(sync_pipe[1]);

	if (pid != waitpid(pid, &status, 0)) { perror("waitpid"); return 1; }
	if (!WIFEXITED(status) || 0 != WEXITSTATUS(status))
	{
		fprintf(stderr, "child failed\n");
		return 1;
	}

	if (0 != strcmp(base + 32, " child-updated"))
	{
		fprintf(stderr, "parent did not see child update: %s\n", base + 32);
		return 1;
	}

	printf("PASS: shm_open create/multi-process access/resize/update\n");

	/* 3. cleanup */
	if (0 != munmap(base, GROWN_SIZE)) { perror("munmap(grown)"); return 1; }
	if (0 != shm_unlink(NAME)) { perror("shm_unlink"); return 1; }

	return 0;
}
