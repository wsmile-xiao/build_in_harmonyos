#ifndef ONION_HTTP_FIXTURE_H
#define ONION_HTTP_FIXTURE_H
#include <onion/onion.h>
#include <onion/http.h>
#include <onion/types_internal.h>
#include <onion/listen_point.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <netinet/in.h>
typedef struct { onion *server; onion_listen_point *point; pthread_t thread;
    unsigned short port; int started; int listen_rc; } fixture;
/* Pre-bind a private port 0 socket; never race a shared fixed port. */
static void already_bound(onion_listen_point *point) { (void)point; }
static void *fixture_listen(void *arg) {
    fixture *f=(fixture *)arg; f->listen_rc=onion_listen(f->server); return NULL;
}
static int fixture_init(fixture *f) {
    memset(f,0,sizeof(*f));
    int fd=socket(AF_INET,SOCK_STREAM,0); if(fd<0) return 1;
    struct sockaddr_in sa; memset(&sa,0,sizeof(sa));
    sa.sin_family=AF_INET; sa.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    socklen_t size=sizeof(sa);
    if(bind(fd,(struct sockaddr *)&sa,sizeof(sa)) || getsockname(fd,(struct sockaddr *)&sa,&size) || listen(fd,5)) { close(fd); return 1; }
    f->port=ntohs(sa.sin_port); f->server=onion_new(O_POOL|O_NO_SIGTERM); f->point=onion_http_new();
    if(!f->server || !f->point) {
        close(fd); if(f->point) onion_listen_point_free(f->point);
        if(f->server) onion_free(f->server); return 1;
    }
    onion_set_max_threads(f->server,2); onion_set_timeout(f->server,5000);
    f->point->listenfd=fd; f->point->listen=already_bound;
    onion_add_listen_point(f->server,"127.0.0.1","0",f->point); return 0;
}
static int fixture_start(fixture *f) {
    if(pthread_create(&f->thread,NULL,fixture_listen,f)) return 1;
    f->started=1; return 0;
}
static int fixture_get(fixture *f,const char *path,char *response,size_t capacity) {
    int fd=socket(AF_INET,SOCK_STREAM,0); if(fd<0) return 1;
    struct timeval timeout={5,0};
    if(setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout)) || setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout))) { close(fd); return 1; }
    struct sockaddr_in sa; memset(&sa,0,sizeof(sa));
    sa.sin_family=AF_INET;sa.sin_addr.s_addr=htonl(INADDR_LOOPBACK);sa.sin_port=htons(f->port);
    if(connect(fd,(struct sockaddr *)&sa,sizeof(sa))) { close(fd); return 1; }
    char request[2048]; int length=snprintf(request,sizeof(request),"GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n",path);
    if(length<0 || (size_t)length>=sizeof(request)) { close(fd); return 1; }
    size_t offset=0;
    while(offset<(size_t)length) {
        ssize_t n=send(fd,request+offset,(size_t)length-offset,0);
        if(n<0 && errno==EINTR) continue;
        if(n<=0) { close(fd); return 1; } offset+=(size_t)n;
    }
    offset=0;
    for(;;) {
        if(offset+1>=capacity) { close(fd); return 1; }
        ssize_t n=recv(fd,response+offset,capacity-1-offset,0);
        if(n<0 && errno==EINTR) continue;
        if(n<0) { close(fd); return 1; }
        if(n==0) break; offset+=(size_t)n;
    }
    response[offset]=0; close(fd); return offset==0;
}
static int fixture_end(fixture *f) {
    int rc=0;
    if(f->started) {
        onion_listen_stop(f->server);
        if(pthread_join(f->thread,NULL) || f->listen_rc) rc=1;
    }
    onion_free(f->server); f->server=NULL; return rc;
}
#endif
