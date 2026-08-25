(* Minimal ATS program — compiled by patscc in test_package (R34).
   println! macro is provided by prelude (auto-loaded, same as the
   upstream doc/EXAMPLE/INTRO/hello.dats — no explicit staload). *)
implement
main0 () = {
  val () = println! ("hello from ats2-postiats")
}
(* end of [hello_ats.dats] *)
