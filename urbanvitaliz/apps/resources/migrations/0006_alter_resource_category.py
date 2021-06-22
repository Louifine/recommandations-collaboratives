# Generated by Django 3.2.4 on 2021-06-22 09:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0005_alter_category_color"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resource",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="resources.category",
            ),
        ),
    ]
