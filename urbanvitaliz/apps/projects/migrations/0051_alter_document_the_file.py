# Generated by Django 3.2.13 on 2022-05-31 18:04

from django.db import migrations, models
import urbanvitaliz.apps.projects.models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0050_auto_20220531_1749"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="the_file",
            field=models.FileField(
                upload_to=urbanvitaliz.apps.projects.models.Document.upload_path
            ),
        ),
    ]