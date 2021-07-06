# Generated by Django 3.2.4 on 2021-07-06 13:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0012_remove_bookmark_project"),
        ("projects", "0009_task_intent"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="resource",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="resources.resource",
            ),
        ),
    ]
