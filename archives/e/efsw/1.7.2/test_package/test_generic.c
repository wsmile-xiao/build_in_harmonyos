/* test_package HarmonyOS 专项测试 — generic (轮询) 后端
 *
 * 上游默认 inotify 后端在 OHOS aarch64 已由 test.c 验证；本专项用例验证
 * efsw_create(1) 的 generic 轮询后端在同一平台可正常创建、监听并回调，
 * 覆盖 efsw 两条平台后端路径。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <efsw/efsw.h>

static int g_events = 0;

static void file_action_callback( efsw_watcher watcher, efsw_watchid watchid,
                                  const char* dir, const char* filename,
                                  enum efsw_action action, const char* old_filename,
                                  void* param ) {
    (void)watcher; (void)watchid; (void)dir; (void)old_filename; (void)param;
    if ( action == EFSW_MODIFIED || action == EFSW_ADD ) {
        g_events++;
    }
}

static void handle_missed( efsw_watcher watcher, efsw_watchid watchid,
                           const char* dir, void* param ) {
    (void)watcher; (void)watchid; (void)dir; (void)param;
}

int main( void ) {
    char tmpdir[512];
    const char* base = getenv( "TMPDIR" );
    if ( base == NULL || *base == '\0' ) base = "/tmp";
    snprintf( tmpdir, sizeof( tmpdir ), "%s/efsw_test_pkg_generic_%ld", base, (long)getpid() );

    if ( mkdir( tmpdir, 0755 ) != 0 ) {
        perror( "mkdir" );
        return 1;
    }

    /* generic_mode=1: 使用 generic 轮询后端 */
    efsw_watcher watcher = efsw_create( 1 );
    if ( watcher == NULL ) {
        fprintf( stderr, "efsw_create(generic) FAILED\n" );
        rmdir( tmpdir );
        return 1;
    }

    efsw_watchid id = efsw_addwatch( watcher, tmpdir, &file_action_callback, 1, NULL );
    if ( id < 0 ) {
        fprintf( stderr, "efsw_addwatch(generic) FAILED (id=%ld)\n", (long)id );
        efsw_release( watcher );
        rmdir( tmpdir );
        return 1;
    }

    efsw_watch( watcher );
    printf( "efsw_test_pkg_generic: watcher(generic) created id=%ld\n", (long)id );

    char path[600];
    snprintf( path, sizeof( path ), "%s/hello.txt", tmpdir );
    FILE* f = fopen( path, "w" );
    if ( f ) {
        fprintf( f, "efsw generic consumer test\n" );
        fclose( f );
    }

    int waited = 0;
    while ( waited < 50 && g_events == 0 ) {
        usleep( 100000 );
        waited++;
    }

    int rc = 0;
    if ( g_events == 0 ) {
        fprintf( stderr, "efsw_test_pkg_generic FAILED: no event in generic backend\n" );
        rc = 1;
    } else {
        printf( "efsw_test_pkg_generic OK: events=%d\n", g_events );
    }

    efsw_removewatch( watcher, tmpdir );
    efsw_release( watcher );

    unlink( path );
    rmdir( tmpdir );
    return rc;
}