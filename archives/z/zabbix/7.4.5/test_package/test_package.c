/* test_package.c — Zabbix 7.4.5 runtime smoke test for HarmonyOS.
 *
 * Executes the packaged zabbix_agentd / zabbix_get / zabbix_sender with
 * --version and checks their exit code, so the compiled test binary actually
 * exercises the packaged executables (R34) rather than just printing strings.
 * The full CLI + agentd/get integration test lives in conanfile.py test().
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int run_checked(const char *argv[])
{
	pid_t	pid = fork();

	if (pid < 0)
	{
		perror("fork");
		return 1;
	}

	if (0 == pid)
	{
		execvp(argv[0], (char *const *)argv);
		perror("execvp");
		_exit(127);
	}

	int	status;

	if (waitpid(pid, &status, 0) < 0)
	{
		perror("waitpid");
		return 1;
	}

	if (!WIFEXITED(status) || 0 != WEXITSTATUS(status))
		return 1;

	return 0;
}

int main(void)
{
	const char	*const tools[] = {"zabbix_agentd", "zabbix_get", "zabbix_sender"};
	size_t		i;

	for (i = 0; i < sizeof(tools) / sizeof(tools[0]); i++)
	{
		const char	*argv[] = {tools[i], "--version", NULL};

		if (0 != run_checked(argv))
		{
			fprintf(stderr, "FAIL: %s --version\n", tools[i]);
			return 1;
		}

		printf("PASS: %s --version\n", tools[i]);
	}

	printf("All tests passed.\n");
	return 0;
}
