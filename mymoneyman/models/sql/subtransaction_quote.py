import sqlalchemy as sa
import typing
from PyQt5      import QtCore
from mymoneyman import models

class SubtransactionQuoteModel(models.AlchemicalQueryModel):
    """Provides data from transaction quotes.

    The class `SubtransactionQuoteModel` extends `AlchemicalQueryModel` to
    implement a model that's populated after transaction quotes.

    Transaction quotes are `Subtransaction` objects that have a `quote_price`
    different than 1, that is, the exchange rate between the two accounts
    in a subtransaction is not equal.

    Although the application enforces a quote price of 1 for all subtransactions
    that have the same asset on its origin and target sides, it's possible that
    the database doesn't enforce this. Thus, this class will also show entries
    for subtransactions that have a value equal to 1.
    """

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent=parent)

        S             = sa.orm.aliased(models.Subtransaction, name='s')
        T             = sa.orm.aliased(models.Transaction,    name='t')
        TargetAccount = sa.orm.aliased(models.Account,        name='tacc')
        OriginAccount = sa.orm.aliased(models.Account,        name='oacc')
        TargetAsset   = sa.orm.aliased(models.Asset,          name='tass')
        OriginAsset   = sa.orm.aliased(models.Asset,          name='oass')

        stmt = (
            sa.select(
                T.date,
                TargetAsset.scope.label('target_scope'),
                TargetAsset.code.label('target_code'),
                TargetAsset.name.label('target_name'),
                OriginAsset.scope.label('origin_scope'),
                OriginAsset.code.label('origin_code'),
                OriginAsset.name.label('origin_name'),
                S.quote_price
            )
            .select_from(S)
            .join(T,             S.transaction_id       == T.id)
            .join(TargetAccount, S.target_id            == TargetAccount.id)
            .join(OriginAccount, S.origin_id            == OriginAccount.id)
            .join(TargetAsset,   TargetAccount.asset_id == TargetAsset.id)
            .join(OriginAsset,   OriginAccount.asset_id == OriginAsset.id)
            .where((TargetAsset.id != OriginAsset.id) | (S.quote_price != sa.literal(1)))
        )

        super().setStatement(stmt)
    
    def setStatement(self, statement) -> None:
        """Reimplements `AlchemicalQueryModel.setStatement()`."""

        pass