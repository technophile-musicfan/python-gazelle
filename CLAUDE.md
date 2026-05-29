# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Create beads tasks AFTER `/superpowers:writing-plans` produces the plan — never before; tasks must reflect the plan structure
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember "insight"` for ALL persistent knowledge — search with `bd memories <keyword>`
- Do NOT use the auto-memory file system (the `~/.claude-personal/.../memory/` directory) — ignore it entirely
- **Issue ID prefix** must match the project `name` in `pyproject.toml` (`python-gazelle`). New issues get this automatically via `issue_prefix` config. If you ever find `<CURRENT_DIR>-` prefixed issues, run `bd rename <CURRENT_DIR>-<suffix> python-gazelle-<suffix>` to fix them.


## Session Completion

1. **File issues for remaining work** — create issues for anything needing follow-up
2. **Update issue status** — close finished work, update in-progress items
3. **Push beads** — `bd dolt push` before finishing the branch

> Git push is handled by `/superpowers:finishing-a-development-branch` (Workflow 2, step 11).
<!-- END BEADS INTEGRATION -->


## Development Workflows

### Workflow 1: Product Vision (Initial Design)

Use when starting a new product or defining major scope.

1. **Brainstorm vision** — `/superpowers:brainstorming`; Claude asks "what does done look like?", surfaces constraints and goals
2. **Define feature map** — second brainstorm refines into feature areas (MVP / Beta / V1) with dependency map
3. **Save brainstorm docs** to `docs/superpowers/`:
   - Vision doc: `YYYY-MM-DD_<major_scope>.md`
   - Feature map: `YYYY-MM-DD_<major_scope>_feature_map.md`
4. **Create Beads epics** — one epic per feature area, with description and sub-epic for each major feature.

> **STOP.** Workflow 1 ends here. Do NOT start Workflow 2 unless explicitly asked to work on a feature.

### Workflow 2: Feature Implementation

Use for each individual feature once the epic exists.

1. **Brainstorm** — `/superpowers:brainstorming` to surface unknowns; produces a design document saved to `docs/superpowers/<major_scope>/YYYY-MM-DD_<feature_name>_design.md`

   > **Transition after brainstorm:** The next step is ALWAYS `/opsx:propose` — prompt the user to run it. Never suggest `writing-plans` here. The brainstorming skill's terminal state says otherwise but it is WRONG for this project.

2. **Propose change spec** — `/opsx:propose` using the design doc + memory → delta spec created in `openspec/changes/`
3. **Verify delta** — make sure that the delta spec has no delta with the initial design
4. **Isolate workspace** — `/superpowers:using-git-worktrees`

   > **Pre-writing-plans gate** — steps 2 - 4 MUST be done before writing-plans. The brainstorming skill's terminal state says "invoke writing-plans" but that is WRONG for this project. Do NOT invoke writing-plans until the delta spec exists and the worktree is active.

5. **Write plan** — `/superpowers:writing-plans` using the delta spec + brainstorm design doc
6. **Create Beads issues** — create tasks/subtasks following beads conventions, linked to the parent epic

   > **Pre-implementation gate** — beads issues MUST be created before starting implementation. Do NOT proceed to step 7 until issues exist.

7. **Implement** — `/superpowers:subagent-driven-development` or `/superpowers:executing-plans`
   > **Post-subtask gate** validate the corresponding checkbox in the delta spec 

8. **Verify** — `/opsx:verify`
9. **Archive spec** — `/opsx:archive`
10. **Code review** — `/code-review` before merging
11. **Finish branch** — `/superpowers:finishing-a-development-branch` (handles git push for feature branches; satisfies the Session Completion protocol above)

### Workflow 3: Explicit bugfix implementation

Use for targeted bugfixes where a spec is overkill but the change is non-trivial.

1. **Debug** — `/superpowers:systematic-debugging` to investigate root cause and scope
2. **Create Beads issue** — `bd create --type=bug` with reproduction steps and expected behavior
3. **Isolate workspace** — `/superpowers:using-git-worktrees`
4. **Implement** — `/superpowers:executing-plans` or direct edit
5. **Verify** — run tests; confirm bug is gone and no regressions
6. **Code review** — `/code-review` before merging
7. **Finish branch** — `/superpowers:finishing-a-development-branch`

> **STOP.** Do NOT use `/opsx:propose` for bugfixes — a delta spec is not required here.

### Workflow 4: Other workflow

Use for small tasks that don't warrant a feature workflow or bugfix investigation (docs, config, dependency bumps, refactors).

1. **Create Beads issue** — `bd create --type=task` describing the change
2. **Implement** — directly, no worktree needed unless risky
3. **Code review** — `/code-review` before merging
4. **Finish branch** — `/superpowers:finishing-a-development-branch` if on a branch, or commit directly to main for trivial changes


## Build & Test

_Add your build and test commands here_

```bash
# Example:
# npm install
# npm test
```

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

_Add your project-specific conventions here_
