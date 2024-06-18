# Generated by Django 5.0.6 on 2024-06-18 07:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("projects", "0099_alter_projectsite_unique_together"),
        ("projects", "0100_remove_project_sites"),
        ("projects", "0101_rename_project_sites_project_sites"),
        ("projects", "0102_remove_project_status_alter_projectsite_status"),
        ("projects", "0103_alter_projectsite_unique_together_and_more"),
        ("projects", "0104_remove_projectsite_unique_origin_site_and_more"),
    ]

    dependencies = [
        ("projects", "0098_site_to_msite"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="projectsite",
            unique_together={("project", "origin")},
        ),
        migrations.RemoveField(
            model_name="project",
            name="sites",
        ),
        migrations.RenameField(
            model_name="project",
            old_name="project_sites",
            new_name="sites",
        ),
        migrations.RemoveField(
            model_name="project",
            name="status",
        ),
        migrations.AlterField(
            model_name="projectsite",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Brouillon"),
                    ("TO_MODERATE", "En attente de modération"),
                    ("READY", "En attente"),
                    ("IN_PROGRESS", "En cours"),
                    ("DONE", "Traité"),
                    ("STUCK", "Conseil Interrompu"),
                    ("REFUSED", "Refusé"),
                ],
                default="TO_MODERATE",
                max_length=20,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="projectsite",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="projectsite",
            name="site",
            field=models.ForeignKey(
                limit_choices_to={"is_staff": True},
                on_delete=django.db.models.deletion.CASCADE,
                to="sites.site",
            ),
        ),
        migrations.AlterField(
            model_name="projectsite",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Brouillon"),
                    ("TO_PROCESS", "A traiter"),
                    ("READY", "En attente"),
                    ("IN_PROGRESS", "En cours"),
                    ("DONE", "Traité"),
                    ("STUCK", "Conseil Interrompu"),
                    ("REJECTED", "Refusé"),
                ],
                default="DRAFT",
                max_length=20,
            ),
        ),
        migrations.RenameField(
            model_name="projectsite",
            old_name="origin",
            new_name="is_origin",
        ),
        migrations.AlterField(
            model_name="projectsite",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="project_sites",
                to="projects.project",
            ),
        ),
        migrations.AddConstraint(
            model_name="projectsite",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_origin", True)),
                fields=("project", "site", "is_origin"),
                name="unique_origin_site",
            ),
        ),
    ]