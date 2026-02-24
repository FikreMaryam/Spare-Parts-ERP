from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .models import SaleItem


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


@receiver(post_save, sender=SaleItem)
def decrease_inventory_on_sale(sender, instance, created, **kwargs):
    """Decrease product quantity when a SaleItem is created or quantity is updated."""
    product = instance.product
    if created:
        product.quantity -= instance.quantity
    else:
        # Quantity was updated: adjust by the difference
        old_qty = getattr(instance, "_previous_quantity", 0)
        diff = old_qty - instance.quantity
        product.quantity += diff
    product.save(update_fields=["quantity"])


@receiver(post_delete, sender=SaleItem)
def restore_inventory_on_sale_delete(sender, instance, **kwargs):
    """Restore product quantity when a SaleItem is deleted."""
    product = instance.product
    product.quantity += instance.quantity
    product.save(update_fields=["quantity"])
