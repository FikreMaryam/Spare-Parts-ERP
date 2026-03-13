# Generated manually to add chassis_prefixes field to CarModel

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_carmake_product_reorder_level_product_sku_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='carmodel',
            name='chassis_prefixes',
            field=models.CharField(blank=True, help_text='Comma-separated chassis codes or prefixes used for quick lookup', max_length=200),
        ),
    ]
