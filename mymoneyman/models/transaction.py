import sqlalchemy as sa
from mymoneyman import models

class Transaction(models.sql.Base):
    __tablename__ = 'transaction'

    id   = sa.Column(sa.Integer,  primary_key=True, autoincrement=True)
    date = sa.Column(sa.DateTime, nullable=False)

class Subtransaction(models.sql.Base):
    __tablename__ = 'subtransaction'

    id             = sa.Column(sa.Integer,                      primary_key=True, autoincrement=True)
    transaction_id = sa.Column(sa.ForeignKey('transaction.id'), nullable=False)
    comment        = sa.Column(sa.String)
    account_id     = sa.Column(sa.ForeignKey('account.id'),     nullable=False)
    quantity       = sa.Column(models.sql.Decimal(8),           nullable=False)