import threading
from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver

from .models import PurchaseItem, StockMovement, Product

# avoid circular import for sales
from sales.models import SaleItem

_deleting_products = threading.local()

def get_deleting_product_ids():
    if not hasattr(_deleting_products, 'ids'):
        _deleting_products.ids = set()
    return _deleting_products.ids


@receiver(pre_delete, sender=Product)
def mark_product_deleting(sender, instance, **kwargs):
    """Mark product ID in thread-local storage so cascading deletes don't trigger re-saves."""
    if instance.pk:
        instance._is_being_deleted = True
        get_deleting_product_ids().add(instance.pk)


@receiver(post_delete, sender=Product)
def unmark_product_deleting(sender, instance, **kwargs):
    """Clear product ID from thread-local storage after deletion completes."""
    if instance.pk:
        get_deleting_product_ids().discard(instance.pk)


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

        # flag to bypass manual adjustment tracking
        product._bypass_adjustment_signal = True
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
    """Decrease inventory quantity when a SaleItem is created and log movement."""
    if created:
        product = instance.product
        # make sure we have the latest quantity value
        product.refresh_from_db(fields=["quantity"])
        new_qty = (product.quantity or 0) - instance.quantity
        if new_qty < 0:
            new_qty = 0
        product.quantity = new_qty
        
        # flag to bypass manual adjustment tracking
        product._bypass_adjustment_signal = True
        product.save(update_fields=["quantity"])

        StockMovement.objects.create(
            product=product,
            quantity=-instance.quantity,
            movement_type="sale",
            reference=f"Sale#{instance.sale.id}",
            warehouse=instance.sale.warehouse,
        )


@receiver(pre_save, sender=Product)
def track_product_quantity_change(sender, instance, **kwargs):
    """Pre-save hook to determine if quantity changed on manual edit."""
    if getattr(instance, '_bypass_adjustment_signal', False) or getattr(instance, '_is_being_deleted', False) or (instance.pk in get_deleting_product_ids()):
        return
    
    if instance.id:
        try:
            old_instance = Product.objects.get(id=instance.id)
            if old_instance.quantity != instance.quantity:
                instance._qty_diff = instance.quantity - old_instance.quantity
        except Product.DoesNotExist:
            pass


@receiver(post_save, sender=Product)
def log_manual_product_adjustment(sender, instance, created, **kwargs):
    """Post-save hook to log manual inventory adjustments to StockMovement."""
    if getattr(instance, '_bypass_adjustment_signal', False) or getattr(instance, '_is_being_deleted', False) or (instance.pk in get_deleting_product_ids()):
        return
        
    if created and instance.quantity > 0:
        StockMovement.objects.create(
            product=instance,
            quantity=instance.quantity,
            movement_type="adjustment",
            reference="Initial stock on creation",
        )
    elif hasattr(instance, '_qty_diff') and instance._qty_diff != 0:
        qty_diff = instance._qty_diff
        # Delete the attribute so it doesn't double-fire if saved again in the same request
        del instance._qty_diff
        StockMovement.objects.create(
            product=instance,
            quantity=qty_diff,
            movement_type="adjustment",
            reference="Manual inventory adjustment",
        )
