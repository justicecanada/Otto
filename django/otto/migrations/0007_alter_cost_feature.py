# Generated by Django 5.1 on 2024-09-20 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("otto", "0006_cost_law"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cost",
            name="feature",
            field=models.CharField(
                blank=True,
                choices=[
                    ("librarian", "Librarian"),
                    ("qa", "Q&A"),
                    ("chat", "Chat"),
                    ("chat_agent", "Chat agent"),
                    ("translate", "Translate"),
                    ("summarize", "Summarize"),
                    ("template_wizard", "Template wizard"),
                    ("laws_query", "Legislation search"),
                    ("laws_load", "Legislation loading"),
                    ("case_prep", "Case prep assistant"),
                    ("text_extractor", "Text extractor"),
                ],
                max_length=50,
                null=True,
            ),
        ),
    ]
