"""SQLAlchemy 声明式基类定义。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """项目中所有 ORM 模型的公共基类。"""

    pass
