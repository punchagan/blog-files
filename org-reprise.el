;;; org-reprise.el --- Export html to be used by reprise.py
;;;
;;; Author: Puneeth Chaganti <punchagan+org-reprise@gmail.com>
;;;
;;; org-reprise is derived from org-hyde and org-jekyll
;;;
;;; Summary
;;; -------
;;;
;;; Extract subtrees from your org-publish project files that have a
;;; WEB_CAT property with a time-stamp and an :ol: tag, and export
;;; them to a subdirectory source of your project's publishing
;;; directory.  Properties are passed over as (email) front-matter in
;;; the exported files.  The title of the subtree is the title of the
;;; entry.

(defvar org-reprise-category "WEB_CAT"
  "Specify a property which, if defined in the entry, is used as
a category: the post is written to category/_posts. Ignored if
nil.")

(defvar org-reprise-new-buffers nil
  "Buffers created to visit org-publish project files looking for blog posts.")

(defvar org-reprise-use-pygments t
  "Use pygments to syntax highlight code blocks if non-nil.")

(defun org-reprise-publish-dir (project &optional category)
  "Where does the project go, by default a :blog-publishing-directory 
   entry in the org-publish-project-alist."
  (let ((pdir (plist-get (cdr project) :blog-publishing-directory)))
    (unless pdir
      (setq pdir (plist-get (cdr project) :publishing-directory)))
    (concat pdir "source/" (if category (concat category "/") ""))))

(defun org-reprise-site-root (project)
  "Site root, like http://yoursite.com, from which blog
  permalinks follow.  Needed to replace entry titles with
  permalinks that RSS agregators and google buzz know how to
  follow.  Looks for a :site-root entry in the org-publish-project-alist."
  (or (plist-get (cdr project) :site-root)
      ""))

(defun org-get-reprise-file-buffer (file)
  "Get a buffer visiting FILE.  If the buffer needs to be
  created, add it to the list of buffers which might be released
  later.  Copied from org-get-agenda-file-buffer, and modified
  the list that holds buffers to release."
  (let ((buf (org-find-base-buffer-visiting file)))
    (if buf
        buf
      (progn (setq buf (find-file-noselect file))
             (if buf (push buf org-reprise-new-buffers))
             buf))))

(defun ensure-directories-exist (fname)
  (let ((dir (file-name-directory fname)))
    (unless (file-accessible-directory-p dir)
      (make-directory dir t)))
  fname)

(defun org-reprise-convert-pre (html)
  "Replace pre blocks with syntax blocks for pygments."
  (save-excursion
    (let (pos info params src-re code-re)
      (with-temp-buffer
        (insert html)
        (goto-char (point-min))
        (save-match-data
          (while (re-search-forward 
                  "<pre\\(.*?\\)>\\(\\(.\\|[[:space:]]\\|\\\n\\)*?\\)</pre.*?>"
                  nil t 1)
            (setq code (match-string-no-properties 2))
            (if (save-match-data 
                  (string-match "example" (match-string-no-properties 1)))
                (setq lang "text")
              (setq lang (substring 
                          (match-string-no-properties 1) 16 -1))
              ;; handling emacs-lisp separately. pygments raises error when language 
              ;; is unknown. list of languages variable should be added?
              (if (string= "emacs-lisp" lang)
                  (setq lang "common-lisp")))
            (save-match-data
              (setq code (replace-regexp-in-string "<.*?>" "" code))
              (while (string-match "&gt;" code)
                (setq code (replace-match ">" t t code)))
              (while (string-match "&lt;" code)
                (setq code (replace-match "<" t t code)))
              (while (string-match "&amp;" code)
                (setq code (replace-match "&" t t code))))
            (replace-match 
             (shell-command-to-string
              (format "echo -e %S | pygmentize -l %s -f html" code lang)) 
             nil t)))
        (setq html (buffer-substring-no-properties (point-min) (point-max))))))
  html)

(defun org-reprise-export-entry (project)
  (let* ((props (org-entry-properties nil 'standard))
         (time (or (org-entry-get (point) "POST_DATE")
                   (org-entry-get (point) "SCHEDULED")
                   (org-entry-get (point) "DEADLINE")
                   (org-entry-get (point) "TIMESTAMP_IA")))
         (category (if org-reprise-category
                       (cdr (assoc org-reprise-category props))
                     nil)))
    (when time
      (let* ((heading (org-get-heading t))
             ;; Get the tags from the headline
             (tags (mapconcat 'identity (org-get-tags-at (point) t) " "))
             (title (replace-regexp-in-string "[/]" "" heading))
             ;; Save the time used as POST_DATE. SCHEDULED etc may change.
             (str-time 
              (format-time-string "%Y:%m:%d:%T" 
                                  (if time
                                      (apply 'encode-time 
                                             (org-parse-time-string time))
                                    (current-time)
                                    (org-entry-put (point) 
                                                   "POST_DATE" cur-time))))
             (to-file (format "%s.txt" title))
             (org-buffer (current-buffer))
             (front-matter (cons (cons "Title" heading) nil))
             (front-matter (cons (cons "Tags" tags) front-matter))
             (front-matter (cons (cons "Created" str-time) front-matter))
             html)
        (org-narrow-to-subtree)
        (let ((level (- (org-reduced-level (org-outline-level)) 1))
              (contents (buffer-substring (point-min) (point-max))))
          ;; Without the promotion the header with which the headline
          ;; is exported depends on the level.  With the promotion it
          ;; fails when the entry is not visible (ie, within a folded
          ;; entry).
          (dotimes (n level nil) (org-promote-subtree))
          (setq html 
                (org-export-region-as-html
                 (1+ (and (org-back-to-heading) (line-end-position)))
                 (org-end-of-subtree)
                 t 'string))
          (set-buffer org-buffer)
          (when org-reprise-use-pygments
            (setq html (org-reprise-convert-pre html)))
          (delete-region (point-min) (point-max))
          (insert contents)
          (save-buffer))
        (widen)
        (with-temp-file (ensure-directories-exist
                         (expand-file-name 
                          to-file (org-reprise-publish-dir project category)))
          (when front-matter
            (mapc (lambda (pair) 
                    (insert (format "%s: %s\n" (car pair) (cdr pair))))
                  front-matter)
            (insert "\n\n"))
          (insert html))))))

; Evtl. needed to keep compiler happy:
(declare-function org-publish-get-project-from-filename "org-publish"
                  (filename &optional up))

(defun org-reprise-export-current-entry ()
  (interactive)
  (save-excursion
    (let ((project (org-publish-get-project-from-filename buffer-file-name)))
      (org-back-to-heading t)
      (org-reprise-export-entry project))))

(defun org-reprise-export-blog (&optional filename)
  "Export all entries in project files that have a :ol: keyword
and a \"WEB_CAT\".  Property drawers are exported as
front-matters, outline entry title is the exported document
title. "
  (interactive)
  (save-excursion
    (setq org-reprise-new-buffers nil)
    (let ((project (org-publish-get-project-from-filename 
                    (if filename
                        filename
                      (buffer-file-name)))))
     (mapc 
      (lambda (jfile)
        (if (string= (file-name-extension jfile) "org")
            (with-current-buffer (org-get-reprise-file-buffer jfile)
              ;; It fails for non-visible entries, CONTENT visibility
              ;; mode ensures that all of them are visible.
              (org-content)
              (org-map-entries (lambda () (org-reprise-export-entry project))
                               "ol+WEB_CAT<>\"\""))))
      (org-publish-get-base-files project)))
    (org-release-buffers org-reprise-new-buffers)))

(provide 'org-reprise)
