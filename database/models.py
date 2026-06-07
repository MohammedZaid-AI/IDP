from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Float
from sqlalchemy import Text

from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Document(Base):

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)

    filename = Column(String)

    document_type = Column(String)

    language = Column(String)

    confidence = Column(Float)

    extracted_data = Column(Text)