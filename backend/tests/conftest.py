import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base

@pytest.fixture
def db_session():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    S=sessionmaker(bind=engine); db=S()
    try: yield db
    finally: db.close()
