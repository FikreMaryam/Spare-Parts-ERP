from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0014_sale_source_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="receipt_reference",
            field=models.CharField(blank=True, help_text="Receipt number printed on the source document", max_length=100),
        ),
        migrations.AddField(
            model_name="sale",
            name="document_date",
            field=models.DateField(blank=True, help_text="Date printed on the source receipt", null=True),
        ),
    ]
