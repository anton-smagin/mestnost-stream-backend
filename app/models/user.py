from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.like import Like
    from app.models.listen_history import ListenHistory
    from app.models.playlist import Playlist


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    playlists: Mapped[list["Playlist"]] = relationship("Playlist", back_populates="user")
    likes: Mapped[list["Like"]] = relationship("Like", back_populates="user")
    listen_history: Mapped[list["ListenHistory"]] = relationship(
        "ListenHistory", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
