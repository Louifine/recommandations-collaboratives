# Generated by Django 4.2.11 on 2024-03-19 13:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0024_siteconfiguration_email_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteconfiguration",
            name="legal_address",
            field=models.CharField(
                blank=True,
                help_text="L'adresse postale est notamment affichée en bas des emails automatiques.",
                max_length=100,
                null=True,
                verbose_name="Adresse postale",
            ),
        ),
    ]
