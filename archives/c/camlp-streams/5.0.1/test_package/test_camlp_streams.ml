(* camlp-streams test_package — consumer test (R34: really uses the package)
 *
 * Exercises both public modules of the packaged camlp-streams library:
 *   Stream  — stream construction + iteration (Stream.of_list / Stream.next)
 *   Genlex  — tokenization via Genlex.make_lexer
 *
 * Compiled against the conan package (OCAMLPATH = <pkg>/lib/ocaml) both as
 * bytecode (ocamlc) and native (ocamlopt); the native binary must run and
 * print the success lines.
 *)

let rec drain s acc =
  match Stream.next s with
  | exception Stream.Failure -> List.rev acc
  | x -> drain s (x :: acc)

let () =
  (* 1. Stream: of_list + next iteration preserves order and values *)
  let s = Stream.of_list [1; 2; 3] in
  assert (drain s [] = [1; 2; 3]);
  Printf.printf "stream iteration ok: 1 2 3\n";

  (* 2. Genlex: keyword / identifier / number / string classification.
       Input deliberately avoids bare operator characters (Genlex raises
       Stream.Error on a special character that is not in the keyword list);
       the nested comment must be skipped. *)
  let lexer = Genlex.make_lexer ["let"; "="] in
  let input = "let x = 1 2 3.14 \"str\" (* comment (nested) *)" in
  let tokens = drain (lexer (Stream.of_string input)) [] in
  assert (tokens = [Genlex.Kwd "let"; Genlex.Ident "x"; Genlex.Kwd "=";
                    Genlex.Int 1; Genlex.Int 2; Genlex.Float 3.14;
                    Genlex.String "str"]);
  Printf.printf "genlex tokenization ok: %d tokens\n" (List.length tokens);

  Printf.printf "ALL TESTS PASSED\n"
