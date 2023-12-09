import json
from datetime import datetime
import logging
from sqlalchemy import create_engine, select, insert
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy import Column, Integer, String, JSON

engine_path = 'sqlite:///database.db'
engine = create_engine(engine_path)

logger = logging.Logger(name='main_database', level=logging.INFO)

session = Session(engine)


class Base(DeclarativeBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug(f'[!] Таблица "{self.__tablename__}" инициализирована.')


class ChartHistory(Base):
    __tablename__ = 'chart_history'

    id = Column(
        Integer,
        name='id',
        autoincrement=True,
        primary_key=True,
        unique=True,
        nullable=False
    )

    file_name = Column(
        String(length=256),
        name='file_name',
        nullable=False
    )

    extra_data = Column(
        JSON(none_as_null=False),
        nullable=True,
        name='extra_data'
    )

    @classmethod
    def get_all_charts(cls):
        results = session.execute(select(cls)).scalars()
        return results

    @classmethod
    def get_chart(cls, chart_id: int):
        result = select(cls).where(ChartHistory.id.__eq__(chart_id))
        return session.scalar(result)

    @classmethod
    def create(cls, **kwargs):
        session.execute(
            insert(cls).values(**kwargs)
        )
        session.commit()


Base.metadata.create_all(bind=engine)
print(f'[!] База данных "{engine_path}" готова к использованию.')
