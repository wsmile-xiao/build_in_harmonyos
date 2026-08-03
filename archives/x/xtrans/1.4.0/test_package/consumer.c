#include <stddef.h>

#include <X11/Xtrans/transport.c>

static const char xtrans_case_id[] = "@XTRANS_CASE_ID@";

int main(void)
{
    size_t interface_size = sizeof(Xtransaddr) + sizeof(XtransConnInfo);

    interface_size += sizeof(&TRANS(FreeConnInfo));
    interface_size += sizeof(&TRANS(SetOption));
    interface_size += sizeof(&TRANS(BytesReadable));
    interface_size += sizeof(&TRANS(Read));
    interface_size += sizeof(&TRANS(Write));
    interface_size += sizeof(&TRANS(Readv));
    interface_size += sizeof(&TRANS(Writev));
    interface_size += sizeof(&TRANS(Disconnect));
    interface_size += sizeof(&TRANS(Close));
    interface_size += sizeof(&TRANS(CloseForCloning));
    interface_size += sizeof(&TRANS(IsLocal));
    interface_size += sizeof(&TRANS(GetPeerAddr));
    interface_size += sizeof(&TRANS(GetConnectionNumber));
    interface_size += sizeof(&TRANS(GetHostname));
#if XTRANS_SEND_FDS
    interface_size += sizeof(&TRANS(SendFd));
    interface_size += sizeof(&TRANS(RecvFd));
#endif
#ifdef TRANS_CLIENT
    interface_size += sizeof(&TRANS(OpenCOTSClient));
    interface_size += sizeof(&TRANS(Connect));
#endif
#ifdef TRANS_SERVER
    interface_size += sizeof(&TRANS(OpenCOTSServer));
    interface_size += sizeof(&TRANS(CreateListener));
    interface_size += sizeof(&TRANS(Received));
    interface_size += sizeof(&TRANS(NoListen));
    interface_size += sizeof(&TRANS(Listen));
    interface_size += sizeof(&TRANS(IsListening));
    interface_size += sizeof(&TRANS(ResetListener));
    interface_size += sizeof(&TRANS(Accept));
    interface_size += sizeof(&TRANS(MakeAllCOTSServerListeners));
#endif
#ifdef TRANS_REOPEN
    interface_size += sizeof(&TRANS(ReopenCOTSServer));
    interface_size += sizeof(&TRANS(GetReopenInfo));
#endif
#ifdef X11_t
    interface_size += sizeof(&TRANS(ConvertAddress));
#endif
#ifdef ICE_t
    interface_size += sizeof(&TRANS(GetMyNetworkId));
    interface_size += sizeof(&TRANS(GetPeerNetworkId));
#endif

    return interface_size == 0 || xtrans_case_id[0] == '\0';
}
