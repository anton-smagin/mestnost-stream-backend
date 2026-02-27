import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.artist import Artist
    from app.models.track import Track


class Album(TimestampMixin, Base):
    __tablename__ = "albums"

    title: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=False,
    )
    cover_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    release_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    artist: Mapped["Artist"] = relationship("Artist", back_populates="albums")
    tracks: Mapped[list["Track"]] = relationship(
        "Track", back_populates="album", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("artist_id", "slug", name="uq_albums_artist_id_slug"),
        Index("ix_albums_artist_id", "artist_id"),
        Index(
            "ix_albums_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<Album id={self.id} slug={self.slug!r}>"
