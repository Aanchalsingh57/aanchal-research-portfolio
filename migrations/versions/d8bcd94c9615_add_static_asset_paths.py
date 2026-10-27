
"""Add static asset paths

Revision ID: d8bcd94c9615
Revises: 8159a639cb45
"""

from alembic import op
import sqlalchemy as sa


revision = "d8bcd94c9615"
down_revision = "8159a639cb45"
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable columns first so existing records remain valid.
    with op.batch_alter_table("blog_post") as batch_op:
        batch_op.add_column(
            sa.Column("cover_path", sa.String(length=500), nullable=True)
        )

    with op.batch_alter_table("profile") as batch_op:
        batch_op.add_column(
            sa.Column("photo_path", sa.String(length=500), nullable=True)
        )
        batch_op.add_column(
            sa.Column("cv_path", sa.String(length=500), nullable=True)
        )

    with op.batch_alter_table("project") as batch_op:
        batch_op.add_column(
            sa.Column("image_path", sa.String(length=500), nullable=True)
        )

    # Backfill existing rows before enforcing NOT NULL.
    op.execute("UPDATE blog_post SET cover_path = '' WHERE cover_path IS NULL")
    op.execute("UPDATE profile SET photo_path = '' WHERE photo_path IS NULL")
    op.execute("UPDATE profile SET cv_path = '' WHERE cv_path IS NULL")
    op.execute("UPDATE project SET image_path = '' WHERE image_path IS NULL")

    # Match the model definitions after the backfill.
    with op.batch_alter_table("blog_post") as batch_op:
        batch_op.alter_column(
            "cover_path",
            existing_type=sa.String(length=500),
            nullable=False,
        )

    with op.batch_alter_table("profile") as batch_op:
        batch_op.alter_column(
            "photo_path",
            existing_type=sa.String(length=500),
            nullable=False,
        )
        batch_op.alter_column(
            "cv_path",
            existing_type=sa.String(length=500),
            nullable=False,
        )

    with op.batch_alter_table("project") as batch_op:
        batch_op.alter_column(
            "image_path",
            existing_type=sa.String(length=500),
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table("project") as batch_op:
        batch_op.drop_column("image_path")

    with op.batch_alter_table("profile") as batch_op:
        batch_op.drop_column("cv_path")
        batch_op.drop_column("photo_path")

    with op.batch_alter_table("blog_post") as batch_op:
        batch_op.drop_column("cover_path")
