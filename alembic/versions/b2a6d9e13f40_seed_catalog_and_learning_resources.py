"""seed career catalog and learning resources

Revision ID: b2a6d9e13f40
Revises: 8c3f1e7a9b20
Create Date: 2026-11-09 08:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2a6d9e13f40"
down_revision: str | Sequence[str] | None = "8c3f1e7a9b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}

CATEGORIES = (
    ("Software Development", "software-development", "Build and maintain software applications."),
    ("Data and AI", "data-and-ai", "Analyze data and build machine-learning systems."),
    ("Cybersecurity", "cybersecurity", "Protect systems, networks, and information."),
    ("Product Design", "product-design", "Research and design useful digital experiences."),
)

SKILLS = (
    ("Python", "Programming language used for backend systems, automation, and data work."),
    ("SQL", "Query and manage relational databases."),
    ("Git", "Track changes and collaborate on source code."),
    ("REST APIs", "Design and integrate HTTP APIs."),
    ("JavaScript", "Build interactive web applications."),
    ("HTML and CSS", "Structure and style web pages."),
    ("Data Visualization", "Communicate findings with clear visual representations."),
    ("Statistics", "Use statistical methods to understand data and uncertainty."),
    ("Machine Learning", "Train and evaluate models that learn from data."),
    ("Linux", "Use and administer Linux operating systems."),
    ("Networking", "Understand network protocols, routing, and infrastructure."),
    ("Threat Modeling", "Identify and prioritize security threats."),
    ("UX Research", "Understand user needs through structured research."),
    ("Wireframing", "Plan interface structure before detailed visual design."),
)

ROLES = (
    ("Backend Developer", "backend-developer", "software-development", "Design and build server-side applications and APIs.", {
        "Python": 4, "SQL": 3, "Git": 3, "REST APIs": 4, "Linux": 2,
    }),
    ("Frontend Developer", "frontend-developer", "software-development", "Build accessible, interactive interfaces for the web.", {
        "JavaScript": 4, "HTML and CSS": 4, "Git": 2, "REST APIs": 2,
    }),
    ("Data Analyst", "data-analyst", "data-and-ai", "Turn data into useful reports and product or business insights.", {
        "SQL": 4, "Python": 3, "Data Visualization": 4, "Statistics": 3,
    }),
    ("Machine Learning Engineer", "machine-learning-engineer", "data-and-ai", "Develop and operate machine-learning applications.", {
        "Python": 4, "SQL": 2, "Statistics": 4, "Machine Learning": 5,
    }),
    ("Cybersecurity Analyst", "cybersecurity-analyst", "cybersecurity", "Monitor systems and help investigate and reduce security risks.", {
        "Linux": 4, "Networking": 4, "Threat Modeling": 3,
    }),
    ("UX/UI Designer", "ux-ui-designer", "product-design", "Research user needs and design clear, usable digital products.", {
        "UX Research": 4, "Wireframing": 4, "HTML and CSS": 2,
    }),
)

RESOURCES = (
    ("python-tutorial", "Python Tutorial", "Python Software Foundation", "https://docs.python.org/3/tutorial/", "documentation", "Python", "Official Python language tutorial."),
    ("sqlbolt-lessons", "Interactive SQL Lessons", "SQLBolt", "https://sqlbolt.com/", "practice", "SQL", "Interactive lessons for learning SQL fundamentals."),
    ("git-documentation", "Git Documentation", "Git", "https://git-scm.com/doc", "documentation", "Git", "Official documentation and learning materials for Git."),
    ("mdn-javascript-guide", "JavaScript Guide", "MDN", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "documentation", "JavaScript", "Guide to the JavaScript language and its core concepts."),
    ("mdn-html-css", "Learn web development", "MDN", "https://developer.mozilla.org/en-US/docs/Learn", "course", "HTML and CSS", "Structured learning materials for HTML, CSS, and web development."),
    ("kaggle-python", "Python Course", "Kaggle Learn", "https://www.kaggle.com/learn/python", "course", "Python", "Short practical lessons and exercises for Python."),
    ("kaggle-data-visualization", "Data Visualization Course", "Kaggle Learn", "https://www.kaggle.com/learn/data-visualization", "course", "Data Visualization", "Practical lessons on communicating data with charts."),
    ("kaggle-statistics", "Intro to Statistics", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-statistics", "course", "Statistics", "Introductory lessons and exercises in statistics."),
    ("google-ml-crash-course", "Machine Learning Crash Course", "Google", "https://developers.google.com/machine-learning/crash-course", "course", "Machine Learning", "Practical introduction to machine learning concepts."),
    ("linux-journey", "Linux Journey", "Linux Journey", "https://linuxjourney.com/", "course", "Linux", "Free guided lessons on Linux and command-line basics."),
    ("owasp-top-ten", "OWASP Top 10", "OWASP", "https://owasp.org/www-project-top-ten/", "documentation", "Threat Modeling", "Awareness resource covering common web application security risks."),
    ("cloudflare-learning-networking", "What is computer networking?", "Cloudflare", "https://www.cloudflare.com/learning/network-layer/what-is-a-computer-network/", "article", "Networking", "Introduction to computer networking concepts."),
    ("nng-ux-research", "UX Research", "Nielsen Norman Group", "https://www.nngroup.com/articles/ux-research-cheat-sheet/", "article", "UX Research", "Overview of UX research methods and when to use them."),
    ("figma-wireframing", "Guide to wireframing", "Figma", "https://www.figma.com/resource-library/what-is-wireframing/", "article", "Wireframing", "Introduction to wireframes and their role in design."),
)


def _get_or_insert(connection, table, key_column, key, values):
    existing_id = connection.scalar(
        sa.select(table.c.id).where(key_column == key)
    )
    if existing_id is not None:
        return int(existing_id)
    connection.execute(sa.insert(table).values(**values))
    inserted_id = connection.scalar(sa.select(table.c.id).where(key_column == key))
    if inserted_id is None:
        raise RuntimeError(f"Unable to seed {table.name} record {key!r}")
    return int(inserted_id)


def upgrade() -> None:
    op.create_table(
        "learning_resources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=False, server_default="en"),
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "resource_type IN ('documentation', 'course', 'video', 'article', 'practice')",
            name="ck_learning_resource_type",
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_learning_resources_slug"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_learning_resources_skill_active",
        "learning_resources",
        ["skill_id", "is_active"],
    )

    connection = op.get_bind()
    categories = sa.table(
        "career_categories",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("description", sa.Text()),
    )
    skills = sa.table(
        "skills",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
    )
    roles = sa.table(
        "career_roles",
        sa.column("id", sa.Integer()),
        sa.column("category_id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    role_skills = sa.table(
        "career_role_skills",
        sa.column("career_role_id", sa.Integer()),
        sa.column("skill_id", sa.Integer()),
        sa.column("required_level", sa.Integer()),
    )
    resources = sa.table(
        "learning_resources",
        sa.column("id", sa.Integer()),
        sa.column("slug", sa.String()),
        sa.column("skill_id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("provider", sa.String()),
        sa.column("url", sa.String()),
        sa.column("resource_type", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("language", sa.String()),
        sa.column("is_free", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )

    category_ids = {
        slug: _get_or_insert(
            connection,
            categories,
            categories.c.slug,
            slug,
            {"name": name, "slug": slug, "description": description},
        )
        for name, slug, description in CATEGORIES
    }

    skill_ids = {}
    for name, description in SKILLS:
        existing_id = connection.scalar(
            sa.select(skills.c.id).where(sa.func.lower(skills.c.name) == name.lower())
        )
        if existing_id is None:
            connection.execute(
                sa.insert(skills).values(name=name, description=description)
            )
            existing_id = connection.scalar(
                sa.select(skills.c.id).where(sa.func.lower(skills.c.name) == name.lower())
            )
        if existing_id is None:
            raise RuntimeError(f"Unable to seed skill {name!r}")
        skill_ids[name] = int(existing_id)

    for name, slug, category_slug, description, required_skills in ROLES:
        role_id = _get_or_insert(
            connection,
            roles,
            roles.c.slug,
            slug,
            {
                "name": name,
                "slug": slug,
                "category_id": category_ids[category_slug],
                "description": description,
                "is_active": True,
            },
        )
        for skill_name, required_level in required_skills.items():
            mapping_exists = connection.scalar(
                sa.select(role_skills.c.career_role_id).where(
                    role_skills.c.career_role_id == role_id,
                    role_skills.c.skill_id == skill_ids[skill_name],
                )
            )
            if mapping_exists is None:
                connection.execute(
                    sa.insert(role_skills).values(
                        career_role_id=role_id,
                        skill_id=skill_ids[skill_name],
                        required_level=required_level,
                    )
                )

    for slug, title, provider, url, resource_type, skill_name, description in RESOURCES:
        _get_or_insert(
            connection,
            resources,
            resources.c.slug,
            slug,
            {
                "slug": slug,
                "skill_id": skill_ids[skill_name],
                "title": title,
                "provider": provider,
                "url": url,
                "resource_type": resource_type,
                "description": description,
                "language": "en",
                "is_free": True,
                "is_active": True,
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_learning_resources_skill_active", table_name="learning_resources"
    )
    op.drop_table("learning_resources")
