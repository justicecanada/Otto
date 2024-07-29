# Generated by Django 5.0.7 on 2024-07-25 20:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("chat", "0001_initial"),
        ("librarian", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="answersource",
            name="document",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="librarian.document",
            ),
        ),
    ]
