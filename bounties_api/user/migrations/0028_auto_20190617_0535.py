# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-06-17 05:35
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0027_auto_20190223_1548'),
    ]

    operations = [
        migrations.AlterField(
            model_name='settings',
            name='emails',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={'activity': False, 'both': {'RatingReceived': True}, 'fulfiller': {'ApplicationAcceptedApplicant': True, 'ApplicationRejectedApplicant': True, 'BountyChangedApplicant': True, 'BountyChangedFulfiller': True, 'BountyCommentReceivedCommenter': True, 'BountyCommentReceivedFulfiller': True, 'FulfillmentAcceptedFulfiller': True}, 'issuer': {'ApplicationReceived': True, 'BountyCommentReceivedIssuer': True, 'BountyCompleted': True, 'BountyExpired': True, 'ContributionReceived': True, 'FulfillmentSubmittedIssuer': True, 'FulfillmentUpdatedIssuer': True, 'TransferRecipient': True}}),
        ),
    ]