---
name: pr-description
description: Writes pull request descriptions. Use when creating a PR, writing a PR, or when the user asks to summarize changes for a pull request.
allowed-tools: Bash(git diff:*), Bash(git log:*), Bash(git status:*), Read
model: sonnet
---

When writing a PR description:

1. Run `git diff main...HEAD` to see all changes on this branch
2. Run `git log main..HEAD --oneline` to see the commit messages
3. Write a description following this format:

## What
One sentence explaining what this PR does.

## Why
Brief context on why this change is needed

## Changes
- Bullet points of specific changes made
- Group related changes together
- Mention any files deleted or renamed

## Special cases

- If the PR fixes a bug, read [references/bugfix-template.md](references/bugfix-template.md) and use that format instead.
- If the PR touches security (auth, passwords, permissions), read [references/security-checklist.md](references/security-checklist.md) and add its checklist at the end of the description.

Only read these files when the case applies.
