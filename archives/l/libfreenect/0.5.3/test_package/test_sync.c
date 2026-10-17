#include <stdio.h>

#include <libfreenect_sync.h>

/* Second consumer use case: compile against the synchronous wrapper header
 * (libfreenect_sync.h) and call freenect_sync_stop(). Without a Kinect
 * attached the global thread_running is 0, so this is a safe no-op; the
 * purpose is to prove the second exported API surface (libfreenect_sync)
 * and its header are consumable from a CMake consumer. */
int main(void)
{
    freenect_sync_stop();
    printf("test libfreenect_sync 0.5.3: LINK-OK (sync wrapper, device absent)\n");
    return 0;
}
