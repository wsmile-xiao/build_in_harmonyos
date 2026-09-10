#include <cstdio>
#include <cstring>
#include <ctime>
#include <atomic>
#include <sched.h>

#include <clthreads.h>

// Consumer-style use case: a worker thread built on H_thread (P_thread +
// ITC_ip1q), the pattern the library is designed for. The main thread sends
// Textmsg commands to the worker's queue; the worker computes the reply and
// posts it back to the main thread's queue. Exercises real thread creation
// (thr_start), blocking event wait (get_event), cross-thread mutex/condvar
// signalling, message ownership transfer, and Textmsg formatting.
//
// P_thread creates detached threads and offers no join, so termination is
// synchronized deterministically: the worker publishes an exit flag as the
// very last statement of thr_main (it touches no member afterwards), and the
// main thread waits for that flag with a bounded spin-sleep before deleting
// the worker object.

class Worker : public H_thread
{
public:
    Worker (Edest *reply_queue) : H_thread (reply_queue, 0) {}

    bool finished (void) const { return _finished.load (std::memory_order_acquire); }

    virtual void thr_main (void)
    {
        while (1)
        {
            int e = get_event ();
            if (e != 0)
                continue;
            Textmsg *cmd = static_cast<Textmsg *> (get_message ());
            if (!cmd)
                continue;
            if (std::strcmp (cmd->text (), "TERM") == 0)
            {
                delete cmd;
                Textmsg *bye = new Textmsg (16);
                bye->printf ("BYE");
                reply (bye);
                _finished.store (true, std::memory_order_release);
                return;
            }
            int v = 0;
            std::sscanf (cmd->text (), "%d", &v);
            delete cmd;
            Textmsg *rep = new Textmsg (32);
            rep->printf ("%d", v * v);
            reply (rep);
        }
    }

private:
    std::atomic<bool> _finished { false };
};

static int expect_text (ITC_ip1q& queue, const char *expected)
{
    // Bounded poll instead of the blocking get_event(): if the worker
    // dies before replying the test must fail, not hang the CI gates.
    bool arrived = false;
    for (int i = 0; i < 10000 && !arrived; i++)
    {
        if (queue.get_event_nowait () == 0)
            arrived = true;
        else
        {
            struct timespec ts = { 0, 1000 * 1000 };
            nanosleep (&ts, 0);
        }
    }
    if (!arrived)
        return 1;
    Textmsg *m = static_cast<Textmsg *> (queue.get_message ());
    if (!m)
        return 1;
    if (std::strcmp (m->text (), expected) != 0)
    {
        delete m;
        return 1;
    }
    delete m;
    return 0;
}

int main ()
{
    ITC_ip1q reply_queue;
    Worker *worker = new Worker (&reply_queue);

    if (worker->thr_start (SCHED_OTHER, 0, 0) != 0)
        return 1;

    for (int v = 3; v <= 12; v += 9)
    {
        Textmsg *cmd = new Textmsg (16);
        cmd->printf ("%d", v);
        if (worker->put_event (0, cmd) != Edest::NO_ERROR)
            return 1;
        char expected [16];
        std::sprintf (expected, "%d", v * v);
        if (expect_text (reply_queue, expected))
            return 1;
    }

    Textmsg *term = new Textmsg (16);
    term->printf ("TERM");
    if (worker->put_event (0, term) != Edest::NO_ERROR)
        return 1;
    if (expect_text (reply_queue, "BYE"))
        return 1;

    // Bounded wait for the worker's exit flag (generous: the worker only
    // has to return from thr_main after the BYE reply).
    for (int i = 0; i < 10000 && !worker->finished (); i++)
    {
        struct timespec ts = { 0, 1000 * 1000 };
        nanosleep (&ts, 0);
    }
    if (!worker->finished ())
        return 1;
    delete worker;

    if (Textmsg::object_counter () != 0)
        return 1;

    return 0;
}
