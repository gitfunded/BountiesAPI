from django.db import models


class BountiesTimeline(models.Model):
    date = models.DateField()
    is_week = models.BooleanField(default=False)
    bounties_issued_cum = models.PositiveIntegerField(default=0)
    bounties_issued = models.PositiveIntegerField(default=0)
    fulfillments_submitted_cum = models.PositiveIntegerField(default=0)
    fulfillments_submitted = models.PositiveIntegerField(default=0)
    fulfillments_accepted_cum = models.PositiveIntegerField(default=0)
    fulfillments_accepted = models.PositiveIntegerField(default=0)
    fulfillments_pending_acceptance = models.PositiveIntegerField(default=0)
    fulfillment_acceptance_rate = models.FloatField(default=0)
    bounty_fulfilled_rate = models.FloatField(default=0)
    avg_fulfiller_acceptance_rate = models.FloatField(default=0)
    avg_fulfillment_amount = models.FloatField(default=0)
    total_fulfillment_amount = models.FloatField(default=0)
    total_unique_issuers = models.PositiveIntegerField(default=0)
    total_unique_issuers_cum = models.PositiveIntegerField(default=0)
    total_unique_fulfillers = models.PositiveIntegerField(default=0)
    total_unique_fulfillers_cum = models.PositiveIntegerField(default=0)
    bounty_draft = models.PositiveIntegerField(default=0)
    bounty_active = models.PositiveIntegerField(default=0)
    bounty_completed = models.PositiveIntegerField(default=0)
    bounty_expired = models.PositiveIntegerField(default=0)
    bounty_dead = models.PositiveIntegerField(default=0)
    platform = models.CharField(max_length=64, blank=True)


class Tokens(models.Model):
    token_symbol = models.CharField(max_length=128)
    token_contract = models.CharField(max_length=128)
    total_count = models.PositiveIntegerField(default=0)
    usd_price = models.FloatField(default=0)
