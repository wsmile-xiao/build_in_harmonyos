(* cppo integration test: invoke cppo_main to preprocess .cppo input, verify output (R34) *)
let () =
  let cppo_main =
    try Sys.argv.(1)
    with Invalid_argument _ ->
      Printf.eprintf "Usage: test_cppo.ml <cppo_main_path> [tests_dir]\n%!";
      exit 1
  in
  let tests_dir =
    try Sys.argv.(2)
    with Invalid_argument _ -> "."
  in
  (* Feed def.cppo through cppo_main, capture output to a temp file *)
  let input_path = Filename.concat tests_dir "def.cppo" in
  let out_path = Filename.concat tests_dir "test_cppo_output.tmp" in
  let cmd =
    Printf.sprintf "%s %s > %s 2>&1"
      (Filename.quote cppo_main)
      (Filename.quote input_path)
      (Filename.quote out_path)
  in
  let rc = Sys.command cmd in
  if rc <> 0 then begin
    Printf.eprintf "cppo integration test FAILED: cppo_main returned %d\n%!" rc;
    exit 1
  end;
  (* Read the output and verify macro expansion occurred.
     cppo expands #define ID(X) X and #def APPLY(F,X) so the output
     must contain "let __x" which proves the APPLY macro was expanded. *)
  let ic = open_in out_path in
  let buf = Buffer.create 4096 in
  (try while true do Buffer.add_channel buf ic 4096 done
   with End_of_file -> ());
  close_in ic;
  Sys.remove out_path;
  let output = Buffer.contents buf in
  let len = String.length output in
  let found_expansion =
    (* Search for "let __x" in the output — proves APPLY macro was expanded *)
    let rec search i =
      if i + 8 > len then false
      else if String.sub output i 8 = "let __x " then true
      else search (i + 1)
    in
    search 0
  in
  if found_expansion then
    Printf.printf "cppo integration test PASSED (macro expansion verified)\n%!"
  else begin
    Printf.eprintf "cppo integration test FAILED: no macro expansion found in output\n%!";
    exit 1
  end
