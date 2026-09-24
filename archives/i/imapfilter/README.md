# imapfilter

Mail filtering tool that connects to IMAP mail servers, fetches messages
and applies Lua-scripted rules (move/copy/mark/delete).

- Homepage: https://github.com/lefcha/imapfilter
- License: MIT
- Build system: makefile (raw recursive Makefile)
- Type: command-line tool

## HarmonyOS PC adaptation

- Dependencies lua/5.4.8.1, pcre2/10.48, openssl/3.5.8.1 come from the
  ohpcd artifact repo (static), injected via make INCDIRS/LIBDIRS.
- No source patches required.
