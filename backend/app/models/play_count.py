"""全站歌曲播放次数聚合模型。

数据来源：
- 由 data/raw/train.csv 清洗聚合得到（按 song_id 统计播放次数）。

用途：
- 支撑首页热门歌曲等非个性化推荐场景，避免在线实时扫描播放明细表。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.song import Song


class PlayCount(Base):
    """歌曲播放次数聚合表（每首歌一行）。"""

    __tablename__ = "play_counts"
    __table_args__ = (
        UniqueConstraint("song_id", name="uq_play_counts_song_id"),
        # 常见查询为按播放次数倒序取 TopN，这里先提供基础索引。
        Index("ix_play_counts_total_play_count", "total_play_count"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_play_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 聚合任务最近一次计算时间，便于观测离线任务新鲜度。
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    song: Mapped["Song"] = relationship("Song", back_populates="play_count")
