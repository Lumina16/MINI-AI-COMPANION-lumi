# LUMI — Current Progress State

**Snapshot taken:**
- Local (Asia/Kuching, MYT = UTC+8): **2026-09-29 08:03 Tuesday**
- UTC: **2026-09-29 00:03 Tuesday**

**Repository:** `Lumina16/MINI-AI-COMPANION-lumi`
**Branch:** `arena/01a0ea73-mini-ai-companion-lumi` (branched from `main` @ `717d87c`)

---

## 1. State of the repository

The project has **no application code yet**. Starting point was a single initial commit
containing only a one-line `README.md`.

Files now present:

```
PROGRESS.md          <- this file
README.md            <- pre-existing, one line
docs/PROGRESS.pdf    <- rendered PDF of this progress state
tools/build_pdf.py   <- reusable text/Markdown -> PDF generator
```

## 2. Requested work

Produce a PDF for the LUMI mini-AI-companion project, and record the current progress state in
the repository, with date and time.

## 3. What is done

- [x] Progress state recorded in the repository with local + UTC timestamps.
- [x] PDF **toolchain** installed and verified working.
- [x] Reusable PDF generator written and exercised end to end.
- [x] `docs/PROGRESS.pdf` generated from this file — 2 pages, verified by text extraction.
- [ ] **The actual LUMI deliverable PDF — still blocked.** See §4.

## 4. Blocker — the source prompt never arrived

The LUMI/Astra prompt was supplied as an attachment **twice**, and **neither attempt reached the
sandbox**.

- Declared filename: `LUMI_Astra_Prompt_260929075634.pdf`
- Declared destination: `/home/user/uploads/`

Evidence gathered at snapshot time:

```
$ ls -la /home/user/uploads/
ls: cannot access '/home/user/uploads/': No such file or directory

$ stat /home/user/uploads
stat: cannot statx '/home/user/uploads': No such file or directory

$ find / -type f -iname "*astra*"
/usr/share/zoneinfo/Europe/Astrakhan          <- timezone data, not the file
/usr/share/zoneinfo/right/Europe/Astrakhan    <- timezone data, not the file
```

A content search (not a filename search) for the `%PDF-` magic bytes across the filesystem
returned no PDF file at all. `/home/user/` contains only `.bash_logout`, `.bashrc`, `.profile`,
and the repository checkout.

Because the prompt's content is unavailable, **the deliverable PDF has not been authored.** Its
requirements were not guessed at or invented. `docs/PROGRESS.pdf` is the progress-state document,
not the LUMI/Astra deliverable.

## 5. Toolchain — ready and verified

A virtualenv was created (system `pip` is blocked by PEP 668) and the PDF stack installed:

```
reportlab 5.0.1     (generation)
pypdf               (verification by text extraction)
```

The generator handles headings, paragraphs, bullets, numbered lists, blockquotes, horizontal
rules, fenced code blocks, Markdown tables, and inline bold/italic/code. It stamps every document
with MYT and UTC generation times and paginates with a footer.

Two defects were found by running it, and both were fixed:

1. Missing parent directories caused `FileNotFoundError` — now created with `mkdir(parents=True)`.
2. Markdown leaked through as literal asterisk pairs, backquotes and code fences — inline markup
   and fenced blocks are now converted, and were confirmed absent from the extracted text.

## 6. Verification performed

`docs/PROGRESS.pdf` is rebuilt from scratch after every edit to this file, then read back with
`pypdf` to confirm real content rather than trusting the byte count. Checks applied:

- Page count and extracted character count are non-trivial (text is genuinely laid out).
- Document title metadata is set.
- Expected prose, timestamps and evidence strings are present in the extracted text.
- No unconverted inline markup survives outside intentional code samples.
- File header is `%PDF-1.4` and trailer ends `startxref` then `%%EOF`.

Note on self-reference: byte size and SHA-256 of this PDF are deliberately **not** recorded here,
because the PDF embeds this file and would invalidate them on every rebuild. They are recorded in
the commit message instead.

## 7. Next step to unblock

The attachment path is not working, so use one of these instead:

1. **Paste the prompt text directly into chat** — most reliable.
2. **Commit it to the repo** and tell me the path; I will `git pull`.
3. **Provide a public URL**; I will fetch it.

On receipt:
1. Extract the required scope from the prompt.
2. Write the content to a source file and run `tools/build_pdf.py <source> <output.pdf>`.
3. Verify by text extraction, then update this file and re-stamp.

## 8. Change log

| Timestamp (MYT / UTC+8) | Timestamp (UTC) | Change |
|---|---|---|
| 2026-09-29 07:58 | 2026-09-28 23:58 | Created `PROGRESS.md`; PDF blocked on missing attachment (attempt 1). |
| 2026-09-29 08:03 | 2026-09-29 00:03 | Second attachment attempt also failed. Installed toolchain, wrote and debugged `tools/build_pdf.py`, generated and verified `docs/PROGRESS.pdf`. |
