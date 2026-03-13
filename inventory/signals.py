from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PurchaseItem, StockMovement

# avoid circular import for sales
from sales.models import SaleItem


@receiver(post_save, sender=PurchaseItem)
def increase_inventory_on_purchase(sender, instance, created, **kwargs):
    """Increase product quantity and update cost_price when a PurchaseItem is created.

    Cost price is updated using a weighted average to preserve historical cost data.
    A corresponding StockMovement record is also created.
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

        # log movement
        StockMovement.objects.create(
            product=product,
            quantity=added_qty,
            movement_type="purchase",
            reference=f"PO#{instance.purchase.id}",
            warehouse=instance.purchase.warehouse,
        )


@receiver(post_save, sender=SaleItem)
def deduct_stock_on_sale(sender, instance, created, **kwargs):
    """Decrease inventory quantity when a SaleItem is created and log movement.

    We refresh the product from the database before modifying so that a cached
    instance (e.g. one passed in from a test) doesn't hold stale quantity
    information.  After computing the new quantity we guard against negatives
    explicitly before saving.
    """
    if created:
        product = instance.product
        # make sure we have the latest quantity value
        product.refresh_from_db(fields=["quantity"])
        new_qty = (product.quantity or 0) - instance.quantity
        if new_qty < 0:
            new_qty = 0
        product.quantity = new_qty
        product.save(update_fields=["quantity"])

        StockMovement.objects.create(
            product=product,
            quantity=-instance.quantity,
            movement_type="sale",
            reference=f"Sale#{instance.sale.id}",
            warehouse=None,
        )
