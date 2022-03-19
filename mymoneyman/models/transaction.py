import sqlalchemy as sa
from mymoneyman import models

class Transaction(models.sql.Base):
    __tablename__ = 'transaction'

    id   = sa.Column(sa.Integer,  primary_key=True, autoincrement=True)
    date = sa.Column(sa.DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"Transaction<id={self.id} date={self.date}>"

class Subtransaction(models.sql.Base):
    __tablename__ = 'subtransaction'

    id             = sa.Column(sa.Integer,                      primary_key=True, autoincrement=True)
    transaction_id = sa.Column(sa.ForeignKey('transaction.id'), nullable=False)
    comment        = sa.Column(sa.String)
    origin_id      = sa.Column(sa.ForeignKey('account.id'),     nullable=False)
    target_id      = sa.Column(sa.ForeignKey('account.id'),     nullable=False)
    quantity       = sa.Column(models.sql.Decimal(8),           nullable=False)

    def __repr__(self) -> str:
        return (
            "Subtransaction<"
            f"id={self.id} "
            f"transaction_id={self.transaction_id} "
            f"origin_id={self.origin_id} "
            f"target_id={self.target_id} "
            f"quantity={self.quantity}"
            ">"
        )