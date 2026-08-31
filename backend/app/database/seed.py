"""Idempotent database seeding.

    python -m app.database.seed            # roles, categories, admin account
    python -m app.database.seed --demo     # + sample employees and projects

The bootstrap administrator password is never hardcoded: it is read from
``FIRST_ADMIN_PASSWORD``. If that variable is unset, a strong password is
generated and printed once so it can be stored in a password manager.
"""
import argparse
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.core import security
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.core.password_policy import PasswordPolicyError, validate_password
from app.database.base import utcnow
from app.database.session import SessionLocal
from app.models.enums import AccountStatus, ProjectStatus, RoleName, Visibility
from app.models.project import Category, Project
from app.models.user import PasswordHistory, Role, User
from app.services import project_service

logger = get_logger("seed")

ROLES = [
    (RoleName.SUPER_ADMIN, "Full control, including managing other administrators", 100),
    (RoleName.ADMIN, "Manages employees, projects and views all activity", 50),
    (RoleName.USER, "Standard employee access to permitted projects", 10),
]

CATEGORIES = [
    ("Research", "Index, market and thematic research tools", "Microscope", "#6366f1", 10),
    ("Analytics", "Dashboards and quantitative analysis", "BarChart3", "#0ea5e9", 20),
    ("Portfolio", "Portfolio construction, audit and review", "Briefcase", "#10b981", 30),
    ("Finance", "Accounting, billing and financial reporting", "Landmark", "#f59e0b", 40),
    ("Automation", "Scheduled jobs and workflow automation", "Workflow", "#8b5cf6", 50),
    ("Data", "Data pipelines, quality and reference data", "Database", "#14b8a6", 60),
    ("Reporting", "Client and regulatory reporting", "FileText", "#ec4899", 70),
    ("Operations", "Day-to-day operational tooling", "Settings2", "#64748b", 80),
    ("Internal Tools", "General-purpose internal applications", "Wrench", "#f43f5e", 90),
    ("Other", "Anything that does not fit elsewhere", "Boxes", "#94a3b8", 100),
]

DEMO_PROJECTS = [
    {
        "name": "MSCI Review Dashboard",
        "url": "https://example.internal/msci-review",
        "short_description": "Automated MSCI index review analysis and backtesting.",
        "description": (
            "Runs the full MSCI index review workflow: candidate screening, "
            "inclusion/exclusion probability, and historical backtests of review outcomes."
        ),
        "category": "Research",
        "tags": ["MSCI", "Index", "Backtesting"],
        "icon": "TrendingUp",
        "featured": True,
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "Portfolio Audit Tool",
        "url": "https://example.internal/portfolio-audit",
        "short_description": "Client portfolio analysis, exposure checks and drift reporting.",
        "description": (
            "Uploads a client portfolio and produces exposure, concentration and "
            "mandate-breach reporting with a downloadable audit pack."
        ),
        "category": "Portfolio",
        "tags": ["Portfolio", "Audit", "Compliance"],
        "icon": "ShieldCheck",
        "featured": True,
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "IPO Analysis Workbench",
        "url": "https://example.internal/ipo-analysis",
        "short_description": "IPO research, valuation comparables and listing-day analytics.",
        "category": "Research",
        "tags": ["IPO", "Research", "Valuation"],
        "icon": "Rocket",
        "featured": True,
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "Daily NAV Reconciliation",
        "url": "https://example.internal/nav-recon",
        "short_description": "Automated NAV reconciliation against custodian files.",
        "category": "Automation",
        "tags": ["NAV", "Reconciliation", "Automation"],
        "icon": "RefreshCw",
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "Factor Attribution Explorer",
        "url": "https://example.internal/factor-attribution",
        "short_description": "Multi-factor performance attribution across mandates.",
        "category": "Analytics",
        "tags": ["Factors", "Attribution", "Performance"],
        "icon": "BarChart3",
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "Client Reporting Pack Generator",
        "url": "https://example.internal/reporting-pack",
        "short_description": "Generates monthly client reporting packs in PDF.",
        "category": "Reporting",
        "tags": ["Reporting", "PDF", "Clients"],
        "icon": "FileText",
        "status": ProjectStatus.MAINTENANCE,
    },
    {
        "name": "Reference Data Quality Monitor",
        "url": "https://example.internal/refdata-quality",
        "short_description": "Tracks completeness and staleness of security master data.",
        "category": "Data",
        "tags": ["Data Quality", "Reference Data"],
        "icon": "Database",
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "Brokerage Fee Analyser",
        "url": "https://example.internal/brokerage-fees",
        "short_description": "Breaks down brokerage and transaction costs by counterparty.",
        "category": "Finance",
        "tags": ["Costs", "Brokerage"],
        "icon": "Landmark",
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "Risk Limits Console",
        "url": "https://example.internal/risk-limits",
        "short_description": "Admin-only console for firm-wide risk limit overrides.",
        "category": "Operations",
        "tags": ["Risk", "Limits"],
        "icon": "AlertTriangle",
        "visibility": Visibility.ADMIN_ONLY,
        "status": ProjectStatus.ACTIVE,
    },
    {
        "name": "Sector Rotation Model",
        "url": "https://example.internal/sector-rotation",
        "short_description": "Experimental sector rotation signal — pilot group only.",
        "category": "Research",
        "tags": ["Model", "Sectors", "Pilot"],
        "icon": "Compass",
        "visibility": Visibility.SPECIFIC_EMPLOYEES,
        "status": ProjectStatus.COMING_SOON,
    },
]

DEMO_USERS = [
    ("ARWL12345", "Sofiyaan Sameer", "sofiyaan.sameer@example.com", "Research", RoleName.ADMIN),
    ("ARWL12346", "Rahul Mehta", "rahul.mehta@example.com", "Research", RoleName.USER),
    ("ARWL12347", "Amit Sharma", "amit.sharma@example.com", "Portfolio", RoleName.USER),
    ("ARWL12348", "Priya Nair", "priya.nair@example.com", "Operations", RoleName.USER),
]


def seed_roles(db: DbSession) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, description, rank in ROLES:
        role = db.execute(select(Role).where(Role.name == str(name))).scalars().first()
        if role is None:
            role = Role(name=str(name), description=description, rank=rank)
            db.add(role)
            db.flush()
            logger.info("Created role %s", name)
        else:
            role.description, role.rank = description, rank
        roles[str(name)] = role
    return roles


def seed_categories(db: DbSession) -> dict[str, Category]:
    categories: dict[str, Category] = {}
    for name, description, icon, colour, order in CATEGORIES:
        category = db.execute(
            select(Category).where(func.lower(Category.name) == name.lower())
        ).scalars().first()
        if category is None:
            category = Category(
                name=name,
                slug=project_service.unique_slug(db, Category, name),
                description=description, icon=icon, colour=colour, sort_order=order,
            )
            db.add(category)
            db.flush()
            logger.info("Created category %s", name)
        categories[name] = category
    return categories


def seed_admin(db: DbSession, roles: dict[str, Role]) -> tuple[User, str | None]:
    employee_id = settings.FIRST_ADMIN_EMPLOYEE_ID.strip().upper()
    existing = db.execute(
        select(User).where(func.lower(User.employee_id) == employee_id.lower())
    ).scalars().first()
    if existing:
        logger.info("Administrator %s already exists — leaving it untouched", employee_id)
        return existing, None

    password = settings.FIRST_ADMIN_PASSWORD
    generated = False
    if not password:
        password = security.generate_temp_password(20)
        generated = True
    else:
        try:
            validate_password(password, employee_id=employee_id)
        except PasswordPolicyError as exc:
            raise SystemExit(
                "FIRST_ADMIN_PASSWORD does not meet the password policy:\n  - "
                + "\n  - ".join(exc.errors)
            )

    admin = User(
        employee_id=employee_id,
        full_name=settings.FIRST_ADMIN_NAME,
        email=settings.FIRST_ADMIN_EMAIL.lower(),
        department="Administration",
        job_title="Portal Administrator",
        role_id=roles[str(RoleName.SUPER_ADMIN)].id,
        password_hash=security.hash_password(password),
        password_changed_at=utcnow(),
        status=str(AccountStatus.ACTIVE),
        must_change_password=generated,
    )
    db.add(admin)
    db.flush()
    db.add(
        PasswordHistory(
            user_id=admin.id, password_hash=admin.password_hash, created_at=utcnow()
        )
    )
    logger.info("Created administrator %s", employee_id)
    return admin, (password if generated else None)


def seed_demo(db: DbSession, roles: dict[str, Role], categories: dict[str, Category],
              admin: User) -> list[tuple[str, str]]:
    """Create sample employees and projects for development. Returns credentials."""
    credentials: list[tuple[str, str]] = []

    users: dict[str, User] = {}
    for employee_id, name, email, department, role in DEMO_USERS:
        user = db.execute(
            select(User).where(func.lower(User.employee_id) == employee_id.lower())
        ).scalars().first()
        if user is None:
            password = security.generate_temp_password(16)
            user = User(
                employee_id=employee_id,
                full_name=name,
                email=email,
                department=department,
                job_title="Analyst",
                role_id=roles[str(role)].id,
                password_hash=security.hash_password(password),
                password_changed_at=utcnow(),
                status=str(AccountStatus.ACTIVE),
                must_change_password=False,
                created_by_id=admin.id,
            )
            db.add(user)
            db.flush()
            db.add(PasswordHistory(
                user_id=user.id, password_hash=user.password_hash, created_at=utcnow()
            ))
            credentials.append((employee_id, password))
            logger.info("Created demo user %s", employee_id)
        users[employee_id] = user

    for spec in DEMO_PROJECTS:
        exists = db.execute(
            select(Project.id).where(func.lower(Project.name) == spec["name"].lower())
        ).first()
        if exists:
            continue
        project = Project(
            name=spec["name"],
            slug=project_service.unique_slug(db, Project, spec["name"]),
            url=spec["url"],
            short_description=spec.get("short_description"),
            description=spec.get("description") or spec.get("short_description"),
            category_id=categories[spec["category"]].id,
            owner_name=spec.get("owner", "Sofiyaan Sameer"),
            icon=spec.get("icon", "LayoutDashboard"),
            status=str(spec.get("status", ProjectStatus.ACTIVE)),
            visibility=str(spec.get("visibility", Visibility.ALL_EMPLOYEES)),
            is_featured=spec.get("featured", False),
            created_by_id=admin.id,
            updated_by_id=admin.id,
        )
        project.tags = project_service.resolve_tags(db, spec.get("tags", []))
        db.add(project)
        db.flush()

        if project.visibility == Visibility.SPECIFIC_EMPLOYEES:
            project_service.sync_permissions(
                db, project, ["ARWL12345", "ARWL12346"], admin
            )
        logger.info("Created demo project %s", project.name)

    return credentials


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the MF AR Workstation database")
    parser.add_argument(
        "--demo", action="store_true", help="also create sample employees and projects"
    )
    args = parser.parse_args()

    configure_logging()
    db = SessionLocal()
    try:
        roles = seed_roles(db)
        categories = seed_categories(db)
        admin, admin_password = seed_admin(db, roles)
        demo_credentials = seed_demo(db, roles, categories, admin) if args.demo else []
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("\n" + "=" * 68)
    print("  MF AR Workstation — seeding complete")
    print("=" * 68)
    print(f"  Administrator Employee ID : {settings.FIRST_ADMIN_EMPLOYEE_ID.upper()}")
    if admin_password:
        print(f"  Generated password        : {admin_password}")
        print("  ^ Shown once. Store it securely; you must change it at first sign-in.")
    else:
        print("  Password                  : as supplied in FIRST_ADMIN_PASSWORD"
              " (or unchanged if the account already existed)")
    if demo_credentials:
        print("\n  Demo accounts (development only):")
        for employee_id, password in demo_credentials:
            print(f"    {employee_id}  {password}")
    print("=" * 68 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
