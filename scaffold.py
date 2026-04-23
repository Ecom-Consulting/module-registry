#!/usr/bin/env python3
"""
Scaffold a new Ecom-Consulting Odoo module repo.

Creates a private GitHub repo, sets up Odoo version branches, adds the
auto-registration workflow, and optionally copies an existing module from
the ecom addons folder.

Usage:
  python scaffold.py <module_name> [options]
  python scaffold.py <module_name> --from-ecom ~/ecom/addons/<name>

Options:
  --versions      Comma-separated Odoo versions (default: 18.0,19.0)
  --description   Short description for the GitHub repo
  --from-ecom     Path to existing module in ecom addons to use as source
  --public        Make the GitHub repo public (default: private)
  --no-push       Only generate files locally, skip GitHub repo creation
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ORG = "Ecom-Consulting"
REGISTRY_REPO = f"{ORG}/module-registry"
WORK_DIR = Path("/tmp/scaffold_modules")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: str, cwd: Path = None, check: bool = True) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"\nCommand failed: {cmd}", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def validate_name(name: str):
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        sys.exit(f"Error: module name must be snake_case with no spaces (got: {name!r})")


# ---------------------------------------------------------------------------
# Scaffold file generators
# ---------------------------------------------------------------------------

def write_manifest(module_dir: Path, name: str, odoo_version: str, description: str):
    title = name.replace("_", " ").title()
    version_str = f"{odoo_version}.1.0.0"
    (module_dir / "__manifest__.py").write_text(
        f"""\
{{
    'name': '{title}',
    'version': '{version_str}',
    'category': 'Uncategorized',
    'summary': '{description}',
    'description': '',
    'author': 'Ecom Consulting',
    'website': 'https://github.com/{ORG}',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}}
"""
    )


def write_models(module_dir: Path, name: str):
    class_name = "".join(w.capitalize() for w in name.split("_"))
    models_dir = module_dir / "models"
    models_dir.mkdir()
    (models_dir / "__init__.py").write_text(f"from . import {name}\n")
    (models_dir / f"{name}.py").write_text(
        f"""\
from odoo import fields, models


class {class_name}(models.Model):
    _name = "{name}"
    _description = "{name.replace("_", " ").title()}"

    name = fields.Char(required=True)
"""
    )


def write_views(module_dir: Path, name: str):
    views_dir = module_dir / "views"
    views_dir.mkdir()
    (views_dir / "views.xml").write_text(
        f"""\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_{name}_list" model="ir.ui.view">
        <field name="name">{name}.list</field>
        <field name="model">{name}</field>
        <field name="arch" type="xml">
            <list>
                <field name="name"/>
            </list>
        </field>
    </record>

    <record id="view_{name}_form" model="ir.ui.view">
        <field name="name">{name}.form</field>
        <field name="model">{name}</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>
</odoo>
"""
    )


def write_security(module_dir: Path, name: str):
    security_dir = module_dir / "security"
    security_dir.mkdir()
    model_id = name.replace(".", "_")
    (security_dir / "ir.model.access.csv").write_text(
        "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
        f"access_{name}_user,{name}.user,model_{model_id},,1,0,0,0\n"
        f"access_{name}_manager,{name}.manager,model_{model_id},base.group_system,1,1,1,1\n"
    )


def create_fresh_scaffold(repo_dir: Path, name: str, odoo_version: str, description: str):
    """Generate a full Odoo module scaffold under repo_dir/<name>/."""
    module_dir = repo_dir / name
    module_dir.mkdir(parents=True)
    (module_dir / "__init__.py").write_text("from . import models\n")
    write_manifest(module_dir, name, odoo_version, description)
    write_models(module_dir, name)
    write_views(module_dir, name)
    write_security(module_dir, name)


def copy_from_ecom(repo_dir: Path, name: str, source: Path, odoo_version: str):
    """Copy existing ecom module into repo_dir/<name>/ and patch manifest version."""
    module_dir = repo_dir / name
    shutil.copytree(source, module_dir)
    manifest = module_dir / "__manifest__.py"
    if manifest.exists():
        content = manifest.read_text()
        content = re.sub(
            r"('version'\s*:\s*')[^']*(')",
            rf"\g<1>{odoo_version}.1.0.0\g<2>",
            content,
        )
        manifest.write_text(content)


def add_register_workflow(repo_dir: Path):
    workflows_dir = repo_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "register-module.yml").write_text(
        """\
name: Register Module

on:
  push:
    branches:
      - '18.0'
      - '19.0'
      - main

jobs:
  register:
    uses: Ecom-Consulting/module-registry/.github/workflows/register.yml@main
    secrets:
      ORG_PAT: ${{ secrets.ORG_PAT }}
"""
    )


# ---------------------------------------------------------------------------
# Registry update
# ---------------------------------------------------------------------------

def register_immediately(name: str):
    """Append repo name to modules.txt in the registry via GitHub API (atomic)."""
    print(f"  Registering {name} in module-registry...")
    file_data = run(f"gh api repos/{REGISTRY_REPO}/contents/modules.txt", check=False)
    if not file_data:
        print("  Warning: could not read modules.txt, skipping immediate registration")
        return

    import json, base64
    data = json.loads(file_data)
    current_sha = data["sha"]
    current_content = base64.b64decode(data["content"]).decode()

    if re.search(rf"^{re.escape(name)}$", current_content, re.MULTILINE):
        print(f"  Already registered.")
        return

    new_content = "\n".join(
        sorted({*current_content.splitlines(), name} - {""})
    ) + "\n"
    new_content_b64 = base64.b64encode(new_content.encode()).decode()

    run(
        f"gh api repos/{REGISTRY_REPO}/contents/modules.txt "
        f"--method PUT "
        f"--field message='register: {name}' "
        f"--field content='{new_content_b64}' "
        f"--field sha='{current_sha}'"
    )
    print(f"  Registered.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new Ecom-Consulting Odoo module repo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("name", help="Module name in snake_case")
    parser.add_argument(
        "--versions", default="18.0,19.0",
        help="Comma-separated Odoo versions to create branches for (default: 18.0,19.0)",
    )
    parser.add_argument("--description", default="", help="Short module description")
    parser.add_argument(
        "--from-ecom", metavar="PATH",
        help="Copy source from this path (e.g. ~/ecom/addons/my_module) instead of generating scaffold",
    )
    parser.add_argument("--public", action="store_true", help="Make repo public (default: private)")
    parser.add_argument(
        "--no-push", action="store_true",
        help="Generate files locally only, skip GitHub repo creation",
    )
    args = parser.parse_args()

    validate_name(args.name)
    name = args.name
    versions = [v.strip() for v in args.versions.split(",")]
    description = args.description or f"Odoo module: {name.replace('_', ' ').title()}"
    source_path = Path(args.from_ecom).expanduser().resolve() if args.from_ecom else None

    if source_path and not source_path.exists():
        sys.exit(f"Error: source path not found: {source_path}")

    print(f"\n{'='*50}")
    print(f"Module:   {name}")
    print(f"Versions: {', '.join(versions)}")
    print(f"Source:   {source_path or 'fresh scaffold'}")
    print(f"{'='*50}\n")

    # Prepare work directory
    repo_dir = WORK_DIR / name
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    repo_dir.mkdir(parents=True)

    # Create GitHub repo
    if not args.no_push:
        visibility = "--public" if args.public else "--private"
        print(f"Creating GitHub repo: {ORG}/{name}...")
        run(f'gh repo create {ORG}/{name} {visibility} --description "{description}"')

    # Init git
    run("git init -b _init", cwd=repo_dir)
    run('git config user.email "github-actions[bot]@users.noreply.github.com"', cwd=repo_dir)
    run('git config user.name "Ecom Consulting Bot"', cwd=repo_dir)

    if not args.no_push:
        run(f"git remote add origin git@github.com:{ORG}/{name}.git", cwd=repo_dir)

    # Build each version branch
    first_branch = True
    for version in versions:
        print(f"Setting up branch: {version}")

        # Clear any files from previous version (keep .git)
        for item in repo_dir.iterdir():
            if item.name == ".git":
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()

        if source_path:
            copy_from_ecom(repo_dir, name, source_path, version)
        else:
            create_fresh_scaffold(repo_dir, name, version, description)

        add_register_workflow(repo_dir)

        if first_branch:
            run(f"git checkout -b {version}", cwd=repo_dir)
            first_branch = False
        else:
            run(f"git checkout -b {version}", cwd=repo_dir)

        run("git add .", cwd=repo_dir)
        run(f'git commit -m "init: {name} for Odoo {version}"', cwd=repo_dir)

    # Push all branches
    if not args.no_push:
        print("\nPushing branches...")
        for version in versions:
            run(f"git push origin {version}", cwd=repo_dir)

        default_branch = versions[-1]
        run(f"gh repo edit {ORG}/{name} --default-branch {default_branch}")

        # Register immediately without waiting for the workflow
        register_immediately(name)

        print(f"\n✓ Done!")
        print(f"  Repo:     https://github.com/{ORG}/{name}")
        print(f"  Branches: {', '.join(versions)}")
        print(f"\n  Remember: add ORG_PAT as an org-level secret if not already set.")
        print(f"  https://github.com/organizations/{ORG}/settings/secrets/actions")
    else:
        print(f"\n✓ Local scaffold at: {repo_dir}")
        print(f"  Branches (local only): {', '.join(versions)}")


if __name__ == "__main__":
    main()
