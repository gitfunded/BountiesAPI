# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2019-11-20 17:39
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('std_bounties', '0035_contract'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='abi',
            field=django.contrib.postgres.fields.jsonb.JSONField(null=True),
        ),
    ]
