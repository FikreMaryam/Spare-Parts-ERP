from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .models import SaleItem
from inventory.signals import get_deleting_product_ids


@receiver(pre_save, sender=SaleItem)
def store_previous_quantity(sender, instance, **kwargs):
    """Store old quantity before save so we can compute the diff on update."""
    if instance.pk:
        try:
            old = SaleItem.objects.get(pk=instance.pk)
            instance._previous_quantity = old.quantity
        except SaleItem.DoesNotExist:
            instance._previous_quantity = 0
    else:
        instance._previous_quantity = 0


@receiver(post_delete, sender=SaleItem)
def restore_inventory_on_sale_delete(sender, instance, **kwargs):
    """Restore product quantity when a SaleItem is deleted individually,
    unless the parent Product itself is currently being deleted."""
    try:
        if not instance.product_id:
            return
            
        # Check thread-local active deletion set for the product's primary key
        if instance.product_id in get_deleting_product_ids():
            return

        product = instance.product
        if getattr(product, '_is_being_deleted', False):
            return
            
        product.quantity += instance.quantity
        product._bypass_adjustment_signal = True
        product.save(update_fields=["quantity"])
    except Exception:
        pass
