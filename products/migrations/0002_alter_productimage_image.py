# Generated by Django 5.1.2 on 2024-11-11 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productimage",
            name="image",
            field=models.URLField(),
        ),
    ]