/* test_package 消费者测试 — 实质调用 efsw C API
 *
 * R34: test 必须实质依赖被测包并调用其 API。本测试验证 efsw 库的
 * 生命周期 API（create / addwatch / watch / removewatch / release）
 * 在 OHOS aarch64 上可正常创建并返回有效句柄。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <efsw/efsw.h>

static int g_add_events = 0;
static int g_callback_called = 0;

static void file_action_callback( efsw_watcher watcher, efsw_watchid watchid,
                                  const char* dir, const char* filename,
                                  enum efsw_action action, const char* old_filename,
                                  void* param ) {
    (void)watcher; (void)watchid; (void)dir; (void)old_filename; (void)param;
    if ( action == EFSW_ADD ) {
        g_add_events++;
    }
    g_callback_called++;
}

static void handle_missed( efsw_watcher watcher, efsw_watchid watchid,
                           const char* dir, void* param ) {
    (void)watcher; (void)watchid; (void)dir; (void)param;
}

int main( void ) {
    char tmpdir[512];
    const char* base = getenv( "TMPDIR" );
    if ( base == NULL || *base == '\0' ) base = "/tmp";
    snprintf( tmpdir, sizeof( tmpdir ), "%s/efsw_test_pkg_%ld", base, (long)getpid() );

    if ( mkdir( tmpdir, 0755 ) != 0 ) {
        perror( "mkdir" );
        return 1;
    }

    efsw_watcher watcher = efsw_create( 0 );
    if ( watcher == NULL ) {
        fprintf( stderr, "efsw_create FAILED\n" );
        rmdir( tmpdir );
        return 1;
    }

    efsw_watchid id = efsw_addwatch( watcher, tmpdir, &file_action_callback, 1, NULL );
    if ( id < 0 ) {
        fprintf( stderr, "efsw_addwatch FAILED (id=%ld)\n", (long)id );
        efsw_release( watcher );
        rmdir( tmpdir );
        return 1;
    }

    efsw_watch( watcher );
    printf( "efsw_test_pkg: watcher created id=%ld, sleeping for events...\n", (long)id );

    /* 在监视目录内创建文件，触发 EFSW_ADD 事件 */
    char path[600];
    snprintf( path, sizeof( path ), "%s/hello.txt", tmpdir );
    FILE* f = fopen( path, "w" );
    if ( f ) {
        fprintf( f, "efsw consumer test\n" );
        fclose( f );
    }

    /* 给事件处理线程时间（inotify 异步，最多等 3 秒） */
    int waited = 0;
    while ( waited < 30 && g_callback_called == 0 ) {
        usleep( 100000 );
        waited++;
    }

    int rc = 0;
    if ( g_callback_called == 0 ) {
        fprintf( stderr, "efsw_test_pkg FAILED: no file action callback received\n" );
        rc = 1;
    } else if ( g_add_events == 0 ) {
        fprintf( stderr, "efsw_test_pkg FAILED: no EFSW_ADD event (callbacks=%d)\n", g_callback_called );
        rc = 1;
    } else {
        printf( "efsw_test_pkg OK: add_events=%d callbacks=%d\n", g_add_events, g_callback_called );
    }

    efsw_removewatch( watcher, tmpdir );
    efsw_release( watcher );

    unlink( path );
    rmdir( tmpdir );
    return rc;
}
