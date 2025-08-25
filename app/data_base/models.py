from sqlalchemy import BigInteger, String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)


class Status(Base):
    __tablename__ = 'statuses'

    id: Mapped[int] = mapped_column(primary_key=True)
    state: Mapped[str] = mapped_column(String(50))


class Book(Base):
    __tablename__ = 'books'

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[int] = mapped_column(Integer(10))
    article: Mapped[int] = mapped_column(Integer(15))
    title: Mapped[str] = mapped_column(String(50))
    number: Mapped[int] = mapped_column(Integer(15))
    name: Mapped[str] = mapped_column(String(50))
    publisher: Mapped[str] = mapped_column(String(50))
    purchiser: Mapped[str] = mapped_column(String(50))
    comment: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(ForeignKey('statuses.id'))


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
