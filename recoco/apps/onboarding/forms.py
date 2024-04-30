# encoding: utf-8

"""
Forms for onboarding application

author  : guillaume.libersat@beta.gouv.fr, raphael.marvie@beta.gouv.fr
created : 2022-06-06 14:16:20 CEST
"""

import os

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from django import forms
from crispy_forms.layout import Layout, Fieldset
from recoco.apps.dsrc.forms import DsrcBaseForm
from django.shortcuts import reverse

from . import models


##################################################
# Notes
##################################################
class OnboardingResponseForm(forms.ModelForm):
    class Meta:
        model = models.OnboardingResponse
        fields = [
            "first_name",
            "last_name",
            "phone",
            "org_name",
            "email",
            "name",
            "location",
            "insee",
            "description",
            "response",
        ]

    first_name = forms.CharField(label="Prénom du contact", initial="", required=True)
    last_name = forms.CharField(label="Nom du contact", initial="", required=True)
    phone = forms.CharField(max_length=16, label="Téléphone", initial="", required=True)
    email = forms.CharField(label="Courriel", required=True)

    def clean_email(self):
        """Make sure email is lowercased"""
        email = self.cleaned_data["email"]
        return email.lower()

    org_name = forms.CharField(
        label="Nom de votre structure", initial="", required=True
    )

    name = forms.CharField(label="Nom du projet", max_length=128, required=True)
    location = forms.CharField(label="Adresse", required=False)
    postcode = forms.CharField(max_length=5, required=False, label="Code Postal")
    insee = forms.CharField(max_length=5, required=False, label="Code Insee")

    description = forms.CharField(label="Description")


class OnboardingResponseWithCaptchaForm(OnboardingResponseForm):
    class Meta:
        model = models.OnboardingResponse
        fields = [
            "first_name",
            "last_name",
            "phone",
            "org_name",
            "email",
            "name",
            "location",
            "insee",
            "description",
            "response",
            "captcha",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Skip captcha during tests
        if "PYTEST_CURRENT_TEST" in os.environ:
            self.fields.pop("captcha")

    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox(api_params={"hl": "fr"}))


class SelectCommuneForm(forms.Form):
    def __init__(self, communes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["commune"] = forms.ModelChoiceField(
            queryset=communes, widget=forms.RadioSelect, label="Votre commune :"
        )


##################################################
# Onboarding multi-step forms
##################################################
class OnboardingEmailForm(DsrcBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = "id-onboarding-email-form"  # The form id is used for validation, it must be set and unique in the page
        self.helper.form_method = "post"
        self.helper.action_button = {
            "submit": {
                "label": "Déposer votre projet",
            }
        }
        self.helper.layout = Layout(
            Fieldset(
                "",  # The first argument is the legend of the fieldset
                "email",
            ),
        )

    def clean_email(self):
        """Make sure email is lowercased"""
        email = self.cleaned_data["email"]
        return email.lower()

    email = forms.EmailField(
        label="Adresse email",
        help_text="Format attendu : prenom.nom@domaine.fr",
        required=True,
        initial="",
    )


class OnboardingSignupForm(DsrcBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = "id-onboarding-signup-form"  # The form id is used for validation, it must be set and unique in the page
        self.helper.form_method = "post"
        self.helper.action_button = {"submit": {"label": "Suivant"}}
        self.helper.form_tag = False
        self.helper.form_button = False

        self.helper.layout = Layout(
            Fieldset(
                "Créez votre compte",  # The first argument is the legend of the fieldset
                "first_name",
                "last_name",
                "org_name",
                "role",
                "email",
                "phone",
                "password",
                "captcha",
            ),
        )
        # Skip captcha during tests
        if "PYTEST_CURRENT_TEST" in os.environ:
            self.fields.pop("captcha")

    # Example clean method
    def clean_email(self):
        """Make sure email is lowercased"""
        email = self.cleaned_data["email"]
        return email.lower()

    # Messages used to provide help to the user: overload in your forms to change the messages
    def password_message_group(errors=None):
        return {
            "help_text": "Votre mot de passe doit contenir :",
            "messages": [{"text": "8 caractères minimum", "type": "info"}],
        }

    first_name = forms.CharField(label="Prénom", initial="", required=True)
    last_name = forms.CharField(label="Nom", initial="", required=True)
    org_name = forms.CharField(
        label="Nom de votre administration ou de votre entreprise",
        initial="",
    )
    role = forms.CharField(label="Fonction", initial="", required=True)

    # TODO: add an email validation, pattern / mask
    email = forms.EmailField(
        label="Adresse email",
        help_text="Format attendu : prenom.nom@domaine.fr",
        required=True,
    )

    # Password input, with a password widget, show/hide control, and a help text
    password = forms.CharField(
        label="Mot de passe",
        required=True,
        help_text="Votre mot de passe doit contenir 8 caractères minimum",
        widget=forms.PasswordInput(
            attrs={"size": "sm", "message_group": password_message_group()}
        ),
    )

    # TODO: add a phone number validation, pattern / mask
    phone = forms.CharField(
        max_length=16,
        label="Téléphone",
        initial="",
        help_text="Format attendu: 0102030405",
        required=True,
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox(api_params={"hl": "fr"}))


class OnboardingProject(DsrcBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = "id-onboarding-project-form"  # The form id is used for validation, it must be set and unique in the page
        self.helper.form_method = "post"
        self.helper.form_tag = False
        self.helper.form_button = False
        self.helper.action_button = {
            "submit": {
                "label": "Suivant",
            },
            "cancel": {
                "label": "Précédent",
                "href": reverse("onboarding-signup"),
            },
        }

        self.helper.layout = Layout(
            Fieldset(
                "",  # The first argument is the legend of the fieldset
                "name",
                "location",
                "postcode",
                "insee",
                "description",
            )
        )

    name = forms.CharField(label="Nom du projet *", initial="", required=True)
    location = forms.CharField(
        label="Adresse *",
        required=True,
        help_text="Si le projet n'a pas d'adresse exacte, donnez-nous une indication proche.",
        initial="",
    )
    postcode = forms.CharField(label="Code postal *", initial="", required=True)

    insee = forms.CharField(
        max_length=5,
        label="Commune",
        required=True,
    )

    description = forms.CharField(label="Description *", initial="", required=True)


class PrefillSetuserForm(DsrcBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = "id-prefill-setuser-form"  # The form id is used for validation, it must be set and unique in the page
        self.helper.form_method = "post"
        self.helper.action_button = {"submit": {"label": "Suivant"}}
        self.helper.form_tag = False
        self.helper.form_button = False

        self.helper.layout = Layout(
            Fieldset(
                "Pour qui remplissez-vous ce projet",  # The first argument is the legend of the fieldset
                "first_name",
                "last_name",
                "org_name",
                "role",
                "email",
                "phone",
            ),
        )

    def clean_email(self):
        """Make sure email is lowercased"""
        email = self.cleaned_data["email"]
        return email.lower()

    first_name = forms.CharField(label="Prénom", initial="", required=True)
    last_name = forms.CharField(label="Nom", initial="", required=True)
    org_name = forms.CharField(
        label="Nom de votre administration ou de votre entreprise",
        initial="",
    )
    role = forms.CharField(label="Fonction", initial="", required=True)

    # TODO: add an email validation, pattern / mask
    email = forms.EmailField(
        label="Adresse email",
        help_text="Format attendu : prenom.nom@domaine.fr",
        required=True,
        initial="",
    )

    # TODO: add a phone number validation, pattern / mask
    phone = forms.CharField(
        max_length=16,
        label="Téléphone",
        initial="",
        help_text="Format attendu: 0102030405",
        required=True,
    )


class PrefillProjectForm(DsrcBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = "id-prefill-project-form"  # The form id is used for validation, it must be set and unique in the page
        self.helper.form_method = "post"
        self.helper.form_tag = False
        self.helper.form_button = False
        self.helper.action_button = {
            "submit": {
                "label": "Suivant",
            },
            "cancel": {
                "label": "Précédent",
                "href": reverse("onboarding-prefill-set-user"),
            },
        }

        self.helper.layout = Layout(
            Fieldset(
                "",  # The first argument is the legend of the fieldset
                "name",
                "location",
                "postcode",
                "insee",
                "description",
            )
        )

    name = forms.CharField(label="Nom du projet", initial="", required=True)
    location = forms.CharField(
        label="Adresse",
        initial="",
        required=True,
        help_text="Si le projet n'a pas d'adresse exacte, donnez-nous une indication proche.",
    )
    postcode = forms.CharField(label="Code postal", initial="", required=True)

    insee = forms.CharField(
        max_length=5,
        label="Commune",
        required=True,
    )

    description = forms.CharField(label="Description", initial="", required=True)


# eof
