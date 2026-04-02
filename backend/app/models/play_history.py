"""播放历史模型。

字段语义参考 data/raw/train.csv：
- msno -> user_id（导入阶段映射到 users.id）
- song_id -> song_id（导入阶段映射到 songs.id）

说明：
- train.csv 不包含真实播放时间，在线事件写入时可使用 played_at 记录实际播放时间。
- 该表可直接支撑“按用户最近播放倒序”的历史页面查询。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.song import Song
    from app.models.user import User


class PlayHistory(Base):
    """用户歌曲播放历史。"""

    __tablename__ = "play_histories"
    __table_args__ = (
        # 历史页核心查询：按 user_id 过滤并按 played_at 倒序分页。
        Index("ix_play_histories_user_played_at", "user_id", "played_at"),
        # 便于歌曲维度分析最近播放趋势。
        Index("ix_play_histories_song_played_at", "song_id", "played_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    song_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="play_histories")
    song: Mapped["Song"] = relationship("Song", back_populates="play_histories")
