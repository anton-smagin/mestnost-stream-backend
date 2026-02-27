import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.album import Album


class Track(TimestampMixin, Base):
    __tablename__ = "tracks"

    title: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("albums.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_number: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    file_key: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    album: Mapped["Album"] = relationship("Album", back_populates="tracks")

    __table_args__ = (
        UniqueConstraint("album_id", "slug", name="uq_tracks_album_id_slug"),
        Index("ix_tracks_album_id", "album_id"),
        Index("ix_tracks_album_id_track_number", "album_id", "track_number"),
        Index(
            "ix_tracks_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<Track id={self.id} slug={self.slug!r}>"
