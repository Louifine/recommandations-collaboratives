# Generated by Django 3.2.3 on 2021-08-17 11:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0013_auto_20210720_1232"),
        ("survey", "0016_auto_20210817_1033"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="project",
            field=models.OneToOneField(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="session",
                to="projects.project",
            ),
            preserve_default=False,
        ),
    ]