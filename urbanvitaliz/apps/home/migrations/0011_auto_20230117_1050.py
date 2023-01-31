# Generated by Django 3.2.16 on 2023-01-17 09:50

import django.db.models.manager
import urbanvitaliz.apps.home.models
from django.contrib.sites import models as sites_models
from django.db import migrations, models
from django.db.models import Q


def assign_sites_to_users(apps, schema_editor):
    UserProfile = apps.get_model("home", "UserProfile")
    Site = apps.get_model("sites", "Site")

    # Assign guessable user sites (either advisor or project member)
    for profile in UserProfile.objects.all():
        sites = Site.objects.filter(
            Q(project__members=profile.user) | Q(project__switchtenders=profile.user)
        ).distinct()
        profile.sites.set(sites)

    # Everyone else is assigned to SITE 1if exists
    try:
        default = Site.objects.get(pk=1)
    except Site.DoesNotExist:
        return
    for profile in UserProfile.objects.filter(sites=None):
        profile.sites.add(default)


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0002_alter_domain_unique"),
        ("home", "0010_alter_siteconfiguration_site"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="userprofile",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("on_site", urbanvitaliz.apps.home.models.UserProfileOnSiteManager()),
            ],
        ),
        migrations.AddField(
            model_name="userprofile",
            name="sites",
            field=models.ManyToManyField(to="sites.Site"),
        ),
        migrations.RunPython(assign_sites_to_users, lambda x, y: None),
    ]
