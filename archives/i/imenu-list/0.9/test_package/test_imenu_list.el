;;; test_imenu_list.el --- consumer tests for packaged imenu-list -*- lexical-binding: t; -*-

(require 'imenu-list)

(defun imenu-list-consumer-check (condition message)
  (unless condition
    (error "imenu-list consumer assertion failed: %s" message)))

;; [1] feature is provided after (require 'imenu-list)
(imenu-list-consumer-check (featurep 'imenu-list) "feature is provided")

;; [2] default target buffer name
(imenu-list-consumer-check (string= imenu-list-buffer-name "*Ilist*") "buffer name default")

;; [3] minor mode entry points are defined
(imenu-list-consumer-check (fboundp 'imenu-list-minor-mode) "minor mode defined")
(imenu-list-consumer-check (fboundp 'imenu-list-smart-toggle) "smart toggle defined")

;; [4] minor mode actually toggles in batch mode (enable/disable round-trip)
(with-temp-buffer
  (imenu-list-minor-mode 1)
  (imenu-list-consumer-check imenu-list-minor-mode "minor mode enabled")
  (imenu-list-minor-mode -1)
  (imenu-list-consumer-check (not imenu-list-minor-mode) "minor mode disabled"))

;; [5] customizable placement variables with upstream defaults
(imenu-list-consumer-check (boundp 'imenu-list-position) "position defcustom")
(imenu-list-consumer-check (eq imenu-list-position 'right) "position default right")
(imenu-list-consumer-check (boundp 'imenu-list-size) "size defcustom")

(princ "imenu-list packaged Elisp assertions: 8/8 PASS\n")
