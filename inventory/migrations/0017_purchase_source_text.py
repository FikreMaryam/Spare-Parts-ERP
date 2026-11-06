from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0016_purchase_receipt_file_alter_assemblycategory_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchase",
            name="source_text",
            field=models.TextField(blank=True, help_text="Transcribed receipt text entered during parts analysis"),
        ),
    ]
