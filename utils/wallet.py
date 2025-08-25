from user.models import WalletTransaction


def refund_to_wallet(order, reason):
    wallet = order.user.wallet
    amount = order.total_paid

    wallet.balance += amount
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        transaction_type='Credit',
        reason=reason,
        related_order=order
    )
