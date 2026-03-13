# Generated manually to create Customer model and add customer foreign key to Sale

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0005_saleitem_cost_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('credit_limit', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ],
        ),
        migrations.AddField(
            model_name='sale',
            name='customer',
            field=models.ForeignKey(blank=True, help_text='Customer who made the purchase', null=True, on_delete=models.SET_NULL, to='sales.customer'),
        ),
    ]
