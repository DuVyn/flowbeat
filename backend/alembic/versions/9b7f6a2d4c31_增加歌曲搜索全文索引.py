"""增加歌曲搜索全文索引

Revision ID: 9b7f6a2d4c31
Revises: ec8c1eb3ec2c
Create Date: 2026-04-24 15:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b7f6a2d4c31"
down_revision: Union[str, Sequence[str], None] = "ec8c1eb3ec2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return

    # 优先使用 ngram parser 以提升中文检索命中；若当前实例不可用则退化为默认 parser。
    try:
        op.execute(
            sa.text(
                """
                CREATE FULLTEXT INDEX ix_songs_search_ft
                ON songs (name, artist_name, song_id)
                WITH PARSER ngram
                """
            )
        )
    except Exception:
        op.execute(
            sa.text(
                """
                CREATE FULLTEXT INDEX ix_songs_search_ft
                ON songs (name, artist_name, song_id)
                """
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return

    op.execute(sa.text("DROP INDEX ix_songs_search_ft ON songs"))
