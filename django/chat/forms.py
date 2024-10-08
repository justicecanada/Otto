from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from autocomplete import HTMXAutoComplete
from autocomplete.widgets import Autocomplete
from data_fetcher.util import get_request

from chat.models import QA_MODE_CHOICES, QA_SCOPE_CHOICES, Chat, ChatOptions
from librarian.models import DataSource, Document, Library

CHAT_MODELS = [
    ("gpt-4o-mini", _("GPT-4o-mini (Global)")),
    ("gpt-4o", _("GPT-4o (Global)")),
    ("gpt-4", _("GPT-4 (Canada)")),
    ("gpt-35", _("GPT-3.5 (Canada)")),
]
SUMMARIZE_STYLES = [
    ("short", _("Short")),
    ("medium", _("Medium")),
    ("long", _("Long")),
]
TEMPERATURES = [
    (0.1, _("Precise")),
    (0.7, _("Balanced")),
    (1.2, _("Creative")),
]
LANGUAGES = [("en", _("English")), ("fr", _("French"))]


class GroupedLibraryChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        if not self.user:
            raise ValueError("User must be provided to GroupedLibraryChoiceField")
        super().__init__(queryset=Library.objects.all(), *args, **kwargs)
        print(f"GroupedLibraryChoiceField initialized with user: {self.user}")
        print(f"Initial queryset count: {self.queryset.count()}")

    def get_grouped_choices(self):
        print(f"get_grouped_choices called for user: {self.user}")
        if not self.user:
            raise ValueError("User must be provided to GroupedLibraryChoiceField")

        public_libraries = list(self.queryset.filter(is_public=True))
        managed_libraries = [
            library
            for library in list(self.queryset.filter(is_public=False))
            if self.user.has_perm("librarian.edit_library", library)
        ]
        shared_libraries = [
            library
            for library in list(self.queryset.filter(is_public=False))
            if self.user.has_perm("librarian.view_library", library)
            and not self.user.has_perm("librarian.edit_library", library)
        ]

        groups = [
            (_("JUS-managed"), public_libraries),
            (_("Managed by me"), managed_libraries),
            (_("Shared with me"), shared_libraries),
        ]

        choices = [
            (group, [(lib.pk, str(lib)) for lib in libs])
            for group, libs in groups
            if libs
        ]

        print(
            f"Returning {len(choices)} groups with a total of {sum(len(options) for _, options in choices)} options"
        )
        print(f"Choices: {choices}")
        return choices

    def label_from_instance(self, obj):
        return str(obj)

    @property
    def choices(self):
        return self.get_grouped_choices()


class DataSourcesAutocomplete(HTMXAutoComplete):
    """Autocomplete component to select Data Sources from a library"""

    name = "qa_data_sources"
    multiselect = True
    minimum_search_length = 0
    model = DataSource

    def get_items(self, search=None, values=None):
        request = get_request()
        library_id = request.GET.get("library_id", None)
        chat_id = request.GET.get("chat_id", None)
        if library_id:
            library = (
                Library.objects.filter(pk=library_id)
                .prefetch_related("data_sources")
                .first()
            )
            data = library.data_sources.all()
            if chat_id and library.is_personal_library:
                chat = Chat.objects.get(pk=chat_id)
                if DataSource.objects.filter(chat=chat).exists():
                    data = list(data)
                    data.insert(0, chat.data_source)
                    data[0].name_en = "This chat"
                    data[0].name_fr = "Ce chat"
        else:
            data = DataSource.objects.all()
        if search is not None:
            items = [
                {"label": str(x), "value": str(x.id)}
                for x in data
                if search == "" or str(search).upper() in f"{x}".upper()
            ]
            return items
        if values is not None:
            items = [
                {"label": str(x), "value": str(x.id)}
                for x in data
                if str(x.id) in values
            ]
            return items

        return []


class DocumentsAutocomplete(HTMXAutoComplete):
    """Autocomplete component to select Documents from a library"""

    name = "qa_documents"
    multiselect = True
    minimum_search_length = 0
    model = Document

    def get_items(self, search=None, values=None):
        request = get_request()
        library_id = request.GET.get("library_id", None)
        if library_id:
            data = Document.objects.filter(data_source__library_id=library_id)
        else:
            data = Document.objects.all()
        if search is not None:
            items = [
                {"label": str(x), "value": str(x.id)}
                for x in data
                if search == "" or str(search).upper() in f"{x}".upper()
            ]
            return items
        if values is not None:
            items = [
                {"label": str(x), "value": str(x.id)}
                for x in data
                if str(x.id) in values
            ]
            return items

        return []


class ChatOptionsForm(ModelForm):
    class Meta:
        model = ChatOptions
        fields = "__all__"
        exclude = ["chat", "user", "global_default", "preset_name"]
        widgets = {
            "mode": forms.HiddenInput(attrs={"onchange": "triggerOptionSave();"}),
            "chat_temperature": forms.Select(
                choices=TEMPERATURES,
                attrs={
                    "class": "form-select form-select-sm",
                    "onchange": "triggerOptionSave();",
                },
            ),
            "summarize_style": forms.Select(
                choices=SUMMARIZE_STYLES,
                attrs={
                    "class": "form-select form-select-sm",
                    "onchange": "triggerOptionSave();",
                },
            ),
            "qa_mode": forms.Select(
                choices=QA_MODE_CHOICES,
                attrs={
                    "class": "form-select form-select-sm",
                    "onchange": "limitScopeSelect(); updateQaSourceForms(); triggerOptionSave();",
                },
            ),
            "qa_scope": forms.Select(
                choices=QA_SCOPE_CHOICES,
                attrs={
                    "class": "form-select form-select-sm",
                    "onchange": "updateQaSourceForms(); triggerOptionSave();",
                },
            ),
            "chat_agent": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input small",
                    "onchange": "triggerOptionSave();",
                    "style": "filter: saturate(0); margin-top: 6px;",
                }
            ),
            # QA advanced options are shown in a different form so they can be hidden
            "qa_system_prompt": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_prompt_template": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_pre_instructions": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_post_instructions": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_topk": forms.HiddenInput(attrs={"onchange": "triggerOptionSave();"}),
            "qa_vector_ratio": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_source_order": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_answer_mode": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_prune": forms.HiddenInput(attrs={"onchange": "triggerOptionSave();"}),
            "qa_granularity": forms.HiddenInput(
                attrs={"onchange": "triggerOptionSave();"}
            ),
            "qa_rewrite": forms.HiddenInput(attrs={"onchange": "triggerOptionSave();"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(ChatOptionsForm, self).__init__(*args, **kwargs)
        # Each of chat_model, summarize_model, qa_model
        # should be a choice field with the available models
        for field in [
            "chat_model",
            "summarize_model",
            "qa_model",
        ]:
            self.fields[field].widget = forms.Select(
                choices=CHAT_MODELS,
                attrs={
                    "class": "form-select form-select-sm",
                    "onchange": "triggerOptionSave();",
                },
            )

        # summarize_language and translate_language have choices "en", "fr"
        for field in ["summarize_language", "translate_language"]:
            self.fields[field].widget = forms.Select(
                choices=LANGUAGES,
                attrs={
                    "class": "form-select form-select-sm",
                    "onchange": "triggerOptionSave();",
                },
            )

        # Text areas
        for field in [
            "chat_system_prompt",
            "summarize_prompt",
        ]:
            self.fields[field].widget = forms.Textarea(
                attrs={
                    "class": "form-control form-control-sm",
                    "rows": 5,
                    "onkeyup": "triggerOptionSave();",
                }
            )

        self.fields["qa_library"] = GroupedLibraryChoiceField(
            user=self.user,
            empty_label=None,
            widget=forms.Select(
                attrs={
                    "class": "form-select form-select-sm",
                    "onchange": "resetQaAutocompletes(); triggerOptionSave(); updateLibraryModalButton();",
                }
            ),
        )

        self.fields["qa_data_sources"] = forms.ModelMultipleChoiceField(
            queryset=DataSource.objects.all(),
            label=_("Select data source(s)"),
            required=False,
            widget=Autocomplete(
                use_ac=DataSourcesAutocomplete,
                attrs={
                    "component_id": f"id_qa_data_sources",
                    "id": f"id_qa_data_sources__textinput",
                },
            ),
        )

        self.fields["qa_documents"] = forms.ModelMultipleChoiceField(
            queryset=Document.objects.all(),
            label=_("Select document(s)"),
            required=False,
            widget=Autocomplete(
                use_ac=DocumentsAutocomplete,
                attrs={
                    "component_id": f"id_qa_documents",
                    "id": f"id_qa_documents__textinput",
                },
            ),
        )

        self.fields["qa_data_sources"].required = False
        self.fields["qa_documents"].required = False

    def save(self, commit=True):
        # Get the PK, if any
        pk = self.instance.pk
        if pk:
            original_library_id = ChatOptions.objects.get(pk=pk).qa_library_id
        instance = super(ChatOptionsForm, self).save(commit=False)
        library_id = instance.qa_library_id
        if not library_id:
            library_id = Library.objects.get_default_library().id
        if pk and original_library_id != library_id:
            instance.qa_scope = "all"
            instance.qa_data_sources.clear()
            instance.qa_documents.clear()
        if commit:
            instance.save()
        if not (pk and original_library_id != library_id):
            instance.qa_data_sources.set(self.cleaned_data["qa_data_sources"])
            instance.qa_documents.set(self.cleaned_data["qa_documents"])
        return instance


class ChatRenameForm(ModelForm):
    class Meta:
        model = Chat
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "onkeyup": "if (event.key === 'Escape') { cancelChatRename(); }",
                    "onblur": "cancelChatRename();",
                    "placeholder": _("Untitled chat"),
                }
            )
        }
