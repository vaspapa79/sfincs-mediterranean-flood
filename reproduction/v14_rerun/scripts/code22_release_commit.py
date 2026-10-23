"""CODE-22 step 3 — the v1.4.2 release-metadata commit and the re-created tag.

The commit's parent is the number-freeze commit (--base, 779a8e0 after the history rewrite) and its tree is the freeze tree with
exactly the listed files taken from --src (the commit on the main line that carries them): `git diff <base> v1.4.2` then lists those
files and nothing else. It is built with a temporary index (read-tree / update-index / write-tree / commit-tree), so the working
tree, the index and every branch are untouched. With --tag, the annotated tag is re-created on the new commit with the message of the
existing tag (verbatim; the previous tag object is kept under refs/backup/code22/tags/<tag>). The procedure and its checks are
written to --out.

Usage: python -I code22_release_commit.py --repo <worktree> --base 779a8e0 --src HEAD --message-file <msg> --files <f1> <f2> ...
       [--tag v1.4.2] [--out reproduction/v14_rerun/code22/release_commit.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def git(repo: Path, *args: str, env: dict | None = None, inp: str | None = None) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", env=env, input=inp)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def build_side_commit(repo: Path, base: str, src: str, files: list[str], message: str) -> str:
    """Commit with parent `base` whose tree is base's tree with `files` added or replaced by their versions in `src`."""
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(d) / "index"))
        git(repo, "read-tree", base, env=env)
        for f in files:
            ls = git(repo, "ls-tree", src, "--", f)
            if not ls:
                raise SystemExit(f"{f} is not in {src}")
            mode, typ, blob = ls.split("\t")[0].split()
            if typ != "blob":
                raise SystemExit(f"{f} is a {typ} in {src}")
            git(repo, "update-index", "--add", "--cacheinfo", f"{mode},{blob},{f}", env=env)
        tree = git(repo, "write-tree", env=env)
        msg = Path(d) / "msg"
        msg.write_text(message, encoding="utf-8")
        return git(repo, "commit-tree", tree, "-p", base, "-F", str(msg))


def tag_message(repo: Path, tag_obj: str) -> str:
    raw = subprocess.run(["git", "-C", str(repo), "cat-file", "tag", tag_obj], capture_output=True, check=True).stdout.decode("utf-8")
    return raw.split("\n\n", 1)[1]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--base", required=True)
    ap.add_argument("--src", default="HEAD")
    ap.add_argument("--message-file", required=True, type=Path)
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--out", type=Path, default=Path("reproduction/v14_rerun/code22/release_commit.json"))
    a = ap.parse_args()
    repo = a.repo.resolve()
    base = git(repo, "rev-parse", f"{a.base}^{{commit}}")
    src = git(repo, "rev-parse", f"{a.src}^{{commit}}")
    files = sorted(a.files)
    commit = build_side_commit(repo, base, src, files, a.message_file.read_text(encoding="utf-8"))
    diff = sorted(git(repo, "diff", "--name-only", base, commit).splitlines())
    same_blobs = {f: git(repo, "rev-parse", f"{commit}:{f}") == git(repo, "rev-parse", f"{src}:{f}") for f in files}
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code22_release_commit.py",
           "base_freeze_commit": base, "src_commit": src, "files": files, "commit": commit,
           "commit_subject": git(repo, "log", "-1", "--format=%s", commit), "commit_parent": git(repo, "rev-parse", f"{commit}^"),
           "diff_base_commit": diff, "diff_is_exactly_the_files": diff == files, "blobs_equal_to_src": same_blobs,
           "diff_stat": git(repo, "diff", "--stat", base, commit)}
    if a.tag:
        ref = f"refs/tags/{a.tag}"
        old_obj = git(repo, "rev-parse", ref)
        old_target = git(repo, "rev-parse", f"{ref}^{{commit}}")
        old_msg = tag_message(repo, old_obj)
        old_tagger = git(repo, "for-each-ref", "--format=%(taggername) %(taggeremail) %(taggerdate:iso-strict)", ref)
        backup = f"refs/backup/code22/tags/{a.tag}"
        git(repo, "update-ref", backup, old_obj)
        with tempfile.TemporaryDirectory() as d:
            mf = Path(d) / "tagmsg"
            mf.write_bytes(old_msg.encode("utf-8"))
            git(repo, "tag", "-a", "-f", "--cleanup=verbatim", "-F", str(mf), a.tag, commit)
        new_obj = git(repo, "rev-parse", ref)
        rec["tag"] = {"name": a.tag, "old_tag_object": old_obj, "old_target": old_target, "old_tagger": old_tagger, "backup_ref": backup,
                      "new_tag_object": new_obj, "new_target": git(repo, "rev-parse", f"{ref}^{{commit}}"),
                      "new_tagger": git(repo, "for-each-ref", "--format=%(taggername) %(taggeremail) %(taggerdate:iso-strict)", ref),
                      "annotated": git(repo, "cat-file", "-t", new_obj) == "tag", "message_unchanged": tag_message(repo, new_obj) == old_msg,
                      "message_subject": old_msg.split("\n", 1)[0][:120],
                      "diff_old_target_new_tag": sorted(git(repo, "diff", "--name-only", old_target, a.tag).splitlines())}
        rec["tag"]["diff_old_target_new_tag_is_exactly_the_files"] = rec["tag"]["diff_old_target_new_tag"] == files
    out = repo / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if k not in ("diff_stat",)}, indent=1, ensure_ascii=False))
    print(rec["diff_stat"])
    ok = rec["diff_is_exactly_the_files"] and all(same_blobs.values()) and (not a.tag or (rec["tag"]["annotated"] and rec["tag"]["message_unchanged"]
                                                                                          and rec["tag"]["diff_old_target_new_tag_is_exactly_the_files"]))
    print("all checks:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
