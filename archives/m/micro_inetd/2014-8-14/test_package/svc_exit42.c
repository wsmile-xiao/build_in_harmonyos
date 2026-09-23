/* svc_exit42.c — inetd-style service that exits immediately with code 42.
 *
 * Used by test_micro_inetd to verify that micro_inetd keeps accepting
 * after a service child exits, reaps it (no zombie), and the client
 * observes EOF because the child's dup2()ed socket descriptors close.
 */
int main(void)
{
    return 42;
}
