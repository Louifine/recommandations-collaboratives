import datetime

import django.dispatch
from actstream import action
from actstream.models import action_object_stream
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from notifications import models as notifications_models
from notifications.signals import notify
from urbanvitaliz.apps.reminders import api as reminders_api
from urbanvitaliz.apps.reminders import models as reminders_models
from urbanvitaliz.apps.survey import signals as survey_signals
from urbanvitaliz.apps.training import utils as training_utils
from urbanvitaliz.utils import is_staff_for_site
from urbanvitaliz import verbs

from . import models
from .utils import (
    create_reminder,
    get_collaborators_for_project,
    get_notification_recipients_for_project,
    get_project_moderators,
    get_regional_actors_for_project,
    get_switchtenders_for_project,
    remove_reminder,
)

########################################################################
# Projects
########################################################################


project_submitted = django.dispatch.Signal()
project_validated = django.dispatch.Signal()

# not using default signal but our own for easier processing
project_userprojectstatus_updated = django.dispatch.Signal()

project_switchtender_joined = django.dispatch.Signal()
project_observer_joined = django.dispatch.Signal()
project_switchtender_leaved = django.dispatch.Signal()

project_member_joined = django.dispatch.Signal()

document_uploaded = django.dispatch.Signal()


@receiver(project_submitted)
def log_project_submitted(sender, site, submitter, project, **kwargs):
    action.send(project, verb=verbs.Project.SUBMITTED)


@receiver(project_submitted)
def notify_moderators_project_submitted(sender, site, submitter, project, **kwargs):
    recipients = get_project_moderators(site)

    # Notify project moderators
    notify.send(
        sender=submitter,
        recipient=recipients,
        verb=verbs.Project.SUBMITTED_OLD,
        action_object=project,
        target=project,
    )


@receiver(project_validated)
def log_project_validated(sender, site, moderator, project, **kwargs):
    action.send(project, verb=verbs.Project.VALIDATED)

    if project.status == "DRAFT" or project.muted:
        return

    # prevent crashing on misconfigured object
    if not project.owner:
        return

    # Notify regional actors of a new project
    notify.send(
        sender=project.owner,
        recipient=get_regional_actors_for_project(site, project),
        verb=verbs.Project.AVAILABLE,
        action_object=project,
        target=project,
    )


@receiver(project_switchtender_joined)
def log_project_switchtender_joined(sender, project, **kwargs):
    action.send(
        sender,
        verb=verbs.Project.BECAME_ADVISOR,
        action_object=project,
        target=project,
    )


@receiver(project_switchtender_joined)
def notify_project_switchtender_joined(sender, project, **kwargs):
    if project.status == "DRAFT" or project.muted:
        return

    recipients = get_notification_recipients_for_project(project).exclude(id=sender.id)

    notify.send(
        sender=sender,
        recipient=recipients,
        verb=verbs.Project.BECAME_ADVISOR,
        action_object=project,
        target=project,
    )


@receiver(project_observer_joined)
def log_project_observer_joined(sender, project, **kwargs):
    action.send(
        sender,
        verb=verbs.Project.BECAME_OBSERVER,
        action_object=project,
        target=project,
    )


@receiver(project_observer_joined)
def notify_project_observer_joined(sender, project, **kwargs):
    if project.status == "DRAFT" or project.muted:
        return

    recipients = get_collaborators_for_project(project).exclude(id=sender.id)

    notify.send(
        sender=sender,
        recipient=recipients,
        verb=verbs.Project.BECAME_OBSERVER,
        action_object=project,
        target=project,
    )


@receiver(project_switchtender_leaved)
def log_project_switchtender_leaved(sender, project, **kwargs):
    action.send(
        sender,
        verb=verbs.Project.LEFT_ADVISING,
        action_object=project,
        target=project,
    )


@receiver(project_switchtender_leaved)
def delete_joined_on_switchtender_leaved_if_same_day(sender, project, **kwargs):
    project_ct = ContentType.objects.get_for_model(project)
    notifications_models.Notification.on_site.filter(
        target_content_type=project_ct.pk,
        target_object_id=project.pk,
        verb=verbs.Project.BECAME_ADVISOR,
        timestamp__gte=timezone.now() - datetime.timedelta(hours=12),
    ).delete()


########################################################################
# Project Members
########################################################################


@receiver(project_member_joined)
def log_project_member_joined(sender, project, **kwargs):
    action.send(
        sender,
        verb=verbs.Project.JOINED,
        action_object=project,
        target=project,
    )


@receiver(project_member_joined)
def notify_project_member_joined(sender, project, **kwargs):
    if project.status == "DRAFT" or project.muted:
        return

    recipients = get_collaborators_for_project(project).exclude(id=sender.id)

    notify.send(
        sender=sender,
        recipient=recipients,
        verb=verbs.Project.JOINED,
        action_object=project,
        target=project,
    )


########################################################################
# Reminders
########################################################################

reminder_created = django.dispatch.Signal()


@receiver(reminder_created)
def log_reminder_created(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user,
            verb=verbs.Recommendation.REMINDER_ADDED,
            action_object=task,
            target=project,
        )


########################################################################
# Actions
########################################################################


action_created = django.dispatch.Signal()
action_visited = django.dispatch.Signal()
action_not_interested = django.dispatch.Signal()
action_blocked = django.dispatch.Signal()
action_inprogress = django.dispatch.Signal()
action_already_done = django.dispatch.Signal()
action_done = django.dispatch.Signal()
action_undone = django.dispatch.Signal()
action_commented = django.dispatch.Signal()


@receiver(action_created)
def log_action_created(sender, task, project, user, **kwargs):
    if task.public is False:
        action.send(
            user,
            verb=verbs.Recommendation.DRAFTED,
            action_object=task,
            target=project,
            public=False,
        )
    else:
        action.send(
            user, verb=verbs.Recommendation.CREATED, action_object=task, target=project
        )


@receiver(action_created)
def notify_action_created(sender, task, project, user, **kwargs):
    if task.public is False:
        return

    if project.status == "DRAFT" or project.muted:
        return

    recipients = get_notification_recipients_for_project(project).exclude(id=user.id)

    notify.send(
        sender=user,
        recipient=recipients,
        verb=verbs.Recommendation.CREATED,
        action_object=task,
        target=project,
    )

    # assign reminder in six weeks
    create_reminder(6 * 7, task, project.owner, origin=reminders_models.Reminder.STAFF)


@receiver(action_visited)
def log_action_visited(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user,
            verb=verbs.Recommendation.SEEN,
            action_object=task,
            target=project,
        )


@receiver(action_not_interested)
def log_action_not_interested(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user,
            verb=verbs.Recommendation.NOT_INTERESTED,
            action_object=task,
            target=project,
        )


@receiver(action_blocked)
def log_action_blocked(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user,
            verb=verbs.Recommendation.STUCK,
            action_object=task,
            target=project,
        )


@receiver(action_already_done)
def log_action_already_done(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user,
            verb=verbs.Recommendation.ALREADY_DONE,
            action_object=task,
            target=project,
        )


@receiver(action_done)
def log_action_done(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user,
            verb=verbs.Recommendation.DONE,
            action_object=task,
            target=project,
        )


@receiver(action_inprogress)
def log_action_inprogress(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user,
            verb=verbs.Recommendation.IN_PROGRESS,
            action_object=task,
            target=project,
        )


# FIXME to convert to action_resume ?
@receiver(action_undone)
def log_action_undone(sender, task, project, user, **kwargs):
    if not is_staff_for_site(user):
        action.send(
            user, verb=verbs.Recommendation.RESUMED, action_object=task, target=project
        )


@receiver(action_commented)
def log_action_commented(sender, task, project, user, **kwargs):
    if project.status == "DRAFT" or project.muted:
        return

    action.send(
        user,
        verb=verbs.Recommendation.COMMENTED,
        action_object=task,
        target=project,
    )


@receiver(action_commented)
def notify_action_commented(sender, task, project, user, **kwargs):
    if project.status == "DRAFT" or project.muted:
        return

    recipients = get_notification_recipients_for_project(project).exclude(id=user.id)

    notify.send(
        sender=user,
        recipient=recipients,
        verb=verbs.Recommendation.COMMENTED,
        action_object=sender,
        target=project,
    )


# In case of deletion
@receiver(pre_delete, sender=models.Note, dispatch_uid="note_hard_delete_logs")
@receiver(pre_save, sender=models.Note, dispatch_uid="note_soft_delete_logs")
def delete_activity_on_note_delete(sender, instance, **kwargs):
    if instance.deleted is None:
        return

    project_ct = ContentType.objects.get_for_model(instance)
    notifications_models.Notification.on_site.filter(
        target_content_type=project_ct.pk, target_object_id=instance.pk
    ).delete()

    action_object_stream(instance).delete()


@receiver(
    pre_delete, sender=models.Project, dispatch_uid="project_delete_notifications"
)
def delete_notifications_on_project_delete(sender, instance, **kwargs):
    project_ct = ContentType.objects.get_for_model(instance)
    notifications_models.Notification.on_site.filter(
        target_content_type=project_ct.pk, target_object_id=instance.pk
    ).delete()


def delete_task_history(
    task,
    suppress_notifications=True,
    suppress_reminders=True,
    suppress_actions=True,
    after=None,
):
    """Remove all logging history and notification if a task is deleted"""
    task_ct = ContentType.objects.get_for_model(task)
    notifications = notifications_models.Notification.on_site.filter(
        action_object_content_type_id=task_ct.pk, action_object_object_id=task.pk
    )
    actions = action_object_stream(task)

    if after:
        notifications = notifications.filter(timestamp__gte=after)
        actions = actions.filter(timestamp__gte=after)

    if suppress_notifications:
        notifications.delete()

    if suppress_actions:
        actions.delete()

    if suppress_reminders:
        reminders_api.remove_reminder_email(task)


@receiver(pre_save, sender=models.Task, dispatch_uid="task_soft_delete_notifications")
def delete_notifications_on_soft_task_delete(sender, instance, **kwargs):
    if instance.deleted is None:
        return
    delete_task_history(instance)


@receiver(
    pre_save,
    sender=models.Task,
    dispatch_uid="task_cancel_publishing_deletes_notifications",
)
def delete_notifications_on_cancel_publishing(sender, instance, **kwargs):
    if instance.pk and instance.public is False:
        delete_task_history(
            instance,
            suppress_actions=False,
            suppress_reminders=False,
            after=timezone.now() - datetime.timedelta(minutes=30),
        )


@receiver(pre_delete, sender=models.Task, dispatch_uid="task_hard_delete_notifications")
def delete_notifications_on_hard_task_delete(sender, instance, **kwargs):
    delete_task_history(instance)


######
# Notes
#####
note_created = django.dispatch.Signal()


@receiver(note_created)
def notify_note_created(sender, note, project, user, **kwargs):
    if note.public is False:
        recipients = get_switchtenders_for_project(project).exclude(id=user.id)

        verb = "a envoyé un message dans l'espace conseillers"
        action.send(
            user,
            verb=verb,
            action_object=note,
            target=project,
        )
    else:
        recipients = get_notification_recipients_for_project(project).exclude(
            id=user.id
        )

        verb = "a envoyé un message"
        action.send(
            user,
            verb=verb,
            action_object=note,
            target=project,
        )

    if project.status == "DRAFT" or project.muted:
        return

    notify.send(
        sender=user,
        recipient=recipients,
        verb=verb,
        action_object=note,
        target=project,
    )


@receiver(note_created)
def note_created_challenged(sender, note, project, user, **kwargs):
    challenge = training_utils.get_challenge_for(user, "project-conversation-writer")
    if challenge and not challenge.acquired_on:
        challenge.acquired_on = timezone.now()
        challenge.save()


################################################################
# UserProjectStatus
################################################################

@receiver(project_userprojectstatus_updated)
def project_userproject_trace_status_changes(sender, old_one, new_one, **kwargs):
    if old_one and new_one:
        if old_one.status != new_one.status:
            action.send(
                new_one.user,
                verb=verbs.Project.USER_STATUS_UPDATED,
                action_object=new_one,
                target=new_one.project,
            )


################################################################
# File Upload
################################################################

@receiver(document_uploaded)
def project_document_uploaded(sender, instance, **kwargs):
    project = instance.project
    if project.status == "DRAFT" or project.muted:
        return

    # Add a trace
    action.send(
        instance.uploaded_by,
        verb=verbs.Document.ADDED,
        action_object=instance,
        target=project,
    )

    # Notify other project's people and switchtenders
    recipients = get_notification_recipients_for_project(project).exclude(
        id=instance.uploaded_by.id
    )

    notify.send(
        sender=instance.uploaded_by,
        recipient=recipients,
        verb=verbs.Document.ADDED,
        action_object=instance,
        target=instance.project,
    )


################################################################
# Project Survey events
################################################################

@receiver(
    survey_signals.survey_session_updated,
    dispatch_uid="survey_answer_created_or_updated",
)
def log_survey_session_updated(sender, session, request, **kwargs):
    project = session.project
    user = request.user

    # If we already sent this notification less a day ago, skip it
    one_day_ago = timezone.now() - datetime.timedelta(days=1)
    if session.action_object_actions.filter(
        verb=verbs.Survey.UPDATED, timestamp__gte=one_day_ago
    ).count():
        return

    action.send(
        user,
        verb=verbs.Survey.UPDATED,
        action_object=session,
        target=session.project,
    )

    recipients = get_switchtenders_for_project(project).exclude(id=user.id)
    notify.send(
        sender=user,
        recipient=recipients,
        verb=verbs.Survey.UPDATED,
        action_object=session,
        target=project,
    )


######################################################################################
# TaskFollowup / Task Status update
######################################################################################
# TODO: we may need to rearm reminders when a followup was issued, to prevent sending it
# too soon.


@receiver(
    post_save, sender=models.TaskFollowup, dispatch_uid="taskfollowup_set_task_status"
)
def set_task_status_when_followup_is_issued(sender, instance, created, **kwargs):
    if not created:  # We don't want to notify about updates
        return

    project = instance.task.project

    task_status_signals = {
        models.Task.INPROGRESS: action_inprogress,
        models.Task.DONE: action_done,
        models.Task.ALREADY_DONE: action_already_done,
        models.Task.NOT_INTERESTED: action_not_interested,
        models.Task.BLOCKED: action_blocked,
    }

    muted = (project.status == "DRAFT") or project.muted

    # Notify about status change
    if instance.status is not None and instance.status != instance.task.status:
        instance.task.status = instance.status
        instance.task.save()

        if instance.task.project.owner:
            if instance.status not in (models.Task.NOT_INTERESTED, models.Task.BLOCKED):
                create_reminder(
                    7 * 6,
                    instance.task,
                    instance.task.project.owner,
                    reminders_models.Reminder.SYSTEM,
                )
            else:
                remove_reminder(instance.task, instance.task.project.owner)

        if not muted:
            if instance.status in task_status_signals.keys():
                signal = task_status_signals[instance.status]
                signal.send(
                    sender=models.TaskFollowup,
                    task=instance.task,
                    project=instance.task.project,
                    user=instance.who,
                )

    if not muted:
        # Notify about comment
        if instance.comment != "":
            action_commented.send(
                sender=instance,
                task=instance.task,
                project=instance.task.project,
                user=instance.who,
            )


# eof
