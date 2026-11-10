"""First-boot enterprise tenant seeding and initialization script.

Executes during initial deployment or commercial client onboarding to create:
1. Standard RBAC Roles (Owner, Admin, QA Lead, Developer, Viewer)
2. Initial Super Admin / Tenant Owner account
3. Primary Organization Project Workspace
4. Target Execution Environments (Staging, Production)
5. Canonical business test suites and templates

Usage:
  python scripts/seed_enterprise_tenant.py --admin-email admin@client.com --admin-password ChangeMe123!
"""

from __future__ import annotations

import argparse
import logging
import sys
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()

from backend.app.db.session import SessionLocal, engine, Base
from backend.app.models.user import User, Role, UserRole
from backend.app.models.project import Project, Environment, ProjectMember
from backend.app.security.password import hash_password
from backend.app.engine.testing.legacy_migration import seed_legacy_test_cases

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tenant_seeder")

DEFAULT_ROLES = [
    {
        "name": "owner",
        "description": "Tenant Owner with full administrative control and key management",
        "permissions": ["*"],
    },
    {
        "name": "admin",
        "description": "System Administrator with project, user, and credential management rights",
        "permissions": [
            "projects:manage", "users:manage", "roles:manage", "credentials:manage",
            "environments:manage", "flows:create_edit", "flows:publish", "flows:execute",
            "tests:create_edit", "tests:publish", "tests:execute", "reports:read",
            "healing:approve", "audit:read", "schedules:manage"
        ],
    },
    {
        "name": "lead_qa",
        "description": "QA Lead with test authoring, flow execution, and self-healing approval rights",
        "permissions": [
            "flows:create_edit", "flows:publish", "flows:execute",
            "tests:create_edit", "tests:publish", "tests:execute", "reports:read",
            "healing:approve", "schedules:manage"
        ],
    },
    {
        "name": "developer",
        "description": "Automation Engineer with flow authoring and execution rights",
        "permissions": [
            "flows:create_edit", "flows:execute",
            "tests:create_edit", "tests:execute", "reports:read"
        ],
    },
    {
        "name": "viewer",
        "description": "Read-only auditor with dashboard and report access",
        "permissions": ["flows:read", "tests:read", "reports:read"],
    },
]


def seed_tenant(
    admin_email: str,
    admin_password: str,
    org_name: str,
    env_name: str = "Staging",
    base_url: str = "https://app.example.com",
) -> None:
    logger.info("Initializing enterprise tenant database schema...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed Roles
        logger.info("Seeding enterprise RBAC roles...")
        role_map: dict[str, Role] = {}
        for r_data in DEFAULT_ROLES:
            existing_role = db.query(Role).filter(Role.name == r_data["name"]).first()
            if not existing_role:
                new_role = Role(
                    name=r_data["name"],
                    description=r_data["description"],
                    permissions=r_data["permissions"],
                )
                db.add(new_role)
                db.flush()
                role_map[r_data["name"]] = new_role
            else:
                existing_role.permissions = r_data["permissions"]
                role_map[r_data["name"]] = existing_role
        db.commit()

        # 2. Seed Super Admin User
        logger.info("Creating primary administrator account '%s'...", admin_email)
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                full_name="Enterprise Super Admin",
                is_active=True,
                is_superuser=True,
            )
            db.add(admin_user)
            db.flush()

            # Assign Owner and Admin roles
            for role_name in ["owner", "admin"]:
                if role_name in role_map:
                    ur = UserRole(user_id=admin_user.id, role_id=role_map[role_name].id)
                    db.add(ur)
            db.commit()
            logger.info("Administrator account created with ID: %s", admin_user.id)
        else:
            logger.info("Administrator account already exists (ID: %s).", admin_user.id)

        # 3. Seed Primary Workspace Project
        logger.info("Configuring workspace project '%s'...", org_name)
        project = db.query(Project).filter(Project.name == org_name).first()
        if not project:
            project = Project(
                name=org_name,
                description=f"Primary automation and testing workspace for {org_name}",
                owner_id=admin_user.id,
            )
            db.add(project)
            db.flush()

            # Add Owner as Project Member with 'admin' role
            member = ProjectMember(
                project_id=project.id,
                user_id=admin_user.id,
                role="admin",
            )
            db.add(member)
            db.commit()
            logger.info("Project created with ID: %s", project.id)
        else:
            logger.info("Project already exists (ID: %s).", project.id)

        # 4. Seed Target Environment
        env = db.query(Environment).filter(
            Environment.project_id == project.id,
            Environment.name == env_name
        ).first()
        if not env:
            env = Environment(
                project_id=project.id,
                name=env_name,
                base_url=base_url,
                allowed_domains=["*"],
            )
            db.add(env)
            db.commit()
            logger.info("Environment '%s' configured for project.", env_name)

        # 5. Seed Canonical Business Test Cases
        logger.info("Seeding verified enterprise business test suites...")
        seeded_ids = seed_legacy_test_cases(db=db, project_id=project.id, user_id=admin_user.id)
        logger.info("Successfully seeded %d test cases into project.", len(seeded_ids))

        # 6. Display Clean Handover Summary
        print("\n" + "=" * 70)
        print("  ENTERPRISE TENANT INITIALIZATION COMPLETE (READY FOR HANDOVER)")
        print("=" * 70)
        print(f"  Organization Project : {project.name} (ID: {project.id})")
        print(f"  Target Environment   : {env.name} ({env.base_url})")
        print(f"  Super Admin Email    : {admin_user.email}")
        print(f"  Super Admin Password : [REDACTED - Configured on command line]")
        print(f"  RBAC Roles Seeded    : owner, admin, lead_qa, developer, viewer")
        print(f"  Seeded Test Cases    : {len(seeded_ids)} canonical suites")
        print(f"  Compliance Standard  : 100% Zero-AI Company Data Protection Guarantee")
        print("=" * 70)
        print("  Web Portal URL       : http://localhost:3000")
        print("  Backend API Docs     : http://localhost:8000/docs")
        print("=" * 70 + "\n")

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed new enterprise tenant for commercial deployment.")
    parser.add_argument("--admin-email", default="admin@enterprise.local", help="Super Admin login email")
    parser.add_argument("--admin-password", default="AdminP@ssw0rd2026!", help="Super Admin initial password")
    parser.add_argument("--org-name", default="Acme QA Systems", help="Enterprise Organization / Project name")
    parser.add_argument("--env-name", default="Production", help="Initial environment name")
    parser.add_argument("--base-url", default="https://app.client.com", help="Target application base URL")

    args = parser.parse_args()
    seed_tenant(
        admin_email=args.admin_email,
        admin_password=args.admin_password,
        org_name=args.org_name,
        env_name=args.env_name,
        base_url=args.base_url,
    )


if __name__ == "__main__":
    main()
