# xjobs

xjobs launches one process per input job while limiting the number of concurrent jobs. The 20241010 package uses the author's official source release and the framework's Conan 2 recipe.

The upstream make test script generates random dummy jobs and only exercises a fixed -j8 run. The consumer test adds deterministic checks for the framework-compatible --version option, exact job counts, the -j cap, failed-job exit status and -e, stdout redirection, arguments with spaces, single-character command template arguments, and SIGINT cancellation with child reaping.

The recipe declares `flex/2.6.4` as a Conan build tool for tokenizer generation during the upstream configure + GNU Make build. Curses/tinfo support is optional and selected by upstream configure probes.
