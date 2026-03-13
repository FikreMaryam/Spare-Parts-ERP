# Generated manually: add Warehouse, StockMovement, Account, JournalEntry & update Purchase

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0007_add_chassis_prefixes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('location', models.CharField(blank=True, max_length=150)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('movement_type', models.CharField(choices=[('purchase','Purchase'),('sale','Sale'),('adjustment','Adjustment'),('transfer','Transfer')], max_length=20)),
                ('reference', models.CharField(blank=True, max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=models.CASCADE, to='inventory.product')),
                ('warehouse', models.ForeignKey(blank=True, help_text='Warehouse where the movement occurred', null=True, on_delete=models.SET_NULL, to='inventory.warehouse')),
            ],
        ),
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(blank=True, max_length=20)),
                ('parent', models.ForeignKey(null=True, blank=True, on_delete=models.CASCADE, related_name='children', to='inventory.account')),
            ],
            options={
                'verbose_name_plural': 'accounts',
            },
        ),
        migrations.CreateModel(
            name='JournalEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('description', models.TextField(blank=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('credit_account', models.ForeignKey(on_delete=models.CASCADE, related_name='credits', to='inventory.account')),
                ('debit_account', models.ForeignKey(on_delete=models.CASCADE, related_name='debits', to='inventory.account')),
            ],
        ),
        migrations.AddField(
            model_name='purchase',
            name='warehouse',
            field=models.ForeignKey(blank=True, help_text='Where the goods are received', null=True, on_delete=models.SET_NULL, to='inventory.warehouse'),
        ),
    ]
