# Claude Instructions — module-registry

This is the **central public registry** for Ecom-Consulting Odoo module repositories.

## What this repo does

- `modules.txt` — source of truth listing all standalone Odoo module repos in the org
- `.github/workflows/register.yml` — reusable workflow that module repos call to self-register
- `template/register-module.yml` — copy this into new module repos
- `scaffold.py` — script to scaffold a new module repo from scratch or from ecom's addons

When `modules.txt` is updated, two sync workflows in `ecom` and `odoo-apps` automatically open PRs to add the new repo as a submodule on each Odoo version branch.

## How a new module enters the system

1. Developer runs `make add_addons name=<module>` in the `ecom` repo
2. `scaffold.py` creates the GitHub repo, sets up `main` + version branches, and writes the name to `modules.txt` immediately
3. The sync workflows in `ecom` and `odoo-apps` pick it up within 6 hours (or on manual trigger)

## Key files

| File | Purpose |
|------|---------|
| `modules.txt` | One repo name per line — the registry |
| `.github/workflows/register.yml` | Reusable workflow for registration |
| `template/register-module.yml` | Template to copy into module repos |
| `scaffold.py` | Developer tool to scaffold new module repos |

## modules.txt format

One bare repo name per line (not a URL):
```
my_module
another_module
```

Blank lines ignored. File is sorted alphabetically on each update.

---

## Before Proceeding — Ask the User

Before taking any of these actions, **always confirm with the user first**:

- Editing `modules.txt` directly (adding or removing entries)
- Running `scaffold.py` to create a new GitHub repo
- Changing the `register.yml` reusable workflow (affects all module repos that call it)
- Changing `template/register-module.yml` (affects how new repos register)

These changes affect org-wide infrastructure and all downstream module repos. Always confirm intent before modifying.
