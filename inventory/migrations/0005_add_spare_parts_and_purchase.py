# Generated manually for spare parts shop ERP

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_remove_product_cost_price_alter_product_brand_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('contact', models.CharField(blank=True, max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='cost_price',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='product',
            name='purpose',
            field=models.CharField(blank=True, help_text='Part purpose e.g. DIFFERENTIAL PINION', max_length=150),
        ),
        migrations.AddField(
            model_name='product',
            name='vehicle_application',
            field=models.TextField(blank=True, help_text='Car/vehicle types this part fits'),
        ),
        migrations.AlterField(
            model_name='product',
            name='location',
            field=models.CharField(blank=True, help_text='Physical storage location (shelf, bin)', max_length=150),
        ),
        migrations.AlterField(
            model_name='product',
            name='part_number',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.category'),
        ),
        migrations.CreateModel(
            name='Purchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('notes', models.CharField(blank=True, max_length=200)),
                ('total_amount', models.FloatField(default=0)),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.supplier')),
            ],
        ),
        migrations.CreateModel(
            name='PurchaseItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('unit_cost', models.FloatField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.product')),
                ('purchase', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='inventory.purchase')),
            ],
        ),
    ]
