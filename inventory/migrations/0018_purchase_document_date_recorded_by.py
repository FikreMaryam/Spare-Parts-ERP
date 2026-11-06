import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0017_purchase_source_text"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="purchase",
            name="document_date",
            field=models.DateField(blank=True, help_text="Date printed on the supplier receipt", null=True),
        ),
        migrations.AddField(
            model_name="purchase",
            name="recorded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="recorded_purchases",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
