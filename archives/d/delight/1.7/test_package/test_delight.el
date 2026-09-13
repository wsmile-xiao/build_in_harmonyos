;;; test_delight.el --- Consumer functional test for delight -*- lexical-binding: t; -*-

(defun test-delight--packaged-library-p (library directory basename)
  (and (stringp library)
       (string-match-p
        (concat (regexp-quote directory)
                "/"
                (regexp-quote basename)
                "\\.elc?\\'")
        library)))

;; 1. The library must resolve to the packaged site-lisp directory.
(let ((library (locate-library "delight")))
  (unless (test-delight--packaged-library-p library "delight-1.7" "delight")
    (error "delight was not loaded from the packaged lisp dir: %S" library)))

(require 'delight)

;; delight documents binding this variable around `format-mode-line' to
;; render the delighted name.  Declare it special here so that the `let'
;; forms below are dynamic bindings in this lexical-binding file.
(defvar delight-mode-name-inhibit)

;; 2. Feature and public entry points.
(unless (featurep 'delight)
  (error "delight feature was not provided"))

(dolist (function '(delight
                    delight-major-mode
                    delight-mode-line-mode-menu
                    delight--format-mode-line))
  (unless (fboundp function)
    (error "%S entry point is not defined" function)))

(unless (boundp 'delighted-modes)
  (error "delighted-modes variable is not defined"))

;; 3. Loading delight installs the format-mode-line advice.
(unless (advice-member-p #'delight--format-mode-line 'format-mode-line)
  (error "format-mode-line advice was not installed"))

;; 4. Minor mode: the lighter in minor-mode-alist is replaced immediately
;;    when FILE is t (mode already loaded), and the "Toggle minor modes"
;;    menu label is rewritten to match when such a menu item exists.
(defvar test-delight--abbrev-menu-item
  (assq 'abbrev-mode (cdr mode-line-mode-menu)))
(delight 'abbrev-mode " Abv" t)
(let ((lighter (cadr (assq 'abbrev-mode minor-mode-alist))))
  (unless (equal lighter " Abv")
    (error "abbrev-mode lighter was not delighted: %S" lighter)))
(when test-delight--abbrev-menu-item
  (let ((label (cadr (cdr (assq 'abbrev-mode (cdr mode-line-mode-menu))))))
    (unless (and (stringp label) (string-match-p " (Abv)\\'" label))
      (error "mode-line-mode-menu label was not delighted: %S" label))))

;; 5. Capture the undelighted major mode name before registering a spec.
(defvar test-delight--original-mode-name
  (with-temp-buffer
    (emacs-lisp-mode)
    (when (and (consp mode-name)
               (eq (car mode-name) 'delight-mode-name-inhibit))
      (error "emacs-lisp-mode was delighted before any spec was registered"))
    mode-name))

;; 6. Major mode: the spec is recorded and the hook is installed.
(delight 'emacs-lisp-mode "Elisp" :major)
(unless (equal (assq 'emacs-lisp-mode delighted-modes)
               '(emacs-lisp-mode "Elisp" :major))
  (error "emacs-lisp-mode delight spec was not recorded: %S"
         (assq 'emacs-lisp-mode delighted-modes)))
(unless (memq #'delight-major-mode after-change-major-mode-hook)
  (error "delight-major-mode was not added to after-change-major-mode-hook"))

;; 7. Switching to the major mode wraps mode-name as
;;    (delight-mode-name-inhibit ORIGINAL "Elisp"): a mode-line construct
;;    that renders ORIGINAL while the inhibit variable is non-nil and
;;    "Elisp" otherwise.
(with-temp-buffer
  (emacs-lisp-mode)
  (unless (and (consp mode-name)
               (= (length mode-name) 3)
               (eq (nth 0 mode-name) 'delight-mode-name-inhibit)
               (equal (nth 1 mode-name) test-delight--original-mode-name)
               (equal (nth 2 mode-name) "Elisp"))
    (error "mode-name was not delighted after emacs-lisp-mode: %S" mode-name)))

;; 8. The format-mode-line advice binds the inhibit switch to t by default
;;    (so describe-mode and friends keep the original name) and respects an
;;    explicit nil binding.  format-mode-line renders nothing in a batch
;;    session, so the around-advice is exercised directly with a probe.
(defun test-delight--probe (&rest _args)
  (if (boundp 'delight-mode-name-inhibit) delight-mode-name-inhibit 'void))

(unless (eq (delight--format-mode-line #'test-delight--probe "") t)
  (error "advice did not inhibit the delighted name by default: %S"
         (delight--format-mode-line #'test-delight--probe "")))

(unless (null (let ((delight-mode-name-inhibit nil))
                (delight--format-mode-line #'test-delight--probe "")))
  (error "advice did not respect an explicit nil inhibit binding"))

(message "delight consumer load validation OK")

;;; test_delight.el ends here
