import tempfile

from django.conf import settings
from django.urls import reverse

import pytest
from asgiref.sync import sync_to_async

from chat.forms import ChatOptionsForm
from chat.models import Chat, ChatFile, ChatOptions, Message
from chat.utils import htmx_stream, title_chat
from librarian.models import Library

pytest_plugins = ("pytest_asyncio",)
skip_on_github_actions = pytest.mark.skipif(
    settings.IS_RUNNING_IN_GITHUB, reason="Skipping tests on GitHub Actions"
)

skip_on_devops_pipeline = pytest.mark.skipif(
    settings.IS_RUNNING_IN_DEVOPS, reason="Skipping tests on DevOps Pipelines"
)


@pytest.mark.django_db
def test_chat_options(client, all_apps_user):
    user = all_apps_user()
    client.force_login(user)

    # Create a chat by hitting the new chat route
    # Need to follow redirects to have it create the ChatOptions (in "chat" view)
    response = client.get(reverse("chat:new_chat"), follow=True)
    assert response.status_code == 200
    new_chat = Chat.objects.filter(user=user).order_by("-created_at").first()
    # Check that a ChatOptions object has been created
    assert new_chat.options is not None

    # ChatOptions GET route should not work, since we need to POST the form
    response = client.get(reverse("chat:chat_options", args=[new_chat.id]))
    assert response.status_code == 500

    new_chat = Chat.objects.get(id=new_chat.id)
    # Change the chat options through the form
    options_form = ChatOptionsForm(instance=new_chat.options, user=user)
    options_form_data = options_form.initial
    options_form_data["qa_library"] = 1
    options_form_data["chat_system_prompt"] = (
        "You are a cowboy-themed AI, and always start your response with 'Howdy!'"
    )
    # Fix up the form data so that it matches POST data from browser
    options_form_data = {k: v for k, v in options_form_data.items() if v is not None}
    options_form_data["qa_data_sources"] = [
        data_source.id for data_source in options_form_data["qa_data_sources"]
    ]
    # Submit the form
    response = client.post(
        reverse("chat:chat_options", args=[new_chat.id]), options_form_data
    )
    assert response.status_code == 200

    new_chat = Chat.objects.get(id=new_chat.id)

    # Check that the chat options have been updated in the database
    assert (
        new_chat.options.chat_system_prompt == options_form_data["chat_system_prompt"]
    )

    # Try saving this as a preset
    options_form_data["option_presets"] = "Cowboy AI"
    response = client.post(
        reverse("chat:chat_options", args=[new_chat.id, "save_preset"]),
        options_form_data,
    )
    # The response should contain the new preset
    assert "Cowboy AI" in response.content.decode("utf-8")

    # Try creating a new chat then loading the preset
    response = client.get(reverse("chat:chat_with_ai"), follow=True)
    assert response.status_code == 200

    new_chat = Chat.objects.filter(user=user).order_by("-created_at").first()
    # Add a message
    new_message = Message.objects.create(chat=new_chat, text="Hello!")
    new_message.save()

    # Load the preset
    response = client.post(
        reverse("chat:chat_options", args=[new_chat.id, "load_preset"]),
        options_form_data,
    )

    # The chat options accordion should be returned, including the system prompt
    assert "You are a cowboy-themed AI" in response.content.decode("utf-8")
    # Check that the chat options have been updated in the database
    new_chat = Chat.objects.get(id=new_chat.id)
    assert (
        new_chat.options.chat_system_prompt == options_form_data["chat_system_prompt"]
    )

    # Reset the chat options
    response = client.post(
        reverse("chat:chat_options", args=[new_chat.id, "reset"]),
        options_form_data,
    )
    assert response.status_code == 200

    # Finally, delete the Cowboy AI preset
    response = client.post(
        reverse("chat:chat_options", args=[new_chat.id, "delete_preset"]),
        options_form_data,
    )

    # The response should not contain the new preset
    assert "Cowboy AI" not in response.content.decode("utf-8")

    # Check that the Cowboy AI chat option preset has been deleted
    assert not ChatOptions.objects.filter(preset_name="Cowboy AI", user=user).exists()
