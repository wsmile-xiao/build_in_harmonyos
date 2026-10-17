;;; test_web_mode.el --- consumer tests for packaged web-mode -*- lexical-binding: t; -*-

(require 'web-mode)

(defun web-mode-consumer-check (condition message)
  (unless condition
    (error "web-mode consumer assertion failed: %s" message)))

(web-mode-consumer-check (featurep 'web-mode) "feature is provided")
(web-mode-consumer-check (string= web-mode-version "17.3.20") "version")

(with-temp-buffer
  (setq buffer-file-name "consumer.html")
  (insert "<main>\n<p>Hello</p>\n</main>\n")
  (web-mode)
  (setq web-mode-markup-indent-offset 2)
  (web-mode-consumer-check (eq major-mode 'web-mode) "major mode")
  (web-mode-consumer-check (string= web-mode-content-type "html") "HTML content type")
  (goto-char (point-min))
  (web-mode-consumer-check
   (string= (web-mode-language-at-pos) "html")
   "HTML language detection")
  (web-mode-buffer-indent)
  (web-mode-consumer-check
   (string= (buffer-string) "<main>\n  <p>Hello</p>\n</main>\n")
   "deterministic HTML indentation"))

(with-temp-buffer
  (setq buffer-file-name "consumer.php")
  (insert "<?php echo 'ok'; ?>")
  (web-mode)
  (web-mode-consumer-check (string= web-mode-engine "php") "PHP engine"))

(with-temp-buffer
  (setq buffer-file-name "consumer.twig")
  (insert "<p>{{ value }}</p>")
  (web-mode)
  (web-mode-consumer-check (string= web-mode-engine "django") "Twig engine"))

(princ "web-mode packaged Elisp assertions: 8/8 PASS\n")
