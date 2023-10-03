# encoding: utf-8

"""
Tests for project application, tasks

authors: raphael.marvie@beta.gouv.fr, guillaume.libersat@beta.gouv.fr
created: 2021-06-01 10:11:56 CEST
"""

import datetime

import pytest
from django.contrib.auth import models as auth
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from model_bakery.recipe import Recipe
from notifications import notify
from pytest_django.asserts import assertContains, assertRedirects
from rest_framework.test import APIClient
from urbanvitaliz.apps.communication import models as communication
from urbanvitaliz import verbs
from urbanvitaliz.apps.geomatics import models as geomatics
from urbanvitaliz.apps.reminders import models as reminders
from urbanvitaliz.apps.reminders import models as reminders_models
from urbanvitaliz.apps.projects import models as project_models
from urbanvitaliz.apps.resources import models as resources
from urbanvitaliz.utils import login

from urbanvitaliz.apps.projects import utils

from .. import models

########################################################################
# Task Recommendation
########################################################################


@pytest.mark.django_db
def test_task_recommendation_list_not_available_for_non_staff(client):
    url = reverse("projects-task-recommendation-list")
    with login(client):
        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_task_recommendation_list_available_for_staff(client):
    url = reverse("projects-task-recommendation-list")
    with login(client, groups=["example_com_staff"]):
        response = client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_task_recommendation_create_not_available_for_non_staff(client):
    url = reverse("projects-task-recommendation-create")
    with login(client):
        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_task_recommendation_available_for_staff(client):
    url = reverse("projects-task-recommendation-create")
    with login(client, groups=["example_com_staff"]):
        response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_task_recommendation_is_created(request, client):
    url = reverse("projects-task-recommendation-create")
    resource = Recipe(resources.Resource, sites=[get_current_site(request)]).make()

    data = {"text": "mew", "resource": resource.pk}
    with login(client, groups=["example_com_staff"]):
        response = client.post(url, data=data)

    assert models.TaskRecommendation.on_site.count() == 1

    assert response.status_code == 302
    newurl = reverse("projects-task-recommendation-list")
    assertRedirects(response, newurl)


@pytest.mark.django_db
def test_task_recommendation_update_not_available_for_non_staff(request, client):
    recommendation = Recipe(
        models.TaskRecommendation, site=get_current_site(request)
    ).make()
    url = reverse("projects-task-recommendation-update", args=(recommendation.pk,))
    with login(client):
        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_task_recommendation_update_available_for_staff(request, client):
    recommendation = Recipe(
        models.TaskRecommendation, site=get_current_site(request)
    ).make()
    url = reverse("projects-task-recommendation-update", args=(recommendation.pk,))
    with login(client, groups=["example_com_staff"]):
        response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_task_recommendation_is_updated(request, client):
    recommendation = Recipe(
        models.TaskRecommendation, site=get_current_site(request)
    ).make()

    url = reverse("projects-task-recommendation-update", args=(recommendation.pk,))

    data = {"text": "new-text", "resource": recommendation.resource.pk}
    with login(client, groups=["example_com_staff"]):
        response = client.post(url, data=data)

    assert response.status_code == 302
    newurl = reverse("projects-task-recommendation-list")
    assertRedirects(response, newurl)

    assert models.TaskRecommendation.on_site.count() == 1
    updated_recommendation = models.TaskRecommendation.on_site.all()[0]
    assert updated_recommendation.text == data["text"]


@pytest.mark.django_db
def test_task_suggestion_not_available_for_non_switchtender(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()
    url = reverse("projects-project-tasks-suggest", args=(project.pk,))
    with login(client):
        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_task_suggestion_when_no_survey(request, client):
    current_site = get_current_site(request)

    project = Recipe(project_models.Project, sites=[current_site]).make()
    url = reverse("projects-project-tasks-suggest", args=(project.pk,))
    with login(client) as user:
        utils.assign_observer(user, project, current_site)
        response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_task_suggestion_available_with_bare_project(request, client):
    current_site = get_current_site(request)

    Recipe(models.TaskRecommendation, condition="").make()
    project = Recipe(project_models.Project, sites=[current_site]).make()
    url = reverse("projects-project-tasks-suggest", args=(project.pk,))
    with login(client) as user:
        utils.assign_observer(user, project, current_site)
        response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_task_suggestion_available_with_filled_project(request, client):
    current_site = get_current_site(request)

    commune = Recipe(geomatics.Commune).make()
    Recipe(models.TaskRecommendation, condition="").make()
    project = Recipe(
        project_models.Project, sites=[current_site], commune=commune
    ).make()
    url = reverse("projects-project-tasks-suggest", args=(project.pk,))
    with login(client) as user:
        utils.assign_observer(user, project, current_site)
        response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_task_suggestion_available_with_localized_reco(request, client):
    current_site = get_current_site(request)

    commune = Recipe(geomatics.Commune).make()
    dept = Recipe(geomatics.Department).make()
    Recipe(
        models.TaskRecommendation,
        condition="",
        departments=[
            dept,
        ],
    ).make()
    project = Recipe(
        project_models.Project, sites=[current_site], commune=commune
    ).make()
    url = reverse("projects-project-tasks-suggest", args=(project.pk,))
    with login(client) as user:
        utils.assign_observer(user, project, current_site)
        response = client.get(url)
    assert response.status_code == 200


#
# Visit


@pytest.mark.django_db
def test_visit_task_for_project_and_redirect_for_project_owner(request, client):
    owner = Recipe(auth.User).make()

    project = Recipe(
        project_models.Project,
        sites=[get_current_site(request)],
        status="READY",
    ).make()

    utils.assign_collaborator(owner, project)

    task = Recipe(
        models.Task,
        project=project,
        site=get_current_site(request),
        visited=False,
        resource=None,
    ).make()

    with login(client, user=owner):
        response = client.get(
            reverse("projects-visit-task", args=[task.id]),
        )
    task = models.Task.on_site.all()[0]
    assert task.visited is True
    assert response.status_code == 302


@pytest.mark.django_db
def test_visit_task_for_project_and_redirect_to_resource_for_project_owner(
    request, client
):
    resource = resources.Resource()
    resource.save()

    owner = baker.make(auth.User)
    project = Recipe(
        project_models.Project,
        sites=[get_current_site(request)],
        status="READY",
    ).make()

    utils.assign_collaborator(owner, project, is_owner=True)

    task = Recipe(
        models.Task,
        site=get_current_site(request),
        project=project,
        visited=False,
        resource=resource,
    ).make()

    with login(client, user=owner):
        response = client.get(
            reverse("projects-visit-task", args=[task.id]),
        )
    task = models.Task.on_site.all()[0]
    assert task.visited is True
    assert response.status_code == 302


@pytest.mark.django_db
def test_visit_task_for_project_no_action_when_hijack(request, client):
    resource = resources.Resource()
    resource.save()

    owner = baker.make(auth.User)
    project = Recipe(
        project_models.Project,
        sites=[get_current_site(request)],
        status="READY",
    ).make()

    utils.assign_collaborator(owner, project, is_owner=True)

    task = Recipe(
        models.Task,
        site=get_current_site(request),
        project=project,
        visited=False,
        resource=resource,
    ).make()

    with login(client, username="hijacker", is_staff=True):
        # hijack user
        url = reverse("hijack:acquire")
        client.post(url, data={"user_pk": owner.pk})
        # perform request
        client.get(
            reverse("projects-visit-task", args=[task.id]),
        )

    # task visited status is unchanged
    task = models.Task.on_site.first()
    assert task.visited is False


#
# mark as done
@pytest.mark.django_db
def test_new_task_toggle_done_for_project_and_redirect_for_project_owner(
    request, client
):
    user = baker.make(auth.User)
    project = Recipe(
        project_models.Project,
        status="READY",
        sites=[get_current_site(request)],
    ).make()

    utils.assign_collaborator(user, project)

    task = Recipe(
        models.Task,
        status=models.Task.PROPOSED,
        project=project,
        visited=True,
        site=get_current_site(request),
    ).make()

    with login(client, user=user):
        response = client.post(
            reverse("projects-toggle-done-task", args=[task.id]),
        )
    task = models.Task.on_site.all()[0]
    assert task.status == models.Task.DONE
    assert response.status_code == 302


@pytest.mark.django_db
def test_done_task_toggle_done_for_project_and_redirect_for_project_owner(
    request, client
):
    user = baker.make(auth.User)
    project = Recipe(
        project_models.Project,
        status="READY",
        sites=[get_current_site(request)],
    ).make()

    utils.assign_collaborator(user, project)

    task = Recipe(
        models.Task,
        project=project,
        visited=True,
        status=models.Task.DONE,
        site=get_current_site(request),
    ).make()

    with login(client, user=user):
        response = client.post(
            reverse("projects-toggle-done-task", args=[task.id]),
        )

    task = models.Task.on_site.all()[0]
    assert task.status == models.Task.PROPOSED
    assert response.status_code == 302


@pytest.mark.django_db
def test_refuse_task_for_project_and_redirect_for_project_owner(request, client):
    user = baker.make(auth.User)

    project = Recipe(
        project_models.Project,
        status="READY",
        sites=[get_current_site(request)],
    ).make()

    utils.assign_collaborator(user, project)

    task = Recipe(
        models.Task, site=get_current_site(request), project=project, visited=False
    ).make()

    with login(client, user=user):
        response = client.post(
            reverse("projects-refuse-task", args=[task.id]),
        )
    task = models.Task.on_site.all()[0]
    assert task.status == models.Task.NOT_INTERESTED
    assert response.status_code == 302


@pytest.mark.django_db
def test_already_done_task_for_project_and_redirect_for_project_owner(request, client):
    user = baker.make(auth.User)

    project = Recipe(
        project_models.Project,
        status="READY",
        sites=[get_current_site(request)],
    ).make()

    task = Recipe(
        models.Task, site=get_current_site(request), project=project, visited=False
    ).make()

    utils.assign_collaborator(user, project)

    with login(client, user=user):
        response = client.post(
            reverse("projects-already-done-task", args=[task.id]),
        )
    task = models.Task.on_site.all()[0]
    assert task.status == models.Task.ALREADY_DONE
    assert response.status_code == 302


#
# update


@pytest.mark.django_db
def test_update_task_not_available_for_non_staff_users(request, client):
    task = Recipe(models.Task, site=get_current_site(request)).make()
    url = reverse("projects-update-task", args=[task.id])
    with login(client):
        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_update_task_available_for_advisor(request, client):
    task = Recipe(models.Task, site=get_current_site(request)).make()
    url = reverse("projects-update-task", args=[task.id])
    with login(client) as user:
        utils.assign_advisor(user, task.project)

        response = client.get(url)
    assert response.status_code == 200
    # FIXME rename add-task to edit-task ?
    assertContains(response, 'form id="form-projects-update-task"')


@pytest.mark.django_db
def test_update_task_for_project_and_redirect(request, client):
    task = Recipe(models.Task, site=get_current_site(request)).make()
    updated_on_before = task.updated_on
    url = reverse("projects-update-task", args=[task.id])

    data = {"content": "this is some content"}

    with login(client) as user:
        utils.assign_advisor(user, task.project)

        response = client.post(url, data=data)

    task = models.Task.on_site.get(id=task.id)
    assert task.content == data["content"]
    assert task.updated_on > updated_on_before
    assert task.project.updated_on == task.updated_on

    assert response.status_code == 302


@pytest.mark.django_db
def test_update_task_with_new_topic(request, client):
    task = Recipe(models.Task, site=get_current_site(request)).make()
    url = reverse("projects-update-task", args=[task.id])

    data = {"content": "this is some content", "topic_name": "A topic"}

    with login(client) as user:
        utils.assign_advisor(user, task.project)
        client.post(url, data=data)

    task = models.Task.on_site.get(id=task.id)
    assert task.topic.name == data["topic_name"]

    assert project_models.Topic.objects.count() == 1


@pytest.mark.django_db
def test_update_task_with_existing_topic_on_get(request, client):
    site = get_current_site(request)
    topic = baker.make(project_models.Topic, site=site, name="A topic")
    task = Recipe(models.Task, site=site, topic=topic).make()
    url = reverse("projects-update-task", args=[task.id])

    with login(client) as user:
        utils.assign_advisor(user, task.project)
        response = client.get(url, {"next": "next-url"})

    assert response.status_code == 200
    # test values are in form


@pytest.mark.django_db
def test_update_task_with_existing_topic(request, client):
    site = get_current_site(request)
    task = Recipe(models.Task, site=site).make()
    url = reverse("projects-update-task", args=[task.id])

    topic = baker.make(project_models.Topic, site=site, name="A topic")

    data = {"content": "this is some content", "topic_name": topic.name.upper()}

    with login(client) as user:
        utils.assign_advisor(user, task.project)
        response = client.post(url, data=data)

    assert project_models.Topic.objects.count() == 1

    task = models.Task.on_site.get(id=task.id)
    assert task.topic == topic

    assert response.status_code == 302


@pytest.mark.django_db
def test_update_task_with_document(request, client):
    task = Recipe(models.Task, site=get_current_site(request)).make()

    with login(client) as user:
        utils.assign_advisor(user, task.project)

        png = SimpleUploadedFile("img.png", b"file_content", content_type="image/png")

        response = client.post(
            reverse("projects-update-task", args=[task.id]),
            data={"the_file": png},
        )

    assert response.status_code == 302

    document = project_models.Document.objects.first()
    assert document

    task = models.Task.on_site.first()
    assert task.document.first() == document


#
# delete


@pytest.mark.django_db
def test_delete_task_not_available_for_non_staff_users(request, client):
    current_site = get_current_site(request)

    task = Recipe(models.Task, site=current_site).make()
    url = reverse("projects-delete-task", args=[task.id])
    with login(client) as user:
        utils.assign_collaborator(user, task.project)

        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_delete_task_from_project_and_redirect(request, client):
    current_site = get_current_site(request)

    task = Recipe(models.Task, site=current_site).make()

    with login(client) as user:
        utils.assign_advisor(user, task.project, current_site)
        response = client.post(reverse("projects-delete-task", args=[task.id]))
    task = models.Task.deleted_on_site.get(id=task.id)
    assert task.deleted
    assert response.status_code == 302


########################################################################
# Push Actions
########################################################################

########################################################################
# Task Notifications
########################################################################


@pytest.mark.django_db
def test_create_new_task_for_project_notify_collaborators(mocker, client, request):
    owner = baker.make(auth.User)

    project = Recipe(
        project_models.Project,
        status="READY",
        sites=[get_current_site(request)],
    ).make()

    utils.assign_collaborator(owner, project, is_owner=True)

    with login(client) as user:
        utils.assign_advisor(user, project)

        client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "noresource",
                "intent": "yeah",
                "content": "this is some content",
                "public": True,
            },
        )

    assert owner.notifications.count() == 1


@pytest.mark.django_db
def test_public_task_update_does_not_trigger_notifications(request, client):
    owner = baker.make(auth.User)

    project = Recipe(
        project_models.Project,
        status="READY",
        sites=[get_current_site(request)],
    ).make()

    utils.assign_collaborator(owner, project, is_owner=True)

    task = Recipe(
        models.Task,
        project=project,
        site=get_current_site(request),
        status=models.Task.PROPOSED,
        public=True,
    ).make()

    url = reverse("projects-update-task", args=(task.pk,))

    data = {"text": "new-text"}
    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(url, data=data)

    assert response.status_code == 302
    assert owner.notifications.count() == 0


@pytest.mark.django_db
def test_draft_task_update_triggers_notifications(request, client):
    owner = baker.make(auth.User)

    project = Recipe(
        project_models.Project,
        status="READY",
        sites=[get_current_site(request)],
    ).make()

    utils.assign_collaborator(owner, project, is_owner=True)

    task = Recipe(
        models.Task,
        status=models.Task.PROPOSED,
        project=project,
        public=False,
        site=get_current_site(request),
    ).make()

    url = reverse("projects-update-task", args=(task.pk,))

    data = {"content": "new-text", "public": True}
    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(url, data=data)

    assert response.status_code == 302
    assert owner.notifications.count() == 1


@pytest.mark.django_db
def test_notifications_are_deleted_on_task_soft_delete(request):
    user = Recipe(auth.User, username="Bob", first_name="Bobi", last_name="Joe").make()
    recipient = Recipe(auth.User).make()

    task = Recipe(models.Task, site=get_current_site(request)).make()

    notify.send(
        sender=user,
        recipient=recipient,
        verb="a reçu une notif",
        action_object=task,
        target=task.project,
    )

    assert recipient.notifications.count() == 1
    task.deleted = timezone.now()
    task.save()
    assert recipient.notifications.count() == 0


@pytest.mark.django_db
def test_created_notifications_are_deleted_when_cancelling_publishing(request):
    user = Recipe(auth.User, username="Bob", first_name="Bobi", last_name="Joe").make()
    recipient = Recipe(auth.User).make()

    task = Recipe(models.Task, public=True, site=get_current_site(request)).make()

    verb_other_than_created = "notif qui reste"

    notify.send(
        sender=user,
        recipient=recipient,
        verb=verb_other_than_created,
        action_object=task,
        target=task.project,
    )

    notify.send(
        sender=user,
        recipient=recipient,
        verb=verbs.Recommendation.CREATED,
        action_object=task,
        target=task.project,
    )

    assert recipient.notifications.count() == 2
    task.public = False
    task.save()
    assert recipient.notifications.count() == 0


@pytest.mark.django_db
def test_notifications_are_not_deleted_when_edited(request):
    user = Recipe(auth.User, username="Bob", first_name="Bobi", last_name="Joe").make()
    recipient = Recipe(auth.User).make()

    task = Recipe(models.Task, public=True, site=get_current_site(request)).make()

    notify.send(
        sender=user,
        recipient=recipient,
        verb="a reçu une notif",
        action_object=task,
        target=task.project,
    )

    assert recipient.notifications.count() == 1
    task.public = True
    task.save()
    assert recipient.notifications.count() == 1


@pytest.mark.django_db
def test_notifications_are_deleted_on_task_hard_delete(request):
    user = Recipe(auth.User).make()
    recipient = Recipe(auth.User).make()

    task = Recipe(models.Task, site=get_current_site(request)).make()

    notify.send(
        sender=user,
        recipient=recipient,
        verb="a reçu une notif",
        action_object=task,
        target=task.project,
    )

    assert recipient.notifications.count() == 1
    task.delete()
    assert recipient.notifications.count() == 0


################################################################
# Create task
################################################################


@pytest.mark.django_db
def test_create_task_not_available_for_non_staff_users(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()
    url = reverse("projects-project-create-task", args=[project.id])
    with login(client):
        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_task_available_for_switchtender(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()
    url = reverse("projects-project-create-task", args=[project.id])
    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_create_new_action_with_invalid_push_type(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()

    with login(client) as user:
        utils.assign_advisor(user, project)

        client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "blah",
                "public": True,
            },
        )
    assert models.Task.on_site.count() == 0


@pytest.mark.django_db
def test_create_new_action_as_draft(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()

    intent = "My Intent"
    content = "My Content"

    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "noresource",
                "intent": intent,
                "content": content,
            },
        )
    task = models.Task.on_site.all()[0]
    assert task.public is False
    assert task.project == project
    assert task.content == content
    assert task.intent == intent
    assert response.status_code == 302


@pytest.mark.django_db
def test_create_new_action_with_new_topic(request, client):
    site = get_current_site(request)
    project = Recipe(project_models.Project, sites=[site]).make()

    intent = "My Intent"
    content = "My Content"
    topic = "A topic"

    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "noresource",
                "intent": intent,
                "content": content,
                "topic_name": topic,
            },
        )

    # new topic is created and associated to task
    assert project_models.Topic.objects.count() == 1
    task = models.Task.on_site.first()
    assert task.topic.name == topic.capitalize()
    assert response.status_code == 302


@pytest.mark.django_db
def test_create_new_action_with_existing_topic(request, client):
    site = get_current_site(request)
    project = Recipe(project_models.Project, sites=[site]).make()
    topic = Recipe(project_models.Topic, name="A topic", site=site).make()

    intent = "My Intent"
    content = "My Content"

    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "noresource",
                "intent": intent,
                "content": content,
                "topic_name": topic.name.upper(),
            },
        )

    # existing topic is reused and associated to task
    assert project_models.Topic.objects.count() == 1
    task = models.Task.on_site.first()
    assert task.topic == topic
    assert response.status_code == 302


@pytest.mark.django_db
def test_create_new_action_without_resource(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()

    intent = "My Intent"
    content = "My Content"

    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "noresource",
                "public": True,
                "intent": intent,
                "content": content,
            },
        )
    task = models.Task.on_site.all()[0]
    assert task.project == project
    assert task.content == content
    assert task.public is True
    assert task.intent == intent
    assert task.resource is None
    assert response.status_code == 302


@pytest.mark.django_db
def test_create_new_action_with_document(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()

    intent = "My Intent"
    content = "My Content"

    with login(client, groups=["example_com_advisor"]) as user:
        utils.assign_advisor(user, project)
        png = SimpleUploadedFile("img.png", b"file_content", content_type="image/png")

        response = client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "noresource",
                "public": True,
                "intent": intent,
                "content": content,
                "the_file": png,
            },
        )

    assert response.status_code == 302

    document = project_models.Document.objects.first()
    assert document

    task = models.Task.on_site.first()
    assert task.document.first() == document


@pytest.mark.django_db
def test_create_new_action_with_single_resource(request, client):
    current_site = get_current_site(request)
    project = Recipe(project_models.Project, sites=[current_site]).make()
    resource = Recipe(
        resources.Resource,
        sites=[current_site],
        status=resources.Resource.PUBLISHED,
    ).make()

    intent = "My Intent"
    content = "My Content"

    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "single",
                "public": True,
                "resource": resource.pk,
                "intent": intent,
                "content": content,
            },
        )
    task = models.Task.on_site.first()
    assert task
    assert task.project == project
    assert task.public is True
    assert task.resource == resource
    assert response.status_code == 302


@pytest.mark.django_db
def test_create_new_action_with_multiple_resources(request, client):
    current_site = get_current_site(request)
    project = Recipe(project_models.Project, sites=[current_site]).make()
    resource1 = Recipe(
        resources.Resource,
        sites=[current_site],
        status=resources.Resource.PUBLISHED,
    ).make()
    resource2 = Recipe(
        resources.Resource,
        sites=[current_site],
        status=resources.Resource.PUBLISHED,
    ).make()

    with login(client) as user:
        utils.assign_advisor(user, project)

        response = client.post(
            reverse("projects-project-create-task", args=[project.id]),
            data={
                "push_type": "multiple",
                "public": True,
                "resources": [resource1.pk, resource2.pk],
            },
        )
    assert models.Task.on_site.count() == 2

    for task in models.Task.on_site.all():
        assert task.project == project
        assert task.public is True

    assert response.status_code == 302


@pytest.mark.django_db
def test_sort_action_up(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()
    taskA = Recipe(
        models.Task, site=get_current_site(request), project=project, priority=1000
    ).make()
    taskB = Recipe(
        models.Task, site=get_current_site(request), project=project, priority=1002
    ).make()

    with login(client) as user:
        utils.assign_advisor(user, project)

        client.post(reverse("projects-sort-task", args=[taskA.id, "up"]))

    taskA = models.Task.on_site.get(pk=taskA.id)
    taskB = models.Task.on_site.get(pk=taskB.id)

    assert taskA.order < taskB.order


@pytest.mark.django_db
def test_sort_action_down(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()
    taskA = Recipe(
        models.Task, site=get_current_site(request), project=project, priority=1000
    ).make()
    taskB = Recipe(
        models.Task, site=get_current_site(request), project=project, priority=900
    ).make()

    with login(client) as user:
        utils.assign_advisor(user, project)

        client.post(reverse("projects-sort-task", args=[taskA.id, "down"]))

    taskA = models.Task.on_site.get(pk=taskA.id)
    taskB = models.Task.on_site.get(pk=taskB.id)

    assert taskA.order > taskB.order


@pytest.mark.django_db
def test_sort_action_down_when_zero(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()
    taskA = Recipe(
        models.Task, site=get_current_site(request), project=project, priority=0
    ).make()

    with login(client) as user:
        utils.assign_advisor(user, project)

        client.post(reverse("projects-sort-task", args=[taskA.id, "down"]))

    taskA = models.Task.on_site.get(pk=taskA.id)

    assert taskA.priority == 0


@pytest.mark.django_db
def test_sort_action_up_when_no_follower(request, client):
    project = Recipe(project_models.Project, sites=[get_current_site(request)]).make()
    taskA = Recipe(
        models.Task, site=get_current_site(request), project=project, priority=1000
    ).make()

    with login(client) as user:
        utils.assign_advisor(user, project)

        client.post(reverse("projects-sort-task", args=[taskA.id, "up"]))

    taskA = models.Task.on_site.get(pk=taskA.id)

    assert taskA.priority == 1000


################################################################################
# Task Followups
################################################################################


@pytest.mark.django_db
def test_update_task_followup_not_available_for_non_creator(request, client):
    followup = Recipe(models.TaskFollowup, task__site=get_current_site(request)).make()
    url = reverse("projects-task-followup-update", args=[followup.id])
    with login(client):
        response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_update_task_followup_accesible_by_creator(request, client):
    with login(client) as user:
        followup = Recipe(
            models.TaskFollowup,
            task__site=get_current_site(request),
            who=user,
            status=0,
        ).make()
        url = reverse("projects-task-followup-update", args=[followup.id])
        response = client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_task_status_is_updated_when_a_followup_issued(request, client):
    with login(client) as user:
        followup = Recipe(
            models.TaskFollowup,
            who=user,
            task__project__status="READY",
            status=1,
            task__site=get_current_site(request),
        ).make()
        url = reverse("projects-task-followup-update", args=[followup.id])
        response = client.get(url)

    assert followup.task.status == followup.status
    assert response.status_code == 200


@pytest.mark.django_db
def test_task_status_is_updated_when_a_followup_issued_on_muted_project(
    request, client
):
    with login(client) as user:
        followup = Recipe(
            models.TaskFollowup,
            who=user,
            status=1,
            task__project__muted=True,
            task__site=get_current_site(request),
        ).make()
        url = reverse("projects-task-followup-update", args=[followup.id])
        response = client.get(url)

    assert followup.task.status == followup.status
    assert response.status_code == 200


@pytest.mark.django_db
def test_update_task_followup_by_creator(request, client):
    data = {"comment": "hello"}

    with login(client) as user:
        followup = Recipe(
            models.TaskFollowup,
            task__site=get_current_site(request),
            status=0,
            who=user,
        ).make()
        url = reverse("projects-task-followup-update", args=[followup.id])
        response = client.post(url, data=data)

    followup = models.TaskFollowup.objects.get(pk=followup.pk)
    assert followup.comment == data["comment"]
    assert response.status_code == 302


###############################################################
# Reminders
###############################################################


@pytest.mark.django_db
def test_create_reminder_for_task(request, client):
    baker.make(communication.EmailTemplate, name="rsvp_reco")

    current_site = get_current_site(request)

    project = baker.make(
        project_models.Project,
        status="READY",
        sites=[current_site],
    )
    task = baker.make(models.Task, site=current_site, project=project)

    url = reverse("projects-remind-task", args=[task.id])
    data = {"days": 5}

    with login(client) as user:
        utils.assign_collaborator(user, project, is_owner=True)
        response = client.post(url, data=data)

    assert response.status_code == 302
    reminder = reminders.Reminder.to_send.all()[0]
    assert models.TaskFollowupRsvp.objects.count() == 0
    assert reminder.recipient == project.members.first().email
    in_fifteen_days = datetime.date.today() + datetime.timedelta(days=data["days"])
    assert reminder.deadline == in_fifteen_days


@pytest.mark.django_db
def test_create_reminder_without_delay_for_task(request, client):
    baker.make(communication.EmailTemplate, name="rsvp_reco")

    task = baker.make(
        models.Task,
        project__status="READY",
        site=get_current_site(request),
    )

    url = reverse("projects-remind-task", args=[task.id])

    with login(client) as user:
        utils.assign_collaborator(user, task.project, is_owner=True)
        response = client.post(url)

    assert response.status_code == 302
    assert reminders.Reminder.to_send.count() == 1
    assert models.TaskFollowupRsvp.objects.count() == 0


@pytest.mark.django_db
def test_recreate_reminder_after_for_same_task(request, client):
    baker.make(communication.EmailTemplate, name="rsvp_reco")

    task = Recipe(
        models.Task,
        project__status="READY",
        site=get_current_site(request),
    ).make()

    url = reverse("projects-remind-task", args=[task.id])
    data = {"days": 5}
    data2 = {"days": 10}
    with login(client) as user:
        utils.assign_collaborator(user, task.project, is_owner=True)

        response = client.post(url, data=data)
        response = client.post(url, data=data2)

    assert response.status_code == 302
    reminder = reminders.Reminder.to_send.all()[0]
    assert reminders.Reminder.to_send.count() == 1
    in_ten_days = datetime.date.today() + datetime.timedelta(days=data2["days"])
    assert reminder.deadline == in_ten_days
    assert models.TaskFollowupRsvp.objects.count() == 0


@pytest.mark.django_db
def test_recreate_reminder_before_for_same_task(request, client):
    baker.make(communication.EmailTemplate, name="rsvp_reco")

    task = Recipe(
        models.Task,
        project__status="READY",
        site=get_current_site(request),
    ).make()

    url = reverse("projects-remind-task", args=[task.id])
    data = {"days": 5}
    data2 = {"days": 2}
    with login(client) as user:
        utils.assign_collaborator(user, task.project, is_owner=True)

        response = client.post(url, data=data)
        response = client.post(url, data=data2)

    assert response.status_code == 302
    assert reminders.Reminder.to_send.count() == 1
    reminder = reminders.Reminder.to_send.all()[0]
    in_two_days = datetime.date.today() + datetime.timedelta(days=data2["days"])
    assert reminder.deadline == in_two_days
    assert models.TaskFollowupRsvp.objects.count() == 0


@pytest.mark.django_db
def test_reminder_is_updated_when_a_followup_issued(request, client):
    owner = baker.make(auth.User)
    project = baker.make(
        project_models.Project,
        sites=[get_current_site(request)],
    )
    utils.assign_collaborator(owner, project, is_owner=True)

    task = baker.make(models.Task, site=get_current_site(request), project=project)

    with login(client) as user:
        utils.assign_advisor(user, project)

        url = reverse("projects-followup-task", args=[task.pk])
        response = client.post(url)

    reminder = reminders_models.Reminder.objects.first()
    assert response.status_code == 302
    assert reminder.recipient == owner.email


###############################################################
# API
###############################################################
@pytest.mark.django_db
def test_unassigned_switchtender_should_see_recommendations(request):
    site = get_current_site(request)
    task = Recipe(models.Task, site=site, project__sites=[site]).make()

    client = APIClient()

    with login(client) as user:
        utils.assign_advisor(user, task.project)

        url = reverse("project-tasks-list", args=[task.project.id])
        response = client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_unassigned_user_should_not_see_recommendations(request):
    site = get_current_site(request)
    task = Recipe(models.Task, site=site, project__sites=[site]).make()

    client = APIClient()

    with login(client):
        url = reverse("project-tasks-list", args=[task.project.id])
        response = client.get(url)

    assert response.status_code == 403


# eof