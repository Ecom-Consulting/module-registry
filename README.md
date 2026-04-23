# Ecom-Consulting Module Registry

Central registry for Odoo module repositories in the [Ecom-Consulting](https://github.com/Ecom-Consulting) org.

When a module repo is registered here, it is automatically added as a submodule to deployment repos (`ecom`, `odoo-apps`) via scheduled GitHub Actions — no manual submodule management needed.

---

## How it works

```
module repo pushes code
        │
        ▼
register-module.yml (in module repo)
        │  calls reusable workflow
        ▼
module-registry/.github/workflows/register.yml
        │  appends repo name to
        ▼
modules.txt  (this repo, public)
        │
        ▼  (every 6h, or manual trigger)
ecom / odoo-apps sync workflows
        │  open PRs adding new submodules
        ▼
version branches (odoo/18.0/ce, 19.0, etc.)
```

---

## Repo structure convention

Every module repo must have a **top-level folder with the same name as the repo**:

```
my_module/                        ← repo root
├── my_module/                    ← Odoo module (same name as repo)
│   ├── __manifest__.py
│   ├── __init__.py
│   ├── models/
│   ├── views/
│   └── security/
└── .github/
    └── workflows/
        └── register-module.yml
```

Version branches (`18.0`, `19.0`) each have the same structure with the `version` field in `__manifest__.py` updated accordingly.

---

## Quickstart — scaffold a new module repo

Use the scaffold script to create a new module repo with branches, GitHub repo, and auto-registration all set up in one command:

```bash
# From anywhere (needs gh CLI and git)
python scaffold.py my_module --description "What this module does"

# Split an existing module from the ecom repo
python scaffold.py my_module --from-ecom ~/ecom/addons/my_module

# Create for specific Odoo versions only
python scaffold.py my_module --versions 19.0
```

The script will:
1. Create `Ecom-Consulting/my_module` private repo on GitHub
2. Set up `18.0` and `19.0` branches with proper Odoo scaffold
3. Add the `register-module.yml` workflow
4. Register in `modules.txt` immediately

See [`scaffold.py`](./scaffold.py) for all options.

---

## Manual setup — add registration to an existing repo

Copy [`template/register-module.yml`](./template/register-module.yml) into your module repo:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/register-module.yml \
  https://raw.githubusercontent.com/Ecom-Consulting/module-registry/main/template/register-module.yml
```

Then commit and push. The workflow fires on push to `18.0`, `19.0`, or `main` and appends the repo name to `modules.txt`.

---

## Required secret: `ORG_PAT`

The register workflow needs a GitHub Personal Access Token with **`repo`** and **`read:org`** scopes.

**Option A — org-level secret (recommended):** Set `ORG_PAT` once in [Ecom-Consulting org settings](https://github.com/organizations/Ecom-Consulting/settings/secrets/actions). All repos in the org inherit it automatically.

**Option B — per-repo secret:** Add `ORG_PAT` under each module repo's Settings → Secrets → Actions.

---

## modules.txt format

One repo name per line (not full URL, just the name):

```
my_module
another_module
```

Blank lines and duplicates are ignored. The file is sorted alphabetically on each update.
