# Generated by Django 5.1 on 2024-08-26 19:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("otto", "0003_cost_count_costtype_short_name_costtype_unit_cost_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="cost",
            old_name="amount",
            new_name="usd_cost",
        ),
    ]
