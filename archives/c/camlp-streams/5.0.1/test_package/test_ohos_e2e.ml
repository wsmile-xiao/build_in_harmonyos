(* camlp-streams test_package — HarmonyOS PC 端到端消费者用例（rule12）
 *
 * 与 test_camlp_streams.ml（纯内存断言）不同，本用例走完整消费者流程：
 *   1. 以 OHOS worker 上的真实文件系统为数据源（写出 param 风格配置文件）
 *   2. Stream.of_channel 从文件逐字符流式读取（库的真实 I/O 消费路径）
 *   3. Genlex.make_lexer 完成分词（库的核心功能）
 *   4. 断言分词结果 + 清理临时文件
 * 原生二进制在 HarmonyOS PC worker（aarch64-linux-ohos 用户态）上执行，
 * 验证的是「OHOS 环境下该库可被消费者端到端使用」这一平台特性。
 *)

let rec drain s acc =
  match Stream.next s with
  | exception Stream.Failure -> List.rev acc
  | x -> drain s (x :: acc)

(* 期望 token 序列（单一事实来源，下方断言直接与它整体比对，避免手工计数漂移）
   行1: const . product . software . version = "5.0.1-openharmony"  → 9 token
   行2: const . product . camera = 2                                → 7 token
   合计 16 token；其中 "." 为 5 个（行1 三个 + 行2 两个），
   字符串字面量 "5.0.1-openharmony" 内部的点号不参与分词、不单独成 token。 *)
let expected =
  [ Genlex.Ident "const"; Genlex.Kwd "."; Genlex.Ident "product"; Genlex.Kwd ".";
    Genlex.Ident "software"; Genlex.Kwd "."; Genlex.Ident "version"; Genlex.Kwd "=";
    Genlex.String "5.0.1-openharmony";
    Genlex.Ident "const"; Genlex.Kwd "."; Genlex.Ident "product"; Genlex.Kwd ".";
    Genlex.Ident "camera"; Genlex.Kwd "="; Genlex.Int 2 ]

let () =
  let path =
    (try Sys.getenv "TMPDIR" with Not_found -> "/tmp")
    ^ "/camlp_streams_ohos_e2e.param" in

  (* 1) 写出 OHOS param 风格数据（真实文件 I/O） *)
  let oc = open_out path in
  output_string oc "const.product.software.version = \"5.0.1-openharmony\"\n";
  output_string oc "const.product.camera = 2\n";
  close_out oc;

  (* 2) Stream.of_channel 流式读取 + 3) Genlex 分词
        （"." 需注册为关键字，否则 Genlex 对裸点号抛 Stream.Error） *)
  let ic = open_in path in
  let lex = Genlex.make_lexer ["="; "."] in
  let toks = drain (lex (Stream.of_channel ic)) [] in
  close_in ic;

  (* 4) 断言：流式解析跨两行输入的 token 序列与 expected 完全一致 *)
  assert (List.length toks = List.length expected);
  assert (toks = expected);
  Printf.printf "ohos param key parsed ok\n";
  assert (List.length (List.filter (fun t -> t = Genlex.Kwd "=") toks) = 2);
  assert (List.length (List.filter (fun t -> t = Genlex.Kwd ".") toks) = 5);
  assert (List.exists (fun t -> t = Genlex.String "5.0.1-openharmony") toks);
  assert (List.exists (fun t -> t = Genlex.Int 2) toks);

  (* 清理 + 成功输出 *)
  Sys.remove path;
  Printf.printf "ohos e2e: %d tokens, file consumed and removed\n"
    (List.length toks);
  Printf.printf "ALL OHOS E2E PASSED\n"
