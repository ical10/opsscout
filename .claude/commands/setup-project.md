---
description: Full one-command project setup — wires .claude/, hooks, and generates CLAUDE.md
argument-hint: <project-name>
---

You are setting up a project for Husni's development workflow. Do all of the following steps in order without stopping for confirmation unless you hit an explicit blocker.

Project name: $ARGUMENTS (if not provided, use the current directory name)

## Step 1 — run bootstrap.sh

Run the bootstrap script from the Obsidian vault. Detect automatically:
- If CLAUDE.md already exists → use --existing flag
- If CLAUDE.md does not exist → fresh mode (no flag)

```bash
VAULT=~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/my-notes/Husni\'s\ second\ brain/dev
PROJECT_DIR=$(pwd)
PROJECT_NAME="$ARGUMENTS"
[ -z "$PROJECT_NAME" ] && PROJECT_NAME=$(basename "$PROJECT_DIR")

if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
  bash "$VAULT/hooks/bootstrap.sh" "$PROJECT_DIR" "$PROJECT_NAME" --existing
else
  bash "$VAULT/hooks/bootstrap.sh" "$PROJECT_DIR" "$PROJECT_NAME"
fi
```

## Step 2 — generate or verify CLAUDE.md

**If CLAUDE.md was just created from template (fresh project):**
- Open it and update the `name` field to match the project name
- Leave everything else as a reminder for the developer to fill in
- Print: "CLAUDE.md created from template — update stack, folder structure, and current focus manually"

**If CLAUDE.md did not exist and this is an existing project (bootstrap created a blank one), OR if no CLAUDE.md existed at all:**
Scan the codebase and generate a proper CLAUDE.md:
- Read: package.json / pyproject.toml / Cargo.toml / go.mod (whichever exist)
- Read: folder structure 2 levels deep
- Read: any linting/formatting config (ruff.toml, .eslintrc, prettier.config.js, etc.)
- Read: any test config (pytest.ini, vitest.config.ts, jest.config.js, etc.)
- Read: README.md if present
- Read: recent git log (last 10 commits): `git log --oneline -10`

Then write CLAUDE.md with these sections filled from what you found:
```
## project — name, stack, deploy, folder structure, domain
## conventions — only what is explicitly configured or clearly visible in code
## architecture decisions — only what is visible, no invention
## current focus — infer from recent commits or mark as # TODO: fill in
## rules — based on detected lint/test commands
```
Mark anything inferred (not explicitly configured) with a comment.

## Step 3 — check pre-commit hook

Read `.git/hooks/pre-commit` and check if the lint/test commands match the detected stack.
If they don't match, update the file automatically with the correct commands.
Print what was changed.

## Step 4 — done, report

Print a clean summary:
```
✓ Setup complete: [project name]

Wired:
  ✓ .claude/agents/     — 5 subagents
  ✓ .claude/commands/   — /plan, /review, /session-end, /init-codebase, /setup-project
  ✓ .claude/settings.json
  ✓ .git/hooks/pre-commit
  ✓ /plans

CLAUDE.md: [generated from scan / created from template — needs manual review]

One thing left:
  → Run /tdd-guard configure and point it at: [detected test command]
```

Do not ask for confirmation at any step. If bootstrap.sh fails, print the error and stop.
