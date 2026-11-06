from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0013_sale_receipt_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="source_text",
            field=models.TextField(blank=True, help_text="Transcribed receipt text entered during parts analysis"),
        ),
    ]
