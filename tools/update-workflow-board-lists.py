#!/usr/bin/env python3
#
# SPDX-License-Identifier: GPL-2.0
#
# Regenerate the `board` and `maintainer` workflow_dispatch dropdown options in a
# build workflow, from the Armbian build framework's board configs.
#
# It is surgical: only the lines between the marker comments
#     # >>> board-options ...   / # <<< board-options
#     # >>> maintainer-options ... / # <<< maintainer-options
# are rewritten, so the rest of the workflow is left untouched.
#
#   python3 tools/update-workflow-board-lists.py \
#       --build ./build \
#       --workflow .github/workflows/build-all-stable.yml
#
# Board list  = every board config except end-of-support (*.eos), matching the
#               "all not eos" target set used for stable builds.
# Maintainers = unique BOARD_MAINTAINER handles across all board configs.
# Both lists are alphabetically sorted and always led by "all".

import argparse
import glob
import os
import re
import sys

BOARD_EXTS = ("conf", "wip", "tvb", "csc")            # not .eos (end of support)
MAINTAINER_EXTS = ("conf", "eos", "wip", "tvb", "csc")  # every board, incl. eos


def _board_files(boards_dir, exts):
    for path in glob.glob(os.path.join(boards_dir, "*")):
        if os.path.isfile(path) and path.rsplit(".", 1)[-1] in exts:
            yield path


def board_slugs(boards_dir):
    slugs = {
        os.path.basename(p).rsplit(".", 1)[0]
        for p in _board_files(boards_dir, BOARD_EXTS)
    }
    return sorted(slugs, key=str.lower)


def maintainers(boards_dir):
    handles = set()
    for path in _board_files(boards_dir, MAINTAINER_EXTS):
        with open(path, errors="ignore") as fh:
            for line in fh:
                if line.lstrip().startswith("#"):
                    continue
                m = re.match(r"^\s*BOARD_MAINTAINER\s*=\s*(.*)$", line)
                if not m:
                    continue
                value = re.sub(r"#.*", "", m.group(1)).replace('"', "").replace("'", "")
                handles.update(h for h in re.split(r"[\s,;]+", value.strip()) if h)
    return sorted(handles, key=str.lower)


def render_options(indent, values):
    lines = [f"{indent}- all"]
    lines += [f"{indent}- {v}" for v in values if v != "all"]
    return "\n".join(lines)


def replace_marked_block(text, name, body):
    pattern = re.compile(
        r"([ \t]*# >>> %s[^\n]*\n).*?(\n[ \t]*# <<< %s\b[^\n]*)"
        % (re.escape(name), re.escape(name)),
        re.DOTALL,
    )
    if not pattern.search(text):
        sys.exit(f"error: markers '# >>> {name}' / '# <<< {name}' not found in workflow")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", default="build", help="path to an armbian/build checkout")
    ap.add_argument("--workflow", required=True, help="workflow YAML to update in place")
    ap.add_argument("--indent", default="          ", help="indent of list items under options:")
    args = ap.parse_args()

    boards_dir = os.path.join(args.build, "config", "boards")
    if not os.path.isdir(boards_dir):
        sys.exit(f"error: board configs not found under {boards_dir}")

    boards = board_slugs(boards_dir)
    maints = maintainers(boards_dir)
    if not boards:
        sys.exit("error: no board configs found")

    with open(args.workflow) as fh:
        text = fh.read()
    text = replace_marked_block(text, "board-options", render_options(args.indent, boards))
    text = replace_marked_block(text, "maintainer-options", render_options(args.indent, maints))
    with open(args.workflow, "w") as fh:
        fh.write(text)

    print(f"updated {args.workflow}: {len(boards)} boards, {len(maints)} maintainers")


if __name__ == "__main__":
    main()
