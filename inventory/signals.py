from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PurchaseItem


@receiver(post_save, sender=PurchaseItem)
def increase_inventory_on_purchase(sender, instance, created, **kwargs):
    """Increase product quantity and update cost_price when a PurchaseItem is created.

    Cost price is updated using a weighted average to preserve historical cost data.
    """
    if created:
        product = instance.product
        old_qty = product.quantity or 0
        old_cost = product.cost_price or 0
        added_qty = instance.quantity
        unit_cost = instance.unit_cost

        # update stock quantity
        product.quantity = old_qty + added_qty

        # compute weighted average cost
        if old_qty + added_qty > 0:
            product.cost_price = ((old_cost * old_qty) + (unit_cost * added_qty)) / (old_qty + added_qty)
        else:
            product.cost_price = unit_cost

        product.save(update_fields=["quantity", "cost_price"])
