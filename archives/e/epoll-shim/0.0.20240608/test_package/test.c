#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/epoll.h>

/* Consumer-side smoke test for epoll-shim on HarmonyOS.
   We create an epoll fd, add a pipe read-end, and verify events. */
int main(void) {
    int epfd = epoll_create1(0);
    if (epfd < 0) { perror("epoll_create1"); return 1; }

    int fds[2];
    if (pipe(fds) < 0) { perror("pipe"); close(epfd); return 1; }

    struct epoll_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.events = EPOLLIN;
    ev.data.fd = fds[0];
    if (epoll_ctl(epfd, EPOLL_CTL_ADD, fds[0], &ev) < 0) {
        perror("epoll_ctl ADD"); close(fds[0]); close(fds[1]); close(epfd); return 1;
    }

    const char *msg = "hello";
    if (write(fds[1], msg, strlen(msg)) < 0) {
        perror("write"); close(fds[0]); close(fds[1]); close(epfd); return 1;
    }

    struct epoll_event events[1];
    int n = epoll_wait(epfd, events, 1, 1000);
    if (n < 0) { perror("epoll_wait"); close(fds[0]); close(fds[1]); close(epfd); return 1; }
    if (n == 0) { fprintf(stderr,"epoll_wait timed out\n"); close(fds[0]); close(fds[1]); close(epfd); return 1; }

    if (events[0].data.fd != fds[0] || !(events[0].events & EPOLLIN)) {
        fprintf(stderr,"unexpected event: fd=%d events=0x%x\n",events[0].data.fd,events[0].events);
        close(fds[0]); close(fds[1]); close(epfd); return 1;
    }

    char buf[16];
    int rd = read(fds[0], buf, sizeof(buf));
    if (rd < 0) { perror("read"); close(fds[0]); close(fds[1]); close(epfd); return 1; }
    buf[rd] = '\0';
    printf("PASS: epoll event received, data=%s\n", buf);

    close(fds[0]); close(fds[1]); close(epfd);
    return 0;
}
